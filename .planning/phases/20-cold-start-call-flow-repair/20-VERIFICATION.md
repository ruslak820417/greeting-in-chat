---
phase: 20-cold-start-call-flow-repair
verified: 2026-03-30T06:30:00Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 20: Cold Start Call Flow Repair — Verification Report

**Phase Goal:** Cold start incoming calls work reliably — audio flows within 8 seconds of user tapping Answer
**Verified:** 2026-03-30T06:30:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | InCallManager.stop() is skipped for incoming cold start calls | VERIFIED | `CallScreen.tsx:236-241` — `isColdStartIncoming = isIncoming && ColdStartCoordinator.hasAnswer` gates the skip path; confirmed log message "InCallManager.stop() SKIPPED -- cold start incoming" |
| 2 | RTCAudioSession.audioSessionDidActivate() is called after answerCall() on cold start | VERIFIED | `CallScreen.tsx:333-337` — `if (ColdStartCoordinator.wasAudioSessionActivated)` fires post-answerCall, calls `RTCAudioSession.audioSessionDidActivate()` |
| 3 | TURN credentials are pre-fetched before CallScreen mount (eliminating 3s wait) | VERIFIED | `ColdStartCoordinator.ts:142-148` — `requestTurnCredentials()` called in `run()` before PATH A; PATH A caches TURN from VoIP push via `SignalingClient.setCachedTurnServers()`; PATH B caches TURN from server call-state response; the 3s wait in CallScreen line 302 is bypassed when cache is populated |
| 4 | didLoadWithEvents handler exists only in index.js | VERIFIED | `index.js:92` registers `RNCallKeep.addEventListener('didLoadWithEvents', ...)` — no matching registration found anywhere in `src/services/CallKitService.ts`; grep across entire `src/` confirms zero occurrences |

**Score:** 4/4 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/services/ColdStartCoordinator.ts` | Singleton coordinator owning all cold start state | VERIFIED | 422 lines; exports singleton instance; contains `run()`, `handleIncomingCallDuringColdStart()`, `navigateToCall()`, `getDiagnosticSummary()`, `reset()` |
| `src/screens/CallScreen.tsx` | Audio session lifecycle fix for cold start | VERIFIED | Imports ColdStartCoordinator; implements InCallManager.stop() guard (line 236-241); implements RTCAudioSession re-notification (line 333-347); clears cold start audio state after use (line 353-355) |
| `src/services/CallKitService.ts` | No duplicate cold start state; delegates to ColdStartCoordinator | VERIFIED | Removed `coldStartAnswerUUID`/`coldStartDeclineUUID` fields; comment line 35-36 confirms delegation; `onAnswerCall` / `onEndCall` call `ColdStartCoordinator.setAnswerUUID()` / `setDeclineUUID()` for unknown UUIDs |
| `index.js` | Single didLoadWithEvents handler; writes to ColdStartCoordinator | VERIFIED | Lines 78-102: `didLoadWithEventsMap` dispatches to shared handler functions that write to ColdStartCoordinator; global.__coldStartCall is a read-only proxy (getters only) |
| `App.tsx` | Simplified cold start coordinator useEffect (~34 lines) | VERIFIED | Lines 312-345: cold start useEffect delegates entirely to `ColdStartCoordinator.run()` — no inline SDP retrieval logic; `isColdStartCall = ColdStartCoordinator.isActive` gates splash screen skip |
| `server/index.js` | getCachedTurnServers() with 1-hour TTL; TURN in get-call-state response | VERIFIED | Lines 183-224: `getCachedTurnServers()` with `TURN_CACHE_TTL = 3600000`; lines 1270-1282: `get-call-state` case includes `turnServers` in response |
| `server/push.js` | TURN from getCachedTurnServers() preferred over static env vars in VoIP push | VERIFIED | Lines 371-380: `if (callData.turnServers && callData.turnServers.length > 0)` prefers callData.turnServers over static env var construction |
| `src/services/MessagingService.ts` | Duplicate offer suppression + callEndedDuringBoot via ColdStartCoordinator | VERIFIED | Line 254: `ColdStartCoord.setCallEndedDuringBoot(message.from)` for call-ended during boot; line 269: `ColdStartCoordinator.isHandled` suppresses duplicate offer delivery |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `index.js` didLoadWithEvents | `ColdStartCoordinator` | `setAnswerUUID()`, `setDeclineUUID()`, `setAudioSessionActivated()`, `setCallData()` | WIRED | Lines 37, 43, 49, 87 — all 4 setter calls confirmed |
| `App.tsx` coordinator useEffect | `ColdStartCoordinator.run()` | Direct method call | WIRED | Line 344: `ColdStartCoordinator.run()` called when `isSetupComplete && isActive && !isHandled` |
| `App.tsx` incoming-call handler | `ColdStartCoordinator.handleIncomingCallDuringColdStart()` | EventBus incoming-call event | WIRED | Lines 185-188: delegates to `handleIncomingCallDuringColdStart(data)` before overlay flow |
| `ColdStartCoordinator.run()` PATH A | `SignalingClient.setCachedTurnServers()` | VoIP push turnServers | WIRED | Lines 163-166 in ColdStartCoordinator.ts |
| `ColdStartCoordinator.run()` PATH B | `SignalingClient.setCachedTurnServers()` | server call-state turnServers | WIRED | Lines 227-230 in ColdStartCoordinator.ts |
| `CallScreen.startCall()` | `ColdStartCoordinator.wasAudioSessionActivated` | Property getter | WIRED | Line 333: `if (ColdStartCoordinator.wasAudioSessionActivated)` |
| `CallScreen.startCall()` | `ColdStartCoordinator.hasAnswer` (InCallManager guard) | Property getter | WIRED | Line 236: `const isColdStartIncoming = isIncoming && ColdStartCoordinator.hasAnswer` |
| `server/index.js` offer to offline callee | `getCachedTurnServers()` then `call.turnServers = servers` | Promise chain | WIRED | Lines 942-945: async TURN population for VoIP push path |
| `server/push.js` sendVoIPPush | `callData.turnServers` | Payload embedding | WIRED | Lines 372-373: TURN embedded in VoIP push payload |
| `MessagingService.ts` offer handler | `ColdStartCoordinator.isHandled` | Duplicate suppression guard | WIRED | Line 269: returns early if already handled |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `CallScreen.tsx` — TURN pre-fetch bypass | `cachedTurn` from `SignalingClient.getCachedTurnServers()` | ColdStartCoordinator caches from VoIP push (PATH A) or server call-state (PATH B) | Yes — real TURN credentials from Metered API or env vars | FLOWING |
| `CallScreen.tsx` — InCallManager guard | `ColdStartCoordinator.hasAnswer` | Set from `index.js` didLoadWithEvents (RNCallKeepPerformAnswerCallAction) | Yes — real CallKit UUID from native layer | FLOWING |
| `CallScreen.tsx` — RTCAudioSession re-notification | `ColdStartCoordinator.wasAudioSessionActivated` | Set from `index.js` didLoadWithEvents (RNCallKeepDidActivateAudioSession) | Yes — real AVAudioSession activation event from CallKit | FLOWING |
| `server/index.js` — get-call-state response | `activeCall.turnServers` | `getCachedTurnServers()` with Metered API or env var fallback | Yes — real TURN credentials | FLOWING |

---

### Behavioral Spot-Checks

Step 7b: SKIPPED — cold start call flow requires a physical device with VoIP push delivery; cannot be invoked from CLI without running server and real iOS device.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| COLD-01 | 20-01-PLAN (completed in 20-02 per summary) | On cold start, InCallManager.stop() is skipped for incoming calls (does not deactivate audio session before answerCall()) | SATISFIED | `CallScreen.tsx:236-241`: `isColdStartIncoming = isIncoming && ColdStartCoordinator.hasAnswer` guards skip; confirmed by "InCallManager.stop() SKIPPED" log message |
| COLD-02 | 20-02-PLAN | After answerCall() creates peer connection, RTCAudioSession.audioSessionDidActivate() is called to re-notify WebRTC of already-active audio session | SATISFIED | `CallScreen.tsx:333-337`: `if (ColdStartCoordinator.wasAudioSessionActivated)` post-answerCall calls `RTCAudioSession.audioSessionDidActivate()` |
| COLD-03 | 20-01-PLAN + 20-03-PLAN | TURN credentials are pre-fetched during cold start coordinator (before CallScreen mount), eliminating 3s wait | SATISFIED | `ColdStartCoordinator.ts:142-148`: `requestTurnCredentials()` called at run() start; PATH A and PATH B both call `SignalingClient.setCachedTurnServers()` so CallScreen's `if (!cachedTurn || cachedTurn.length === 0)` check at line 302 is bypassed |
| COLD-04 | 20-01-PLAN | didLoadWithEvents handler exists only in one place (index.js), removing fragile dual-handler in CallKitService | SATISFIED | `index.js:92` is the single registration; `grep -rn "addEventListener.*didLoadWithEvents" src/` returns zero results; CallKitService comment line 36 confirms: "index.js writes to ColdStartCoordinator in didLoadWithEvents" |

All 4 requirement IDs (COLD-01, COLD-02, COLD-03, COLD-04) are accounted for across the 3 plans.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `index.js` | 23-29 | `global.__coldStartCall` proxy still assigned | Info | Backward-compat proxy; read-only getters only; no stale state — safe but could be removed in a future cleanup |
| `CallScreen.tsx` | 302-319 | 3s TURN wait still present as fallback | Info | Only triggered when `cachedTurn` is empty; in cold start with coordinator, cache is populated before CallScreen mount so this path is inactive for the primary flow. Serves as safety net for edge cases. |
| `index.js` | 23-24 | Comment says "Needed because CallScreen.tsx reads global.__coldStartCall" — CallScreen no longer does this | Info | Stale comment only; no functional impact |

No blocker or warning anti-patterns found.

---

### Human Verification Required

#### 1. End-to-End Cold Start Audio Test (Physical Device)

**Test:** Kill QRChat on an iPhone (swipe up from app switcher). From another device, initiate an incoming call to the test phone. On the test phone, tap "Answer" in the native CallKit UI (lock screen or banner).
**Expected:** Audio begins flowing within 8 seconds of tapping Answer. Call status transitions to "connected". Both parties can hear each other. No "no audio" symptom.
**Why human:** Requires physical iPhone with VoIP push (APNs), real CallKit native layer, AVAudioSession, and RTCAudioBridge native module. Cannot be verified programmatically.

#### 2. Cold Start Audio State Cleanup for Subsequent Calls

**Test:** Complete a cold start call normally (both parties hang up). Without killing the app, initiate a second incoming call.
**Expected:** The second call does NOT skip InCallManager.stop() (because `ColdStartCoordinator.wasAudioSessionActivated` was cleared to `false` after the first cold start). Audio works correctly on the second call too.
**Why human:** Requires sequential call lifecycle testing on device; depends on runtime state between calls.

#### 3. TURN Pre-Fetch Eliminates Wait Window

**Test:** With network logs enabled (`[ColdStart]` prefix), answer a cold start call and check Xcode Console / LogService output.
**Expected:** Log shows "PATH A: Cached N TURN servers from VoIP push" OR "PATH B: Cached N TURN servers from server call-state" before "answerCall starting...". The "Waiting for TURN credentials" log should NOT appear.
**Why human:** Log analysis on device required; depends on actual VoIP push payload content.

---

### Gaps Summary

No gaps found. All 4 requirements are fully implemented and wired:

- **COLD-01**: InCallManager.stop() skip is gated by `ColdStartCoordinator.hasAnswer` — exists, is substantive, and the data flows from a real native CallKit event via index.js didLoadWithEvents.
- **COLD-02**: RTCAudioSession re-notification fires post-answerCall only when `wasAudioSessionActivated` is true — exists, is substantive, state is set from a real didActivateAudioSession CallKit event, and is cleared after use to prevent stale state.
- **COLD-03**: TURN credentials are cached in SignalingClient before CallScreen mounts via ColdStartCoordinator PATH A (VoIP push) and PATH B (server call-state). The server embeds real TURN creds (Metered API or env var fallback) in both VoIP push and get-call-state responses. The 3s wait in CallScreen is a conditional that resolves immediately when cache is populated.
- **COLD-04**: `didLoadWithEvents` is registered exclusively in `index.js` (line 92). Zero registrations found in `src/services/CallKitService.ts` or any other source file. The fragile dual-handler pattern is eliminated.

All 6 commits (a61d2b1, a7ee2a8, deb1fbb, 13337bc, 942efba, 6dadcd7) are verified present in the QRChat git history.

---

_Verified: 2026-03-30T06:30:00Z_
_Verifier: Claude (gsd-verifier)_
