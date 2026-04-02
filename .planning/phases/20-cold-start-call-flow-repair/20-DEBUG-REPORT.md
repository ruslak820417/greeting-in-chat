# Phase 20 ColdStartCoordinator Debug Report

**Date:** 2026-03-30
**Investigator:** Claude Opus 4.6 (GSD Debugger)
**Scope:** Complete regression analysis of Phase 20 refactoring (commits a61d2b1 through 85c44ca)
**Baseline:** Build 83, commit 4e508ac (everything worked)

---

## Executive Summary

Phase 20 extracted cold start call coordination from App.tsx, CallKitService, and index.js into a new `ColdStartCoordinator.ts` module. The extraction introduced **3 critical bugs** that completely break the call system. Two of the bugs interact to create a cascading failure where calls are permanently dead after the first CallKit interaction.

Messages and online status are **NOT broken by the code changes** themselves -- the server-side changes (TURN caching, SDP minification) are correct and don't affect message relay or status ping. If the user observes message/status failures, the cause is likely environmental (server not redeployed with latest code, WebSocket connection issues, or testing confusion caused by the call system being completely broken).

---

## ROOT CAUSE #1: Dangling Reference to Removed Method

**Severity:** CRITICAL -- breaks ALL incoming calls on warm start
**File:** `src/services/MessagingService.ts`, line 300
**Introduced by:** Commit a7ee2a8 (refactor 20-01) removed `hasColdStartAnswer()` from CallKitService but did NOT update MessagingService

### The Bug

```typescript
// MessagingService.ts, line 299-301
const CallKitServiceRef = require('./CallKitService').default;
const isColdStartAnswer = CallKitServiceRef.hasColdStartAnswer() ||  // <-- METHOD DOES NOT EXIST
    (global as any).__coldStartCall?.answerUUID;
```

`CallKitService.hasColdStartAnswer()` was removed in Phase 20 (moved to ColdStartCoordinator). But MessagingService still calls it.

### Impact Chain

1. Incoming call offer arrives via SignalingClient `offer` event
2. Handler enters `if (message.payload?.isCall)` block (line 264)
3. Passes `ColdStartCoordinator.isHandled` check (line 269) -- returns `false` for normal calls
4. Passes dedup check (line 275) and age check (line 292)
5. Reaches line 300: `CallKitServiceRef.hasColdStartAnswer()`
6. **THROWS**: `TypeError: CallKitServiceRef.hasColdStartAnswer is not a function`
7. Promise rejects (async handler) -- error is unhandled
8. The 600ms pending call timer is NEVER set
9. `EventBus.emit('incoming-call')` is NEVER called
10. **Result:** Caller's phone rings, callee never sees the call

### Fix

```typescript
// Replace lines 299-301 with:
const isColdStartAnswer = ColdStartCoordinator.hasAnswer;
```

Import `ColdStartCoordinator` at the top of the offer handler (already `require`'d on line 268 as a local variable but using a shadowed name -- use the existing reference):

```typescript
// Line 268 already has:
const ColdStartCoordinator = require('./ColdStartCoordinator').default;
// So line 300-301 becomes:
const isColdStartAnswer = ColdStartCoordinator.hasAnswer;
```

---

## ROOT CAUSE #2: `ColdStartCoordinator.reset()` Never Called

**Severity:** CRITICAL -- makes calls permanently dead after first cold start handling
**File:** `src/services/ColdStartCoordinator.ts`, line 406
**Introduced by:** Commit a61d2b1 (feat 20-01) -- `reset()` method was created but never wired up

### The Bug

The `reset()` method exists (line 406-418) and properly clears all state:
```typescript
reset(): void {
    this._answerUUID = null;
    this._declineUUID = null;
    this._audioSessionActivated = false;
    this._callData = null;
    this.handled = false;          // <-- THIS is the critical field
    this._callEndedFrom = null;
    // ... etc
}
```

But **no code anywhere calls it**. Zero references in the entire codebase:
- Not called when CallScreen finishes
- Not called when call ends
- Not called on any lifecycle event

### Impact Chain

1. Cold start call is handled (or BUG #3 triggers false cold-start handling)
2. `this.handled = true` is set (line 308, 345, or 367)
3. `ColdStartCoordinator.isHandled` returns `true` **permanently**
4. Every subsequent `incoming-call` event is blocked by App.tsx line 180:
   ```typescript
   if (ColdStartCoordinator.isHandled) {
       console.log('[App] incoming-call ignored -- cold start already handled');
       return;  // SILENTLY DROPS ALL CALLS
   }
   ```
5. Every subsequent call offer is blocked by MessagingService line 269:
   ```typescript
   if (ColdStartCoordinator.isHandled) {
       console.log('...suppressed -- cold start already handled');
       return;  // SILENTLY DROPS ALL OFFERS
   }
   ```

### Fix

Call `ColdStartCoordinator.reset()` when a call ends. Best location: CallScreen's `finishAndGoBack()` function.

```typescript
// In CallScreen.tsx, inside finishAndGoBack():
ColdStartCoordinator.reset();
```

Also consider resetting when the App.tsx cold start coordinator useEffect completes (for cases where cold start is detected but no call materializes -- e.g., caller hung up during boot, or paths A/B/C all fail).

---

## ROOT CAUSE #3: index.js Contaminates ColdStartCoordinator State for Warm Calls

**Severity:** CRITICAL -- causes false cold-start handling and silent call auto-decline
**File:** `index.js`, lines 34-44
**Introduced by:** Commit a61d2b1 (feat 20-01) -- index.js handlers write to ColdStartCoordinator unconditionally

### The Bug

```javascript
// index.js, lines 34-43
const onAnswerCall = ({ callUUID }) => {
    ColdStartCoordinator.setAnswerUUID(callUUID);  // Called for ALL calls, not just cold start
};

const onEndCall = ({ callUUID }) => {
    ColdStartCoordinator.setDeclineUUID(callUUID);  // Called for ALL calls, not just cold start
};
```

These handlers are registered as "Normal event listeners (for when app is already running)" on lines 104-108:
```javascript
RNCallKeep.addEventListener('answerCall', onAnswerCall);
RNCallKeep.addEventListener('endCall', onEndCall);
```

The problem: When the app is already running (warm start) and a user answers/declines a call via CallKit, these handlers fire and SET state in ColdStartCoordinator. The old code wrote to `global.__coldStartCall` which was harmless because App.tsx read it differently. But now ColdStartCoordinator interprets any non-null `answerUUID` or `declineUUID` as a cold start scenario.

### Impact Chain (Warm Call Decline Scenario)

1. User is in a warm (normal) call, ends it via CallKit
2. index.js `onEndCall` fires: `ColdStartCoordinator.setDeclineUUID(callUUID)`
3. `ColdStartCoordinator.hasDecline` is now `true`
4. `ColdStartCoordinator.isActive` is now `true`
5. Next incoming call triggers `incoming-call` event
6. App.tsx handler calls `ColdStartCoordinator.handleIncomingCallDuringColdStart(data)`
7. `handleIncomingCallDuringColdStart` sees `hasDecline = true`
8. AUTO-DECLINES the call: sends `call-ended`, saves missed call, sets `handled = true`
9. User never sees the incoming call
10. Due to BUG #2, `handled = true` permanently -- ALL future calls blocked

### Fix

The index.js "normal event listeners" should NOT write to ColdStartCoordinator. They were added for cold start event capture via `didLoadWithEvents`, but the normal `addEventListener` calls duplicate with CallKitService's own handlers.

**Option A (Recommended):** Remove the normal event listener registrations from index.js entirely:
```javascript
// REMOVE lines 104-108:
// RNCallKeep.addEventListener('answerCall', onAnswerCall);
// RNCallKeep.addEventListener('endCall', onEndCall);
// RNCallKeep.addEventListener('didActivateAudioSession', onDidActivateAudioSession);
// RNCallKeep.addEventListener('didDeactivateAudioSession', onDidDeactivateAudioSession);
```

The `didLoadWithEvents` handler on line 92 already handles the cold start case. CallKitService.initialize() handles the warm case.

**Option B:** Guard the handlers with a cold-start-only check:
```javascript
const onAnswerCall = ({ callUUID }) => {
    // Only set ColdStartCoordinator if this is actually a cold start
    // (no activeCalls tracked yet = CallKitService hasn't initialized)
    if (!CallKitService.initialized) {
        ColdStartCoordinator.setAnswerUUID(callUUID);
    }
};
```

---

## Additional Issues (Non-Critical)

### Issue 4: Duplicate CallKeep Event Handlers

**Files:** `index.js` lines 104-108, `CallKitService.ts` lines 66-68
**Impact:** Medium -- causes duplicate event processing

Both index.js and CallKitService register handlers for `answerCall`, `endCall`, `didActivateAudioSession`, and `didDeactivateAudioSession`. When a CallKit event fires, both handlers execute. This causes:
- `ColdStartCoordinator.setAnswerUUID()` called twice (once from index.js, once from CallKitService cold start path)
- Audio session activation code runs twice
- Potential for race conditions in event ordering

**Fix:** Remove the duplicate registrations from index.js (same as ROOT CAUSE #3 fix).

### Issue 5: `global.__coldStartCall` Backward-Compat Proxy May Be Unnecessary

**File:** `index.js` lines 25-30
**Impact:** Low -- adds complexity

The proxy object delegates to ColdStartCoordinator. The comment says it's needed because "CallScreen.tsx reads `global.__coldStartCall?.answerUUID`". However, the CallScreen.tsx diff shows it was updated to read from ColdStartCoordinator directly. The proxy may still be needed by other code, but should be verified and removed if not.

---

## Server-Side Analysis

The server changes in Phase 20 are **clean and correct**:

1. **TURN Server Cache** (`server/index.js`): New `getCachedTurnServers()` async function with proper caching. Used in `get-call-state` and call offer push. No impact on message relay.

2. **Async Message Handler** (`server/index.js`): `ws.on('message')` changed from sync to `async` to support `await getCachedTurnServers()`. This is safe in Node.js.

3. **SDP Minification** (`server/push.js`): Strips `extmap` and `rtcp-fb` lines from SDP to fit within Apple's 5KB VoIP payload limit. Adds final payload size validation with fallback (removes SDP if too large). Correct implementation.

4. **TURN in VoIP Push** (`server/push.js`): Prefers `callData.turnServers` over static env vars. Falls back correctly.

None of these changes affect message delivery (`encrypted-message`), online status (`ping-user`/`user-status`), or WebSocket registration.

---

## Messages and Online Status

The user reports messages don't arrive and online/last seen doesn't update. After thorough investigation:

1. **Message relay path** (`encrypted-message` event): Unchanged in Phase 20. No code in the diff touches message handling.

2. **Online status path** (`user-status` event): Unchanged in Phase 20. Server `ping-user` handler is intact.

3. **P2P data channel offers**: WebRTCManager's `handleOffer()` correctly ignores `isCall` offers and processes chat offers independently. The `hasColdStartAnswer()` crash only affects the MessagingService call offer handler, not WebRTCManager.

**Possible explanations for reported message/status failures:**
- Server was not redeployed with the Phase 20 changes (the `async` handler change requires server restart)
- Testing confusion: calls being broken made the entire app seem dead
- WebSocket connection failure on one device (unrelated to Phase 20)
- If the user's test involved force-killing the app and relaunching, ColdStartCoordinator.isActive returning `true` (from stale state) could cause the app to bypass the loading screen but then behave oddly

---

## Fix Priority Order

| Priority | Bug | Fix | Files |
|----------|-----|-----|-------|
| P0 | BUG #1: Dangling `hasColdStartAnswer()` | Replace with `ColdStartCoordinator.hasAnswer` | `MessagingService.ts:300` |
| P0 | BUG #3: index.js normal listeners contaminate ColdStartCoordinator | Remove lines 104-108 (normal event listeners) | `index.js` |
| P0 | BUG #2: `reset()` never called | Add `ColdStartCoordinator.reset()` call in CallScreen.finishAndGoBack() | `CallScreen.tsx`, `ColdStartCoordinator.ts` |
| P1 | Issue #4: Duplicate event handlers | Addressed by BUG #3 fix | `index.js` |
| P2 | Issue #5: Unnecessary global proxy | Verify and remove if no other consumers | `index.js` |

---

## Proposed Code Changes

### Fix 1: MessagingService.ts (line 299-301)

**Before:**
```typescript
const CallKitServiceRef = require('./CallKitService').default;
const isColdStartAnswer = CallKitServiceRef.hasColdStartAnswer() ||
    (global as any).__coldStartCall?.answerUUID;
```

**After:**
```typescript
const isColdStartAnswer = ColdStartCoordinator.hasAnswer;
```

Note: `ColdStartCoordinator` is already `require`'d on line 268 as a local variable. Use that reference. Remove the unused `CallKitServiceRef` require.

### Fix 2: index.js (lines 104-108)

**Remove:**
```javascript
// Normal event listeners (for when app is already running)
RNCallKeep.addEventListener('answerCall', onAnswerCall);
RNCallKeep.addEventListener('endCall', onEndCall);
RNCallKeep.addEventListener('didActivateAudioSession', onDidActivateAudioSession);
RNCallKeep.addEventListener('didDeactivateAudioSession', onDidDeactivateAudioSession);
```

These are redundant with CallKitService.initialize() handlers. The `didLoadWithEvents` handler (line 92) already handles the cold start case.

### Fix 3: CallScreen.tsx -- Add reset() call

**In `finishAndGoBack()`:**
```typescript
// After saving call log and before navigating back:
ColdStartCoordinator.reset();
```

### Fix 4: App.tsx -- Add reset() call for failed cold start

**In the cold start coordinator useEffect, add cleanup for the case where coordinator doesn't resolve:**
```typescript
// In the polling stopTimer callback:
stopTimer = setTimeout(() => {
    if (pollTimer) clearInterval(pollTimer);
    ColdStartCoordinator.reset(); // Cold start timed out -- clear stale state
}, 60000);
```

---

## Verification Plan

After applying fixes:
1. **Warm start incoming call**: Phone A calls Phone B (both apps already running) -- call should ring on B
2. **Warm start outgoing call**: Phone B calls Phone A -- call should connect
3. **Second call after first**: End first call, make another -- should work (verifies reset())
4. **Cold start call**: Force-kill app on Phone B, call from Phone A -- should wake via VoIP push
5. **Messages**: Send text message -- should arrive via relay
6. **Online status**: Open chat -- should show online/last seen
7. **CallKit decline test**: Decline a call via CallKit, then receive another call -- should show normally
