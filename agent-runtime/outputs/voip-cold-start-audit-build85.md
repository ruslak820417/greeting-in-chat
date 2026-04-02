# QRChat VoIP Cold Start Call Flow — Full Audit

**Build:** 85 (v4.3.0)
**Date:** 2026-03-29
**Scope:** Complete cold start call infrastructure analysis

---

## 1. EXACT COLD START SEQUENCE (Numbered Steps with Timing)

### Phase 0: VoIP Push Arrives (Native Layer, ~0-50ms)

```
T+0ms    iOS receives VoIP push via PKPushRegistry
T+1ms    AppDelegate.pushRegistry(didReceiveIncomingPushWith:) fires
T+2ms    Parse payload: from, callerName, isVideo, sdp, turnServers
T+3ms    Generate UUID for this call
T+4ms    Serialize callInfo to JSON → UserDefaults["PendingVoIPCall"]
         (includes uuid, from, callerName, isVideo, sdp, turnServers, timestamp)
T+5ms    MUST call RNCallKeep.reportNewIncomingCall() synchronously
         (Apple kills app if not called before method returns)
T+10ms   CallKit shows native incoming call UI (lock screen / banner)
T+15ms   completion() called — VoIP push handler done
```

### Phase 1: App Cold Boot (Native → JS Bridge, ~50-500ms)

```
T+50ms   iOS launches the app process (if killed)
T+100ms  AppDelegate.didFinishLaunchingWithOptions fires
T+110ms  RTCAudioSession observer registered (audio interruption notification)
T+120ms  PKPushRegistry registered (VoIP push — already handled above)
T+150ms  React Native factory starts loading JS bundle
T+200ms  AVAudioSession interruptionNotification may fire (.ended)
         → RTCAudioSession.audioSessionDidActivate() called
```

### Phase 2: JS Bridge Boot (index.js, ~300-800ms)

```
T+300ms  index.js executes BEFORE AppRegistry.registerComponent
T+305ms  global.__coldStartCall initialized:
           { answerUUID: null, declineUUID: null,
             audioSessionActivated: false, callData: null }
T+310ms  RNCallKeep.addEventListener('didLoadWithEvents') registered
T+315ms  RNCallKeep.addEventListener('answerCall') registered
T+320ms  RNCallKeep.addEventListener('endCall') registered
T+325ms  RNCallKeep.addEventListener('didActivateAudioSession') registered
T+330ms  didLoadWithEvents fires (if user already tapped Answer/Decline):
           → global.__coldStartCall.answerUUID set
           → global.__coldStartCall.audioSessionActivated set
           → RTCAudioSession.audioSessionDidActivate() called
           → RTCAudioBridge.setAudioEnabled(true) called
T+340ms  AppRegistry.registerComponent('QRChat', () => App)
```

### Phase 3: React Tree Mount (App.tsx, ~500-1500ms)

```
T+500ms  App component renders
T+510ms  isColdStartCall detected from global.__coldStartCall
         → showSplash set to FALSE (skip splash for cold start calls)
T+520ms  CallKitService constructor runs:
         → registers its OWN didLoadWithEvents listener
         → captures coldStartAnswerUUID / coldStartDeclineUUID
T+530ms  useEffect[] fires → checkSetup() begins
T+540ms  useEffect[] for cold-start-answer EventBus listener registered
T+550ms  useEffect[] for incoming-call / callkit-answer / callkit-decline registered
```

### Phase 4: checkSetup() (async, ~500-3000ms from T+530)

```
T+600ms  Database.getProfile() + Database.getKeys()
T+700ms  KeyManager.loadKeys()
T+800ms  MessagingService.initialize() begins:
           → Registers signaling handlers (offer, answer, ice-candidate, etc.)
           → SignalingClient.connect(userId) — WebSocket to relay
T+1200ms WebSocket connects + auth challenge/response
T+1500ms 'registered' event → requestTurnCredentials() sent automatically
T+1600ms 'turn-credentials' response → cached in SignalingClient
T+1700ms NotificationService.initialize()
T+1800ms CallKitService.initialize()
           → RNCallKeep.setup()
           → addEventListener('answerCall') / ('endCall')
           → addEventListener('didActivateAudioSession')
T+2000ms setIsSetupComplete(true) → triggers cold start coordinator useEffect
```

### Phase 5: Cold Start Coordinator (useEffect[isSetupComplete], ~2000-5000ms)

```
T+2100ms Coordinator detects hasColdAnswer OR starts polling (200ms intervals)
T+2200ms runCoordinator() executes:

         PATH A: Try VoIP push payload (fastest)
T+2210ms   NativeModules.APNsTokenModule.getPendingVoIPCall()
T+2220ms   Parse JSON → extract sdp, turnServers, from, callerName
T+2230ms   JSON.parse(sdp) if string → sdpOffer object
T+2240ms   Cache TURN servers from push into SignalingClient
T+2250ms   CallKitService.trackColdStartCall()
T+2260ms   SignalingClient.sendCallAcceptedPending(callFrom)
T+2270ms   navigate('Call', { ... offer: sdpOffer ... })
           → queued in NavigationService if NavigationContainer not ready

         PATH B: WebSocket get-call-state (if PATH A fails)
T+2300ms   Check if WebSocket connected (should be from checkSetup)
T+2400ms   If not → MessagingService.initializeFastPath()
T+2500ms   SignalingClient.requestCallState()
T+2600ms   Wait for 'call-state' response (max 3s timeout)
T+2700ms   If SDP received → navigate to CallScreen

         PATH C: Fall through to pending queue (slowest)
T+5000ms   Offer arrives via normal pending message delivery
           → MessagingService offer handler fires 'incoming-call'
           → App.tsx handler checks hasColdStartAnswer → skips overlay
           → navigate('Call')
```

### Phase 6: NavigationContainer Ready + CallScreen Mount

```
T+2500ms AppNavigator renders → NavigationContainer mounts
T+2600ms onReady fires → setNavReady(true) → flushPendingNavigation()
         → queued navigate('Call') replays
T+2700ms CallScreen mounts
T+2800ms startCall() begins:
           → getUserMedia (audio + optional video)
           → Check WebSocket connected (initializeFastPath if not)
           → Wait for TURN credentials (3s max timeout)
           → InCallManager.start()
           → WebRTCManager.answerCall() — peer connection + SDP exchange
           → Re-notify RTCAudioSession (cold start audio fix)
T+3500ms ICE negotiation begins
T+4000ms ICE connected → audio flows
```

---

## 2. DEPENDENCY CHAIN DIAGRAM

```
VoIP Push (native)
  |
  ├── reportNewIncomingCall (SYNCHRONOUS, required by Apple)
  |     └── CallKit UI shows on screen
  |
  └── UserDefaults["PendingVoIPCall"] = { uuid, from, sdp, turnServers }
        |
        ├── [User taps Answer on CallKit UI]
        |     |
        |     ├── index.js handler → global.__coldStartCall.answerUUID = UUID
        |     ├── CallKitService.didLoadWithEvents → coldStartAnswerUUID = UUID
        |     └── didActivateAudioSession → RTCAudioSession.audioSessionDidActivate()
        |
        v
  JS Bridge boots (index.js → App.tsx)
        |
        v
  checkSetup() ─────────────────────────────────────────────┐
    ├── Database.getProfile/getKeys                          |
    ├── KeyManager.loadKeys                                  |
    ├── MessagingService.initialize()                        |
    |     ├── Register offer/answer/ice handlers             |
    |     └── SignalingClient.connect()                      |
    |           ├── WebSocket auth                           |
    |           ├── 'registered' → requestTurnCredentials()  |
    |           └── 'turn-credentials' → cached              |
    ├── CallKitService.initialize()                          |
    └── setIsSetupComplete(true) ────────────────────────────┘
                  |
                  v
  Cold Start Coordinator (useEffect[isSetupComplete])
    |
    ├── PATH A: getPendingVoIPCall() → UserDefaults
    |     └── Has SDP + TURN? → navigate('Call') ← FASTEST
    |
    ├── PATH B: get-call-state via WebSocket
    |     └── Server has activeCall? → navigate('Call')
    |
    └── PATH C: Wait for pending queue offer
          └── 'incoming-call' EventBus → navigate('Call') ← SLOWEST

  NavigationContainer.onReady()
    └── flushPendingNavigation() → replays navigate('Call')
          |
          v
  CallScreen.startCall()
    ├── getUserMedia()
    ├── [TURN wait: 3s max]
    ├── InCallManager.start()
    ├── WebRTCManager.answerCall()
    |     ├── createPeerConnection(ICE servers)
    |     ├── setRemoteDescription(offer SDP)
    |     ├── drainIceCandidateQueue()
    |     ├── createAnswer()
    |     ├── setLocalDescription(answer)
    |     └── SignalingClient.sendAnswer()
    └── RTCAudioSession re-notify (cold start)
```

---

## 3. RACE CONDITIONS IDENTIFIED

### RC-1: getPendingVoIPCall Consumed Before Coordinator Runs
**Severity: HIGH (but mitigated)**
**Location:** `APNsTokenModule.swift:253-259`, `App.tsx:173-237`

The `getPendingVoIPCall()` bridge method reads AND DELETES the UserDefaults key in a single call. There are TWO consumers:

1. The `cold-start-answer` EventBus handler (line 173-237 in App.tsx)
2. The cold start coordinator (line 421-636 in App.tsx)

If the EventBus handler from `CallKitService.onAnswerCall` fires and calls `getPendingVoIPCall` first, the coordinator's PATH A will find `null` and fall to PATH B (slower WebSocket path).

**Mitigation present:** The `coldStartHandledRef` guards against double execution. If the EventBus handler succeeds first, the coordinator checks `coldStartHandledRef.current` and exits.

**Remaining risk:** If the EventBus handler fires but FAILS (e.g., JSON parse error), `coldStartHandledRef` is NOT set, but `PendingVoIPCall` is already consumed. The coordinator then falls to PATH B/C, adding 1-3 seconds.

### RC-2: NavigationContainer Not Mounted When navigate() Is Called
**Severity: MEDIUM (mitigated with queue)**
**Location:** `NavigationService.ts:10-22`, `App.tsx:761-763`

The `navigate()` function checks `navigationRef.current` and queues the request if null. The queue is flushed when `NavigationContainer.onReady` fires. However:

- The queue holds only ONE pending navigation (`pendingNavigation` is a single variable, not an array)
- If `navigate('Call')` is called, then `navigate('Chat')` is called before flush, the Call navigation is LOST

**Current risk:** Low in practice — during cold start call, only one navigate should fire. But if a notification tap also queues, there is a real conflict.

### RC-3: WebSocket Not Connected When Answer SDP Needs to Be Sent
**Severity: HIGH**
**Location:** `CallScreen.tsx:287-296`, `WebRTCManager.ts:416`

CallScreen.startCall() (incoming path) calls `WebRTCManager.answerCall()` which calls `SignalingClient.sendAnswer()`. If the WebSocket is not connected at this point, the answer SDP is queued in the send queue (30s TTL). But:

- The caller's peer connection has a `connectionState` timeout
- If the answer arrives late, the caller may have already abandoned ICE negotiation
- The send queue uses `QUEUE_MAX_AGE = 30000` (30s) — the answer may be flushed before delivery

**Mitigation present:** CallScreen does `MessagingService.initializeFastPath()` if not connected (line 289-295). But `initializeFastPath` has an 8-second timeout, and the answer is sent AFTER `answerCall()` — if the WS connection drops between fast-path and sendAnswer, the answer is silently queued.

### RC-4: TURN Credentials Not Available at Peer Connection Creation
**Severity: HIGH**
**Location:** `CallScreen.tsx:297-320`, `WebRTCManager.ts:509-511`, `constants.ts:46-75`

The peer connection is created with ICE servers from `getIceServers()`. This function:
1. Checks `SignalingClient.getCachedTurnServers()` (primary)
2. Falls back to HTTP fetch from Railway server
3. Last resort: STUN-only

On cold start, if TURN credentials from the VoIP push were cached (PATH A), `getCachedTurnServers()` returns them. But if PATH B or C was taken, TURN may not be cached yet because:
- `requestTurnCredentials()` is sent after `'registered'` event
- The `'turn-credentials'` response is async
- CallScreen has a 3-second TURN wait loop (200ms polling)

**Remaining risk:** If the 3-second TURN timeout expires, the peer connection is created with STUN-only. Behind symmetric NAT, the call WILL FAIL silently (ICE stays in "checking" state until it times out).

### RC-5: Audio Session Timing — CallKit Activates Before Peer Connection Exists
**Severity: MEDIUM (mitigated)**
**Location:** `index.js:43-58`, `CallScreen.tsx:331-349`

On cold start:
1. CallKit activates the audio session (user taps Answer)
2. `audioSessionDidActivate()` is called in index.js
3. But the RTCPeerConnection does not exist yet (CallScreen hasn't mounted)
4. WebRTC's audio unit needs the session to be active WHEN it initializes

**Mitigation present:** CallScreen re-calls `RTCAudioSession.audioSessionDidActivate()` and `RTCAudioBridge.setAudioEnabled(true)` AFTER `answerCall()` completes (lines 331-349). This is the "double-notify" pattern that was the Build 83 root cause fix.

**Remaining risk:** If `audioSessionActivated` flag is not set in `global.__coldStartCall` (e.g., the `didLoadWithEvents` event didn't include `RNCallKeepDidActivateAudioSession`), the re-notify is SKIPPED (line 348-349 condition). This can happen if CallKit delayed the audio activation event.

### RC-6: Duplicate Call Navigation — Multiple Paths Race to Navigate
**Severity: MEDIUM (mitigated)**
**Location:** `App.tsx` — three separate paths can call `navigate('Call')`

1. `cold-start-answer` EventBus handler (line 173)
2. Cold start coordinator PATH A/B/C (line 492-635)
3. `incoming-call` EventBus handler with `hasColdStartAnswer()` check (line 250-266)

All three are guarded by `coldStartHandledRef`, but the guards are checked at different times. If two paths start concurrently and both pass the guard before either sets it, you get duplicate navigation.

**Mitigation:** `coldStartHandledRef.current = true` is set before `navigate()` in the coordinator (line 501). The EventBus handler checks it at entry (line 175, 244). The ordering of state mutations should prevent duplicates in practice.

### RC-7: SDP Double-Serialization in VoIP Push Payload
**Severity: LOW (handled)**
**Location:** `server/index.js:868`, `server/push.js:379-391`, `App.tsx:553`

The offer payload goes through multiple serializations:
1. `server/index.js:868` — `JSON.stringify(message.payload)` → string
2. `push.js:380` — if string, keeps as-is; if object, `JSON.stringify()` again
3. `push.js:391` — stored as `payloadObj.sdp = sdpStr` (a JSON string)
4. `AppDelegate.swift:189` — stored as-is in UserDefaults
5. `App.tsx:553` — `typeof callInfo.sdp === 'string' ? JSON.parse(callInfo.sdp) : callInfo.sdp`

The server sends `callData.offer` as `JSON.stringify(message.payload)` at line 868, which means `push.js` receives a string, keeps it as-is, and the client parses it back. This works, but there is a subtle issue: `message.payload` is an object with `{ sdp, type, isCall, isVideo, callTimestamp }`. After `JSON.stringify`, it becomes a string. In `push.js:382`, the check `typeof callData.offer === 'object'` fails, so the SDP minification is NEVER applied (the offer is already a string). The unminified SDP may exceed the 4500-byte VoIP payload limit more often.

### RC-8: Caller Hangs Up During Callee Boot — Race with call-ended
**Severity: MEDIUM (mitigated)**
**Location:** `MessagingService.ts:250-254`, `CallScreen.tsx:221-227`

If the caller hangs up while the callee is booting:
1. `call-ended` arrives via WebSocket pending queue
2. `MessagingService` sets `global.__callEndedDuringBoot = message.from`
3. CallScreen checks this flag on mount (line 222) and exits immediately

**Remaining risk:** If the WebSocket connection is not yet established when `call-ended` is sent by the caller, the message may not arrive until after CallScreen already started the peer connection. The check at line 222 only runs once at mount time.

### RC-9: Polling Timer Leak if Setup Never Completes
**Severity: LOW**
**Location:** `App.tsx:449-487`

If `isSetupComplete` never becomes true (e.g., no profile), the polling interval for cold-start answer runs indefinitely (200ms polls for 60 seconds). The cleanup function at line 483-486 handles this, but only if the component unmounts. If the app stays in loading state, the polling runs for the full 60 seconds — low impact but wasted CPU.

---

## 4. BUILD 83-85 FIXES — WHAT WAS ADDRESSED VS WHAT REMAINS

### Build 83 (Session March 27) — Root Cause Found
**Fixed:**
- Root cause identified: NavigationContainer was not mounted during SplashScreen, so `navigate('Call')` was silently dropped
- Added `isColdStartCall` detection to skip splash screen
- Added `NavigationService.ts` queue + `flushPendingNavigation()`

### Build 84 (2026-03-28) — Critical Bridge Fixes
**Fixed:**
- `getPendingVoIPCall` was missing from `APNsTokenModule.m` (Swift method existed but ObjC bridge was not exported)
- TURN servers from VoIP push payload were not being saved to UserDefaults by AppDelegate
- Android notification sound was broken (no-op assignment)

### Build 85 (current) — Inferred Incremental Fixes
**Fixed (inferred from code):**
- Cold start coordinator with 3 paths (A/B/C) for SDP retrieval
- `initializeFastPath()` for minimal WebSocket boot during cold start
- `call-accepted-pending` message to inform caller that callee is connecting
- `global.__callEndedDuringBoot` flag for early hangup detection
- Audio session double-notify pattern after answerCall()
- `coldStartHandledRef` guard against duplicate call navigation
- Polling loop for user who hasn't tapped Answer yet (200ms, max 60s)

### WHAT REMAINS BROKEN / AT RISK

| Issue | Severity | Description |
|-------|----------|-------------|
| **No TURN in get-call-state response** | HIGH | Server's `get-call-state` sends `from, offer, callerName, isVideo` but NOT `turnServers`. If PATH B is used (VoIP push had no SDP), the callee gets the offer but no TURN credentials from the coordinator. They must wait for `turn-credentials` via WebSocket, adding 0-3s delay. |
| **SDP minification never applied** | MEDIUM | Server sends `JSON.stringify(message.payload)` as `callData.offer` string. `push.js` checks `typeof callData.offer === 'object'` for minification — always false since it's a string. Unminified SDP may exceed 4.5KB VoIP limit. |
| **Single-slot navigation queue** | MEDIUM | `NavigationService.pendingNavigation` is a single variable. If two navigations queue before flush, the first is silently overwritten. |
| **TURN 3s timeout → STUN-only** | HIGH | If TURN credentials don't arrive within 3 seconds, CallScreen proceeds with STUN-only. Behind symmetric NAT (common on mobile carriers), ICE will fail. No user-visible error — just "Connecting..." forever until 10s disconnect timeout. |
| **No retry on sendAnswer failure** | HIGH | If `SignalingClient.sendAnswer()` returns false (WS not connected), the answer SDP goes to the send queue with 30s TTL. But `endCall` has retry logic (3 retries, 2s apart) while `sendAnswer` does not. If the WS reconnects after 30s, the answer is lost. |
| **audioSessionActivated flag dependency** | MEDIUM | The post-answerCall audio re-notify (CallScreen:331-349) only fires if `global.__coldStartCall?.audioSessionActivated` is true. If the `didActivateAudioSession` event was delayed or not included in `didLoadWithEvents`, audio will not work. |
| **getPendingVoIPCall read-and-delete** | MEDIUM | The bridge method deletes the data after reading. If the first consumer fails, subsequent attempts get null. No way to re-read. |

---

## 5. SPECIFIC FILE-BY-FILE FINDINGS

### `ios/QRChat/AppDelegate.swift`
- Lines 179-203: PendingVoIPCall properly stores SDP and TURN servers (Build 84 fix confirmed)
- Line 208-221: `reportNewIncomingCall` called synchronously (correct, Apple requirement)
- Line 49-68: Audio interruption observer correctly bridges to RTCAudioSession
- **No issue found** — native layer is solid

### `ios/QRChat/APNsTokenModule.m`
- Line 9: `getPendingVoIPCall` bridge export is present (Build 84 fix confirmed)
- **No issue found** — bridge is complete

### `ios/QRChat/RTCAudioBridge.swift`
- Line 14-19: `setAudioEnabled` correctly locks/unlocks RTCAudioSession
- **No issue found** — audio bridge is clean

### `src/services/CallKitService.ts`
- Lines 42-76: `didLoadWithEvents` handler captures cold start events correctly
- Lines 78-139: `initialize()` sets up RNCallKeep + audio session handlers
- Lines 258-276: `onAnswerCall` — cold start path emits `cold-start-answer` EventBus event AND sets `coldStartAnswerUUID`. This means BOTH the EventBus handler and the coordinator can fire.
- **Finding:** `didLoadWithEvents` in CallKitService and `didLoadWithEvents` in index.js are BOTH registered. The index.js handler runs first (module load time) and sets `global.__coldStartCall.answerUUID`. The CallKitService handler runs during construction (imported by App.tsx) and sets `this.coldStartAnswerUUID`. These are redundant but consistent.

### `src/screens/CallScreen.tsx`
- Lines 215-382: startCall() is well-instrumented with diagnostic logging
- Lines 286-296: Fast-path WebSocket init for cold start — good
- Lines 297-320: TURN credential wait loop (3s max, 200ms polling) — good but timeout fallback is STUN-only
- Lines 331-349: Audio session re-notify — good but conditional on flag
- **Finding:** `InCallManager.stop()` is correctly SKIPPED for cold start incoming calls (line 236-242). This was a critical fix — calling it would deactivate the audio session that CallKit already activated.

### `src/network/SignalingClient.ts`
- Lines 83-122: connect() with relay pinning — solid
- Lines 282-310: send() with queue fallback — good, but no retry for critical messages
- Lines 394-397: `requestCallState()` — simple send, no validation
- Lines 419-432: `setCachedTurnServers` — allows external cache injection (VoIP push path)
- **Finding:** `requestTurnCredentials()` is called automatically after `'registered'` event (line 449). This means TURN credentials arrive naturally ~200-500ms after WebSocket connects. The 3s wait in CallScreen is usually sufficient.

### `src/network/WebRTCManager.ts`
- Lines 371-419: `answerCall()` — proper sequence: close existing peer, create new, setRemoteDescription, drain ICE queue, createAnswer, setLocalDescription, sendAnswer
- Lines 509-511: `createPeerConnection` calls `getIceServers()` which checks cached TURN first
- Lines 784-796: `handleOffer` correctly queues ICE candidates for call offers (doesn't auto-answer)
- **Finding:** `answerCall()` sends the answer SDP via `SignalingClient.sendAnswer()` but does NOT check the return value for retry. If the WebSocket drops right at that moment, the answer is queued with 30s TTL.

### `App.tsx`
- Lines 82-93: Cold start detection + splash skip — correct
- Lines 173-237: `cold-start-answer` EventBus handler — reads from UserDefaults, navigates
- Lines 421-636: Cold start coordinator with PATH A/B/C — comprehensive
- Lines 240-411: incoming-call handler with cold start checks — well-guarded
- **Finding:** The coordinator at line 476 checks `pendingVoIPCall()` which calls `getPendingVoIPCall()`. This is a SECOND call to the bridge method. If the cold-start-answer EventBus handler already consumed it, this returns null. But the coordinator uses it only to decide whether to start polling — it doesn't consume the data here (the `await` at line 477 only checks truthiness). However, if the EventBus handler already consumed AND handled the call, `coldStartHandledRef` should be true, and polling won't start. This is correct.

### `index.js`
- Lines 17-108: Critical early registration of CallKeep events
- Lines 31-35: `global.__coldStartCall` structure — clean
- Lines 43-58: `didActivateAudioSession` handler correctly notifies RTCAudioSession
- **Finding:** Both `index.js` AND `CallKitService` register `didLoadWithEvents`. RNCallKeep fires this event ONCE (the first registered listener gets it). If index.js consumes it, CallKitService never sees the events via `didLoadWithEvents`. BUT CallKitService also has separate `answerCall`/`endCall` event listeners that fire normally. The index.js `didLoadWithEvents` is the authoritative source for cold start state.

### `src/services/NavigationService.ts`
- Lines 8-22: Single-slot queue for pending navigation
- Lines 29-42: `flushPendingNavigation` replays with `setTimeout(0)` — correct
- **Finding:** The `setTimeout(0)` in flush ensures navigation runs after the current render cycle. This is important because `onReady` fires during render, and navigating during render causes undefined behavior.

---

## 6. RECOMMENDED FIXES (Priority Order)

### P0 — Critical

1. **Add TURN servers to `get-call-state` response** (`server/index.js:1175-1182`)
   Store TURN credentials in `activeCalls` map when the call offer is queued, and include them in the `call-state` response. This fixes PATH B cold starts behind NAT.

2. **Fix SDP minification bypass** (`server/index.js:868`)
   Change `offer: typeof message.payload === 'string' ? message.payload : JSON.stringify(message.payload || {})` to always pass the OBJECT, not a pre-stringified version. Let `push.js` handle serialization and minification.

3. **Add retry logic to `sendAnswer()`** (`WebRTCManager.ts:416`)
   Mirror the retry pattern from `endCall()` — if `sendAnswer` returns false, retry up to 3 times at 2s intervals.

### P1 — High

4. **Make navigation queue an array** (`NavigationService.ts:8`)
   Change `pendingNavigation` from a single slot to an array. Flush all pending navigations in order.

5. **Make getPendingVoIPCall non-destructive** (`APNsTokenModule.swift:253-259`)
   Add a separate `clearPendingVoIPCall()` method. Have the read be idempotent so multiple consumers can read the same data. Only clear after confirmed handling.

6. **Add user-visible error for TURN timeout** (`CallScreen.tsx:306`)
   When the 3s TURN timeout expires, show "Connection may be limited" or similar. Currently the user sees "Connecting..." with no indication that ICE will likely fail.

### P2 — Medium

7. **Deduplicate didLoadWithEvents registration**
   Either remove the CallKitService's `didLoadWithEvents` listener or have it read from `global.__coldStartCall` instead of registering its own duplicate listener.

8. **Add audioSessionActivated fallback**
   In CallScreen's post-answerCall audio re-notify (line 331-349), always call `RTCAudioSession.audioSessionDidActivate()` regardless of the flag value. The call is idempotent and safe to invoke even if already active.

---

## 7. SUMMARY

The cold start call flow in Build 85 is **substantially more robust** than the pre-Build 83 state. The triple-path coordinator (VoIP push / WebSocket / pending queue), splash skip, navigation queue, and audio re-notify pattern are all well-designed.

**Critical gap:** The WebSocket `get-call-state` path (PATH B) does not include TURN servers, meaning calls that fall through to PATH B behind NAT will fail silently. This is the highest-priority fix.

**Architecture assessment:** The system has 7+ places where SDP/call data can flow, creating inherent complexity. The `coldStartHandledRef` mutex pattern is the right approach, but the number of racing paths means edge cases are inevitable. A state machine approach (IDLE → VOIP_RECEIVED → ANSWER_TAPPED → SETUP_COMPLETE → NAVIGATED → CONNECTED) would be more maintainable than the current ref-flag guards.

**Overall cold start reliability estimate:** ~85-90% success rate for calls where VoIP push includes SDP (PATH A). ~60-70% for calls where SDP exceeds 4.5KB APNs limit (PATH B/C, especially behind NAT without TURN).
