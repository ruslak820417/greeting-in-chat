# QRChat Call System: Deep Technical Audit

**Date:** 2026-03-26
**Auditor:** Claude Opus 4.6
**Project:** QRChat v3.0.6
**Reported Issue:** "Calls connect but drop, especially on cold start -- CallKit appears but audio never starts."

---

## 1. Complete Call Flow Diagrams

### 1A. Normal (Warm Start) Outgoing Call

```
Caller                          Server                          Callee
  |                               |                               |
  |-- getUserMedia() ------------>|                               |
  |   (get audio track)          |                               |
  |-- createPeerConnection() --->|                               |
  |-- addTrack(localStream) ---->|                               |
  |-- createOffer() ------------>|                               |
  |-- setLocalDescription() ---->|                               |
  |-- sendOffer(isCall:true) --->|-- forward offer ------------->|
  |                               |-- activeCalls.set() -------->|
  |                               |                               |-- CallKitService.reportIncomingCall()
  |                               |                               |-- IncomingCallOverlay shown
  |                               |                               |
  |                               |                               |<-- User taps Answer
  |                               |                               |-- getUserMedia()
  |                               |                               |-- createPeerConnection()
  |                               |                               |-- addTrack(localStream)
  |                               |                               |-- setRemoteDescription(offer)
  |                               |                               |-- drainIceCandidateQueue()
  |                               |                               |-- createAnswer()
  |                               |                               |-- setLocalDescription(answer)
  |                               |<-- sendAnswer() -------------|
  |<-- forward answer ------------|                               |
  |-- setRemoteDescription() --->|                               |
  |-- drainIceCandidateQueue() ->|                               |
  |                               |                               |
  |<============ ICE candidates exchanged bidirectionally ========>|
  |                               |                               |
  |<==== DTLS handshake + SRTP media flows ======================>|
  |                               |                               |
  |-- onconnectionstatechange:   |                               |
  |   'connected' => timer start |                               |
```

### 1B. Cold Start (App Killed) Incoming Call

```
Caller                    Server                   Native iOS              JS Runtime
  |                         |                         |                       |
  |-- sendOffer(isCall) --->|                         |                       |  (APP KILLED)
  |                         |-- activeCalls.set() --->|                       |
  |                         |-- sendVoIPPush() ------>|                       |
  |                         |  (APNs priority:10)     |                       |
  |                         |                         |-- didReceiveIncoming  |
  |                         |                         |   PushWith payload    |
  |                         |                         |-- Save SDP+callInfo  |
  |                         |                         |   to UserDefaults    |
  |                         |                         |-- RNCallKeep.report  |
  |                         |                         |   NewIncomingCall()  |
  |                         |                         |-- CallKit UI shows   |
  |                         |                         |                       |
  |                         |                         |<-- User taps Answer   |
  |                         |                         |                       |
  |                         |                         |-- index.js boots      |
  |                         |                         |   (onAnswerCall sets  |
  |                         |                         |    __coldStartCall    |
  |                         |                         |    .answerUUID)       |
  |                         |                         |   (didActivateAudio   |
  |                         |                         |    Session fires)     |
  |                         |                         |-- RTCAudioSession.    |
  |                         |                         |   audioSessionDid     |
  |                         |                         |   Activate() called  |
  |                         |                         |  (NO peer connection) |
  |                         |                         |                       |
  |                         |                         |              App.tsx mounts
  |                         |                         |              checkSetup():
  |                         |                         |                MessagingService.init()
  |                         |                         |                CallKitService.init()
  |                         |                         |                isSetupComplete = true
  |                         |                         |                       |
  |                         |                         |              Cold Start Coordinator:
  |                         |                         |              PATH A: getPendingVoIPCall()
  |                         |                         |                (read SDP from UserDefaults)
  |                         |                         |                       |
  |                         |                         |   if SDP found:       |
  |                         |                         |     navigateToCallScreen()
  |                         |                         |     sendCallAcceptedPending()
  |                         |                         |                       |
  |<-- call-accepted-pending|                         |                       |
  |   (stop ringing)        |                         |                       |
  |                         |                         |              CallScreen mounts:
  |                         |                         |                getUserMedia()
  |                         |                         |                wait for TURN (3s timeout)
  |                         |                         |                answerCall()
  |                         |                         |                re-activate audio session
  |                         |                         |                InCallManager.start()
```

### 1C. Cold Start Three-Path Coordinator (App.tsx)

```
isSetupComplete = true
        |
        v
hasColdStartAnswer? ----NO----> return (not cold start)
        |
       YES
        |
        v
+------- PATH A: getPendingVoIPCall() --------+
| Read SDP from UserDefaults (saved by native) |
| If SDP found:                                |
|   navigateToColdStartCall()                  |
|   return                                     |
+----------------------------------------------+
        |
     NO SDP
        |
        v
+------- PATH B: WebSocket get-call-state -----+
| If WS not connected: initializeFastPath()     |
|   (connect WS, wait for 'registered', 8s max) |
| Send 'get-call-state' to server               |
| Wait for response (5s timeout)                 |
| If SDP found:                                  |
|   navigateToColdStartCall()                    |
|   return                                       |
+-----------------------------------------------+
        |
     NO SDP
        |
        v
+------- PATH C: Fallback ----------------------+
| Wait for offer via pending queue flush         |
| MessagingService 'offer' handler fires         |
| hasColdStartAnswer() => skip overlay           |
| Navigate to CallScreen                         |
+-----------------------------------------------+
```

---

## 2. Identified Issues (Ranked by Severity)

---

### CRITICAL-1: AVAudioSession activated BEFORE WebRTC peer connection exists -- audio never flows

**Severity: CRITICAL -- PRIMARY CAUSE of "CallKit appears but audio never starts"**

**Files:**
- `/Users/ruslanconstantinovici/QRChat/index.js` lines 38-48
- `/Users/ruslanconstantinovici/QRChat/src/screens/CallScreen.tsx` lines 285-290

**The Problem:**

In `index.js`, when `didActivateAudioSession` fires during cold start, the code calls `RTCAudioSession.audioSessionDidActivate()` immediately (line 44). However, at this point NO WebRTC peer connection exists -- the peer connection is created much later when `CallScreen.startCall()` runs `WebRTCManager.answerCall()`.

The sequence:
1. CallKit activates audio session -> `didActivateAudioSession` fires in `index.js`
2. `index.js` calls `RTCAudioSession.audioSessionDidActivate()` -- but no peer connection exists
3. `global.__coldStartCall.audioSessionActivated = true`
4. ...seconds pass (JS boot, profile load, WS connect)...
5. `CallScreen` mounts, calls `getUserMedia()`, creates peer connection
6. `CallScreen` checks `__coldStartCall.audioSessionActivated` (line 285) -- it IS true
7. Calls `RTCAudioSession?.audioSessionDidActivate?.()` AGAIN

**The critical issue:** `react-native-webrtc` does NOT export `RTCAudioSession` from its JS module. The export list is: `RTCPeerConnection`, `RTCSessionDescription`, `RTCIceCandidate`, `mediaDevices`, `RTCView`. The optional chaining (`?.`) makes every call to `RTCAudioSession` a silent no-op:

```typescript
// index.js line 42-46 -- DEAD CODE (RTCAudioSession is undefined)
try {
  const { RTCAudioSession } = require('react-native-webrtc');
  if (RTCAudioSession?.audioSessionDidActivate) {
    RTCAudioSession.audioSessionDidActivate();  // Never executes
  }
} catch (e) {}

// CallScreen.tsx line 285-290 -- ALSO DEAD CODE
if ((global as any).__coldStartCall?.audioSessionActivated) {
  try {
    const { RTCAudioSession } = require('react-native-webrtc');
    RTCAudioSession?.audioSessionDidActivate?.();  // Never executes
    console.log('[CallScreen] Re-activated audio session for cold start call');
  } catch (e) {}
}
```

The real mechanism for CallKit audio activation to reach WebRTC is through the native `RTCAudioSession` singleton, which observes `AVAudioSessionInterruptionNotification` posted by `react-native-callkeep`'s native delegate. But on cold start, this notification fires BEFORE WebRTC's native audio unit is initialized, so WebRTC misses it entirely. The JS re-activation code was meant to solve this but uses a non-existent API.

**Recommended Fix:**
After `answerCall()` completes and the peer connection is created, use `InCallManager` or a custom native module to re-configure AVAudioSession:

```typescript
// After WebRTCManager.answerCall() completes:
InCallManager.stop();
InCallManager.start({ media: 'audio' });
// Force audio route
InCallManager.setForceSpeakerphoneOn(false);
```

Or create a native module that calls:
```swift
let session = AVAudioSession.sharedInstance()
try session.setCategory(.playAndRecord, mode: .voiceChat, options: [.allowBluetooth])
try session.setActive(true)
```

---

### CRITICAL-2: Race condition -- TURN credentials unavailable during cold-start answerCall()

**Severity: CRITICAL**

**Files:**
- `/Users/ruslanconstantinovici/QRChat/src/screens/CallScreen.tsx` lines 259-280
- `/Users/ruslanconstantinovici/QRChat/src/utils/constants.ts` lines 46-75
- `/Users/ruslanconstantinovici/QRChat/src/network/SignalingClient.ts` line 430

**The Problem:**

TURN credentials arrive via WebSocket AFTER registration (`requestTurnCredentials()` called in `handleMessage` on `registered` event, SignalingClient line 430). The cold start coordinator PATH A obtains the SDP from UserDefaults without involving the WebSocket at all. It then navigates to CallScreen, which must create a peer connection.

`CallScreen` line 262-280 polls for TURN credentials with a 3-second timeout:
```typescript
if (!SignalingClient.getCachedTurnServers() || ...) {
  await new Promise<void>((resolve) => {
    const turnTimeout = setTimeout(() => {
      console.warn('[ColdStart] TURN credentials timeout -- proceeding with STUN-only');
      resolve();  // Falls back to STUN-only
    }, 3000);
    const turnCheck = setInterval(() => {
      const cached = SignalingClient.getCachedTurnServers();
      if (cached && cached.length > 0) { clearInterval(turnCheck); clearTimeout(turnTimeout); resolve(); }
    }, 200);
  });
}
```

If WebSocket hasn't connected and registered by then, TURN creds never arrive. The peer connection is created with STUN-only servers (`getIceServers()` in constants.ts returns only `STUN_SERVERS` as last resort, line 73-74).

For users behind symmetric NAT (common on mobile carriers), STUN-only means ICE will fail completely -- the connection drops.

**Recommended Fix:**
Pre-fetch TURN credentials during the cold start coordinator, BEFORE navigating to CallScreen. If WebSocket is connected, wait for TURN credentials specifically (not just registration). If not, use the HTTP fallback in `getIceServers()`.

---

### CRITICAL-3: Server disconnection cleanup prematurely ends calls during cold start

**Severity: CRITICAL**

**Files:**
- `/Users/ruslanconstantinovici/QRChat/server/index.js` lines 1194-1221

**The Problem:**

When a WebSocket disconnects, the server immediately cleans up active calls:

```javascript
ws.on('close', () => {
  if (userId) {
    clients.delete(userId);
    for (const [calleeId, call] of activeCalls.entries()) {
      if (call.from === userId) {
        peerWs.send(JSON.stringify({ type: 'call-ended', from: userId }));
        activeCalls.delete(calleeId);
      }
      if (calleeId === userId) {
        peerWs.send(JSON.stringify({ type: 'call-ended', from: userId }));
        activeCalls.delete(calleeId);
      }
    }
  }
});
```

During cold start, the callee's WebSocket may disconnect briefly:
- `MessagingService.initialize()` calls `WebRTCManager.initialize()` which calls `SignalingClient.connect()`
- If there's already a stale connection, or the WS disconnects during cold start setup
- The disconnect triggers server cleanup -> sends `call-ended` to caller
- Caller receives `call-ended` -> terminates the call

This is especially dangerous because:
- The cold start coordinator in PATH B calls `initializeFastPath()` which connects the WS
- If `MessagingService.initialize()` (called from `checkSetup()`) runs concurrently and also tries to connect, there could be conflicting WS states
- `hardReconnect()` explicitly closes the WS and reconnects -- this would trigger the server cleanup

**Recommended Fix:**
Add a 5-10 second grace period on the server before sending `call-ended` on WS disconnect. Track the disconnect timestamp and only clean up if the user doesn't reconnect within the grace period:

```javascript
ws.on('close', () => {
  // Delay call cleanup -- user may reconnect (cold start, network switch)
  setTimeout(() => {
    if (!clients.has(userId)) {  // Still disconnected after grace period
      // Clean up active calls
    }
  }, 5000);
});
```

---

### HIGH-1: `call-accepted-pending` sent before WebSocket connected (PATH A)

**Severity: HIGH**

**Files:**
- `/Users/ruslanconstantinovici/QRChat/App.tsx` lines 366-368

**The Problem:**

In PATH A, SDP comes from UserDefaults (VoIP push), not WebSocket. The coordinator immediately calls:
```typescript
SignalingClientRef.sendCallAcceptedPending(callFrom);
```

But SignalingClient may not be connected. The message is queued (SignalingClient line 292-296) with a 30-second expiry. This means:
- The caller keeps showing "Ringing..." with ringback tone for several extra seconds
- If WS connects within 30s (likely), the message flushes and caller sees "Connecting..."
- In worst case, the queued message expires and is never delivered

**Recommended Fix:**
Check `SignalingClient.isConnected()` before sending. If not connected, defer until connection is established.

---

### HIGH-2: Duplicate call offer arrives from pending queue after PATH A already consumed it

**Severity: HIGH**

**Files:**
- `/Users/ruslanconstantinovici/QRChat/src/network/WebRTCManager.ts` lines 735-746
- `/Users/ruslanconstantinovici/QRChat/src/services/MessagingService.ts` lines 270+

**The Problem:**

PATH A gets the SDP from UserDefaults. CallScreen answers the call. Meanwhile, the WebSocket connects, and the server flushes the pending message queue which includes the SAME offer. This triggers:
1. `handleOffer()` in WebRTCManager -> `pendingCallPeers.add(from)` (line 743)
2. New ICE candidates from the caller are now queued because `pendingCallPeers` has the contact
3. But CallScreen already called `answerCall()` which did `pendingCallPeers.delete(from)` (line 386)

If the pending queue offer arrives AFTER `answerCall()`, it re-adds the contact to `pendingCallPeers`, causing subsequent ICE candidates to be queued instead of applied. The call connects via DTLS but ICE may degrade or fail to add new relay candidates.

Similarly, `MessagingService` fires `incoming-call` EventBus event for the duplicate offer. App.tsx has a guard (`coldStartHandledRef.current`), but the guard is checked in the `incoming-call` handler (line 166). If the handler runs before the coordinator sets `coldStartHandledRef.current = true`, there could be a race.

**Recommended Fix:**
After `answerCall()` completes, set a flag in WebRTCManager that suppresses `handleOffer` for the same contact for the next 30 seconds. Or have the server NOT flush pending call offers when it detects an active call that's already in "accepted-pending" status.

---

### HIGH-3: Cumulative cold start latency can exceed 15 seconds

**Severity: HIGH**

**Files:** Multiple

**The Problem:**

Worst-case cold start timeline:
- JS boot: ~2-3 seconds
- `checkSetup()` (DB load, MessagingService init, CallKit init): ~1-2 seconds
- Cold start coordinator runs:
  - PATH A fails (SDP too large for VoIP push, or parse error): ~instant
  - PATH B: `initializeFastPath()` -- 8s timeout for WS + `get-call-state` 5s timeout
- Navigate to CallScreen
- CallScreen: TURN wait: 3s timeout
- `answerCall()` + ICE: 1-2 seconds

**Total: up to 20 seconds** from user tapping Answer to audio flowing. The caller shows "Ringing..." for 15+ seconds (minus the `call-accepted-pending` arrival time), which feels broken. The caller's 60-second timeout provides buffer, but users will hang up long before.

**Recommended Fix:**
- Pipeline TURN fetch into the coordinator (start it immediately, don't wait for CallScreen)
- Reduce PATH B `get-call-state` timeout from 5s to 3s
- Reduce TURN wait from 3s to 1.5s
- Consider sending the WebRTC answer with STUN-only immediately, then ICE restart with TURN when credentials arrive

---

### HIGH-4: Duplicate `didLoadWithEvents` handlers in index.js and CallKitService

**Severity: HIGH**

**Files:**
- `/Users/ruslanconstantinovici/QRChat/index.js` lines 73-80
- `/Users/ruslanconstantinovici/QRChat/src/services/CallKitService.ts` lines 41-43, 51-71

**The Problem:**

Both register `didLoadWithEvents`:
```javascript
// index.js line 73
RNCallKeep.addEventListener('didLoadWithEvents', (events) => { ... });

// CallKitService constructor, line 42
RNCallKeep.addEventListener('didLoadWithEvents', this.onDidLoadWithEvents);
```

Both independently set `coldStartAnswerUUID`:
- `index.js` sets `global.__coldStartCall.answerUUID`
- `CallKitService` sets `this.coldStartAnswerUUID`

App.tsx checks BOTH:
```typescript
const hasColdAnswer = CallKitService.hasColdStartAnswer() ||
  (global as any).__coldStartCall?.answerUUID;
```

This works but is fragile. If `CallKitService.consumeColdStartAnswer()` runs first, it returns the UUID and clears `CallKitService.coldStartAnswerUUID`. But `global.__coldStartCall.answerUUID` is still set. If the coordinator then tries to consume it again for some reason, there's stale state.

**Recommended Fix:**
Remove `didLoadWithEvents` from `CallKitService.ts`. Let `index.js` be the sole handler for cold-start events. The `CallKitService.onAnswerCall` handler (line 224) already handles the warm-start case.

---

### MEDIUM-1: `InCallManager.stop()` before `start()` may disrupt cold-start audio session

**Severity: MEDIUM**

**Files:**
- `/Users/ruslanconstantinovici/QRChat/src/screens/CallScreen.tsx` lines 226, 297

**The Problem:**

```typescript
// Line 226 -- "Reset audio state from any previous call"
try { InCallManager.stop(); } catch (e) {}

// ...later, line 297
InCallManager.start({ media: isVideo ? 'video' : 'audio' });
```

On cold start, CallKit has already activated the audio session with `.voiceChat` mode. `InCallManager.stop()` deactivates the audio session (calls `AVAudioSession.setActive(false)`). Then `InCallManager.start()` re-activates it. But between `stop()` and `start()`, WebRTC may attempt to use the audio session and find it inactive. This is especially problematic because `answerCall()` (line 282) runs BEFORE `InCallManager.start()` (line 297).

Timeline:
1. `InCallManager.stop()` -- deactivates audio session
2. `answerCall()` -- creates peer connection, adds tracks, creates answer
3. WebRTC native layer tries to start audio -- but session is inactive
4. `InCallManager.start()` -- reactivates audio session
5. WebRTC audio never recovers because its audio unit initialization failed

**Recommended Fix:**
For cold-start incoming calls, skip `InCallManager.stop()`:
```typescript
if (!isIncoming || !(global as any).__coldStartCall?.answerUUID) {
  try { InCallManager.stop(); } catch (e) {}
}
```

---

### MEDIUM-2: SDP may exceed VoIP push 5KB limit, forcing slower PATH B

**Severity: MEDIUM**

**Files:**
- `/Users/ruslanconstantinovici/QRChat/server/push.js` lines 370-378

**The Problem:**

```javascript
const testSize = Buffer.byteLength(JSON.stringify({ ...payloadObj, sdp: sdpStr }), 'utf8');
if (testSize < 4500) {
  payloadObj.sdp = sdpStr;
} else {
  console.warn('[Push] SDP too large for VoIP payload');
}
```

Video call SDPs with multiple codecs can easily exceed 4.5KB. When this happens, PATH A fails silently (no SDP in UserDefaults), and the cold start falls through to the much slower PATH B.

**Recommended Fix:**
Minify the SDP before including it: strip `a=extmap` lines, remove unused codecs, compress `a=candidate` lines. Alternatively, send a compressed/base64 version.

---

### MEDIUM-3: TURN credential delivery can be double-sent (static + Metered API async)

**Severity: MEDIUM**

**Files:**
- `/Users/ruslanconstantinovici/QRChat/server/index.js` lines 1000-1052

**The Problem:**

The server sends static TURN credentials immediately AND kicks off an async Metered API fetch. The client receives two `turn-credentials` messages. `SignalingClient` (line 442) overwrites `cachedTurnServers` each time. If the first (static) set has working credentials and is used by `createPeerConnection`, but the second (Metered) set overwrites them mid-ICE, it could cause inconsistency. However, since `getIceServers()` is called per-connection (not dynamically updated), this is low risk.

---

### LOW-1: `sendCallEnded` retry timer is not tracked or cleaned up

**Severity: LOW**

**Files:**
- `/Users/ruslanconstantinovici/QRChat/src/network/WebRTCManager.ts` lines 401-411

```typescript
if (!sent) {
  let retries = 0;
  const retryTimer = setInterval(() => {
    retries++;
    if (SignalingClient.sendCallEnded(contactId) || retries >= 3) {
      clearInterval(retryTimer);
    }
  }, 2000);  // Not tracked in callTimeouts, not cleaned in destroy()
}
```

**Recommended Fix:** Track the timer in `callTimeouts` map and clean it in `destroy()`.

---

### LOW-2: Stale call cleanup timeout mismatch across layers

**Severity: LOW**

**Files:**
- `CallKitService.ts` line 22: 60s
- `server/index.js` line 170: 60s
- `CallScreen.tsx` line 307: 60s

All three have 60s timeouts starting at different moments. The server may clean up the `activeCall` entry (deleting it from the Map) before the callee's cold start finishes, causing `get-call-state` to return `{ from: null }`.

**Recommended Fix:** Extend server's `ACTIVE_CALL_TIMEOUT` to 120s, or make it configurable.

---

## 3. Root Cause Summary

The reported issue ("Calls connect but drop, especially on cold start -- CallKit appears but audio never starts") is caused by a convergence of three critical issues:

| # | Issue | Effect |
|---|-------|--------|
| CRITICAL-1 | `RTCAudioSession` JS API does not exist -- all audio re-activation code is dead | Audio session activated by CallKit is never bridged to WebRTC's audio unit |
| CRITICAL-2 | TURN credentials unavailable during cold-start `answerCall()` | ICE fails for users behind symmetric NAT, connection drops |
| CRITICAL-3 | Server sends `call-ended` immediately on WS disconnect during cold start | Call terminated before audio can flow |
| MEDIUM-1 | `InCallManager.stop()` deactivates audio session before `answerCall()` | WebRTC audio unit fails to initialize |
| HIGH-3 | 15-20 second cold start latency | Users hang up, or caller timeout fires |

The most likely single scenario:
1. VoIP push wakes app, CallKit shows UI
2. User taps Answer
3. Audio session activates (CallKit) -- but no WebRTC peer yet
4. JS boots, cold start coordinator runs
5. `InCallManager.stop()` deactivates the audio session
6. `answerCall()` creates peer connection -- audio unit finds session inactive
7. `RTCAudioSession?.audioSessionDidActivate?.()` is a no-op (export doesn't exist)
8. `InCallManager.start()` re-activates session, but WebRTC audio unit already failed initialization
9. Result: call is "connected" (ICE works, DTLS completes) but audio never flows

---

## 4. Recommended Priority Fixes

| Priority | Fix | Files to Modify | Impact |
|----------|-----|-----------------|--------|
| **P0** | Fix audio session handling: move `InCallManager.stop()` AFTER the cold-start check. For cold start, skip `stop()` entirely. After `answerCall()`, call `InCallManager.start()` BEFORE the peer starts consuming audio. | `CallScreen.tsx` lines 226, 282-297 | Fixes primary "no audio" issue |
| **P0** | Remove dead `RTCAudioSession` code. Replace with proper native module that calls `AVAudioSession.setCategory(.playAndRecord, mode: .voiceChat)` + `setActive(true)` after peer connection exists. | `index.js`, `CallScreen.tsx` | Ensures audio session is properly configured |
| **P0** | Add 5-10 second grace period on server WS disconnect before sending `call-ended` | `server/index.js` line 1194-1221 | Prevents premature call termination during cold start |
| **P1** | Pre-fetch TURN credentials in cold start coordinator (before CallScreen mount) | `App.tsx` cold start coordinator | Eliminates 3s TURN wait in CallScreen |
| **P1** | Skip `InCallManager.stop()` for cold-start incoming calls | `CallScreen.tsx` line 226 | Prevents audio session disruption |
| **P1** | Deduplicate `didLoadWithEvents` -- keep only `index.js`, remove from `CallKitService` | `CallKitService.ts` lines 41-43, 51-71 | Removes fragile dual-handler pattern |
| **P2** | Suppress duplicate offer from pending queue when call already accepted | `WebRTCManager.ts`, `server/index.js` | Prevents ICE candidate routing confusion |
| **P2** | Reduce cold start timeouts (TURN 3s->1.5s, get-call-state 5s->3s) | `CallScreen.tsx`, `App.tsx` | Faster cold start |
| **P2** | Minify SDP in VoIP push payload to fit under 4.5KB | `server/push.js` | More frequent PATH A success |
| **P3** | Track `sendCallEnded` retry timer in `callTimeouts` | `WebRTCManager.ts` line 405 | Minor leak fix |
| **P3** | Extend server `ACTIVE_CALL_TIMEOUT` to 120s | `server/index.js` line 170 | Prevents stale cleanup during slow cold start |
