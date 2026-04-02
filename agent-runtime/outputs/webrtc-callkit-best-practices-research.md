# WebRTC + CallKit/PushKit Best Practices for React Native
## Production-Grade Encrypted Messenger (WhatsApp/Signal/Telegram class)

**Research Date:** 31 March 2026
**Target:** QRChat v4.3.0 (Build 100)
**Stack:** React Native 0.84, react-native-webrtc, react-native-callkeep, Node.js signaling server

---

## Table of Contents

1. [React Native WebRTC Best Practices](#1-react-native-webrtc-best-practices)
2. [CallKit + PushKit Integration](#2-callkit--pushkit-integration)
3. [Signal App Architecture Reference](#3-signal-app-architecture-reference)
4. [Offer/Answer Exchange Patterns](#4-offeranswer-exchange-patterns)
5. [ICE Candidate Handling](#5-ice-candidate-handling)
6. [Audio Session Management on iOS](#6-audio-session-management-on-ios)
7. [Node.js Signaling Server](#7-nodejs-signaling-server)
8. [Common Pitfalls & Solutions](#8-common-pitfalls--solutions)
9. [QRChat Gap Analysis](#9-qrchat-gap-analysis)

---

## 1. React Native WebRTC Best Practices

### 1.1 Known Issues with react-native-webrtc

| Issue | Impact | Mitigation |
|-------|--------|------------|
| Static ExecutorService in ThreadUtils causes resource leaks on JS Reload | Memory leak on hot reload (dev only) | Ignore in production, restart app during dev |
| RTCDataChannel does not fire close event on iOS/Android | Stale channel references | Track channel state manually, use connection state as ground truth |
| Audio session conflicts with CallKit | No audio, one-way audio | Use `useManualAudio = true` (see Section 6) |
| WebRTC auto-configures AVAudioSession | Fights CallKit's audio session management | `useManualAudio = true` prevents this |
| H264 codec bug with remote SDP | Video codec mismatch on some devices | Use VP8 as fallback, or prefer Opus/VP8 in SDP preferences |
| PeerConnection not closing properly in background | Resource leak, battery drain | Nullify all event handlers BEFORE calling .close() |

### 1.2 Proper WebRTC Initialization Sequence

```
1. App starts (index.js)
   -> Set RTCAudioSession.useManualAudio = true
   -> Set RTCAudioSession.isAudioEnabled = false
   -> Register CallKeep event listeners (didLoadWithEvents for cold start)

2. User opens app (App.tsx mount)
   -> Initialize SignalingClient (WebSocket connection)
   -> Initialize WebRTCManager (attach signaling handlers)
   -> Request TURN credentials via WebSocket

3. Call initiated (outgoing) or received (incoming)
   -> Create RTCPeerConnection with ICE servers (STUN + TURN)
   -> Add media tracks to connection
   -> Create offer/set remote description
   -> Exchange ICE candidates

4. CallKit activates audio session
   -> RTCAudioSession.audioSessionDidActivate()
   -> RTCAudioSession.isAudioEnabled = true
   -> Audio flows through WebRTC
```

### 1.3 RTCPeerConnection Lifecycle Management

**CRITICAL RULE: One PeerConnection per call session. Never reuse.**

```typescript
// CREATION
const pc = new RTCPeerConnection({
  iceServers: [...stunServers, ...turnServers],
  iceCandidatePoolSize: 1,                    // Pre-allocate 1 ICE candidate
  continualGatheringPolicy: 'gatherContinually', // Signal's approach
});

// TEARDOWN (strict order)
1. Stop all media tracks:     stream.getTracks().forEach(t => t.stop())
2. Nullify event handlers:    pc.ontrack = null; pc.onicecandidate = null; ...
3. Close the connection:      pc.close()
4. Delete from tracking map:  peers.delete(contactId)
5. Clear ICE candidate queue: iceCandidateQueues.delete(contactId)
```

**Why nullify handlers before closing:** When `pc.close()` is called, it triggers state change events (connectionState -> 'closed', iceConnectionState -> 'closed'). If handlers are still attached, they may fire and cause ghost callbacks -- e.g., triggering an ICE restart on an already-closing connection, or calling `onCallDisconnected` which navigates away prematurely.

### 1.4 Memory Leak Prevention

- **Media tracks:** ALWAYS call `track.stop()` when done. `pc.close()` does NOT stop tracks.
- **Chunk buffers:** Set TTL on reassembly buffers (QRChat: 5 min). Clean periodically.
- **ICE candidate queues:** Clear on call end. Don't let them accumulate across calls.
- **Signaling handlers:** Store references. Remove on destroy/re-init. Prevent duplicate handlers.
- **Disconnect timers:** Clear all `setTimeout`/`setInterval` on teardown.

---

## 2. CallKit + PushKit Integration

### 2.1 The Apple Contract (Non-Negotiable)

Since iOS 13, Apple REQUIRES:

1. **Every VoIP push MUST call `reportNewIncomingCall()` synchronously in the push handler.** If you fail to do this, iOS kills your app. If it happens repeatedly, Apple stops delivering VoIP pushes entirely.

2. **The call must be reported BEFORE the push handler completion block returns.** You cannot defer this to JavaScript -- it MUST happen in native Swift/ObjC code.

3. **Maximum time budget: ~5 seconds.** From VoIP push arrival to `reportNewIncomingCall()`. In practice, do it in < 100ms.

### 2.2 VoIP Push Architecture (Production Pattern)

```
Server                          APNs                    iOS Device
  |                              |                         |
  |-- VoIP push (with SDP) ---->|                         |
  |                              |-- Wake app ----------->|
  |                              |                         |-- AppDelegate: didReceiveIncomingPushWith
  |                              |                         |   1. Parse payload (callerName, SDP, TURN)
  |                              |                         |   2. Store in UserDefaults (for JS cold start)
  |                              |                         |   3. reportNewIncomingCall() <-- IMMEDIATE
  |                              |                         |   4. completion()
  |                              |                         |
  |                              |                         |-- CallKit shows native UI
  |                              |                         |-- User taps Answer/Decline
  |                              |                         |-- React Native bridge initializes
  |                              |                         |-- index.js: didLoadWithEvents captures action
  |                              |                         |-- App.tsx mounts, reads cold start state
```

### 2.3 Cold Start Call Flow (The Hardest Problem)

When the app is killed and a VoIP push arrives, this is the sequence:

```
TIME  EVENT                                    WHO
0ms   VoIP push arrives                        iOS (native)
1ms   AppDelegate.didReceiveIncomingPushWith    Swift
2ms   Parse payload, store in UserDefaults      Swift
3ms   reportNewIncomingCall()                   Swift -> CallKit
50ms  CallKit UI appears on lock screen         iOS
---   User sees incoming call                   User
---   User taps Answer                          User
---   RNCallKeep buffers 'answerCall' event     Native
---   React Native JS bridge initializes        Hermes
---   index.js registers didLoadWithEvents      JS
---   didLoadWithEvents fires with buffered events  JS
---   ColdStartCoordinator stores answerUUID    JS
---   App.tsx mounts, runs cold start coordinator  JS
```

### 2.4 3-Path SDP Retrieval (QRChat's Production Pattern)

```
PATH A (fastest, ~20ms): Read SDP from UserDefaults (stored by VoIP push handler)
  - The VoIP push payload includes the SDP offer (if it fits in 5KB APNs limit)
  - Minify SDP before including in push payload
  - Also include TURN credentials in push payload

PATH B (fast, ~500ms): WebSocket get-call-state after reconnection
  - Server stores active call state: { from, offer, timestamp, turnServers }
  - Callee sends 'get-call-state' after WebSocket reconnects
  - Server responds immediately with stored SDP

PATH C (slow, ~2-5s): Pending message queue delivery
  - Server queued the offer in pending messages
  - After registration, server delivers all pending messages
  - The 'incoming-call' EventBus handler picks up the offer
  - This is the FALLBACK -- should rarely be needed
```

### 2.5 The "Active Foreground" Edge Case

When app is in foreground and VoIP push arrives (WebSocket already delivered the offer):

```swift
// Apple STILL requires reportNewIncomingCall for every VoIP push!
// Solution: report + immediately end the duplicate call silently
if appState == .active {
    let silentUUID = UUID().uuidString
    RNCallKeep.reportNewIncomingCall(silentUUID, ...)
    DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
        RNCallKeep.endCall(withUUID: silentUUID, reason: 2)
    }
    completion()
    return
}
```

### 2.6 VoIP Push Payload Optimization

APNs VoIP push limit: **5KB** (5120 bytes).

```json
{
  "from": "userId",
  "callerName": "Display Name",
  "isVideo": false,
  "sdp": "{minified SDP offer}",
  "turnServers": [
    {"urls": "turn:relay.example.com:443?transport=tcp", "username": "...", "credential": "..."}
  ]
}
```

**SDP Minification Techniques:**
- Remove blank lines and trailing whitespace
- Remove `a=ice-options:`, `a=extmap:`, `a=rtcp:` lines (non-essential for initial offer)
- Keep `m=`, `a=rtpmap:`, `a=fmtp:`, `c=`, `a=ice-ufrag:`, `a=ice-pwd:`, `a=fingerprint:`, `a=setup:`
- Typical SDP: ~2KB full -> ~1.2KB minified

---

## 3. Signal App Architecture Reference

### 3.1 RingRTC -- Signal's WebRTC Wrapper

Signal uses **RingRTC** (`github.com/signalapp/ringrtc`), a Rust-based middleware that wraps WebRTC:

- **Core logic in Rust** -- portable across iOS, Android, Desktop
- **iOS binding:** `src/ios/SignalRingRTC` (Swift framework linking `libringrtc.a`)
- **Custom WebRTC fork:** `github.com/signalapp/webrtc` (patches for E2EE, custom codecs)
- **SFU for group calls:** Custom Rust SFU supporting 40 participants

### 3.2 Signal's Call State Machine

Signal's call flow has explicit states:

```
IDLE
  -> OUTGOING_CALL_SETUP (caller creates offer)
    -> OUTGOING_RINGING (offer sent, waiting for answer)
      -> CONNECTING_AFTER_ACCEPTED (answer received, ICE in progress)
        -> CONNECTED (media flowing)
          -> ENDING (hang up initiated)
            -> ENDED (cleanup complete)

IDLE
  -> INCOMING_CALL_SETUP (offer received)
    -> INCOMING_RINGING (CallKit UI shown)
      -> CONNECTING_AFTER_ACCEPTED (user tapped answer)
        -> CONNECTED
          -> ENDING -> ENDED
```

**Key insight:** The `CONNECTING_AFTER_ACCEPTED` state was added specifically to fix a race condition on the caller's end -- after the callee accepts but before ICE completes.

### 3.3 Signal's Cold Start Approach

1. VoIP push wakes the app
2. `reportNewIncomingCall()` called synchronously in push handler
3. Call metadata stored in a native-accessible location
4. RingRTC initializes when JS bridge is ready
5. `useManualAudio = true` -- audio only starts when CallKit activates it
6. `continualGatheringPolicy = GATHER_CONTINUALLY` -- handles network changes
7. ICE candidates gathered continuously, not just at offer/answer time

### 3.4 Signal's Audio Architecture

Signal uses `RTCAudioSession` with manual control:
```swift
RTCAudioSession.sharedInstance().useManualAudio = true
RTCAudioSession.sharedInstance().isAudioEnabled = false

// When CallKit activates:
RTCAudioSession.sharedInstance().audioSessionDidActivate(AVAudioSession.sharedInstance())
RTCAudioSession.sharedInstance().isAudioEnabled = true

// When CallKit deactivates:
RTCAudioSession.sharedInstance().isAudioEnabled = false
RTCAudioSession.sharedInstance().audioSessionDidDeactivate(AVAudioSession.sharedInstance())
```

---

## 4. Offer/Answer Exchange Patterns

### 4.1 Correct Offer/Answer Sequence

```
CALLER (Peer A)                                CALLEE (Peer B)
     |                                              |
     |-- createOffer()                              |
     |-- setLocalDescription(offer)                 |
     |      (ICE gathering starts)                  |
     |-- send offer via signaling ----------------->|
     |                                              |-- setRemoteDescription(offer)
     |                                              |      (can now add ICE candidates)
     |                                              |-- createAnswer()
     |                                              |-- setLocalDescription(answer)
     |                                              |      (ICE gathering starts)
     |<--------------- send answer via signaling ---|
     |-- setRemoteDescription(answer)               |
     |      (can now add ICE candidates)            |
     |                                              |
     |<===== ICE candidates trickle both ways =====>|
     |                                              |
     |<========== Media flows (DTLS+SRTP) =========>|
```

### 4.2 Perfect Negotiation (Polite Peer Pattern)

The W3C-recommended pattern for handling offer collisions (glare):

```typescript
// Assign roles: one peer is "polite", the other is "impolite"
// Convention: the peer with the lower userId is polite
const isPolite = localUserId < remoteUserId;

// On receiving an offer:
async function handleOffer(offer: RTCSessionDescriptionInit) {
  const offerCollision = makingOffer || pc.signalingState !== 'stable';

  const ignoreOffer = !isPolite && offerCollision;
  if (ignoreOffer) return; // Impolite peer ignores incoming offer during collision

  if (offerCollision) {
    // Polite peer: rollback own offer and accept incoming
    await pc.setLocalDescription({ type: 'rollback' });
  }

  await pc.setRemoteDescription(offer);
  const answer = await pc.createAnswer();
  await pc.setLocalDescription(answer);
  signalingClient.sendAnswer(remotePeerId, answer);
}

// On creating an offer:
async function makeOffer() {
  try {
    makingOffer = true;
    const offer = await pc.createOffer();
    if (pc.signalingState !== 'stable') return; // State changed during createOffer
    await pc.setLocalDescription(offer);
    signalingClient.sendOffer(remotePeerId, pc.localDescription);
  } finally {
    makingOffer = false;
  }
}
```

**When glare happens:**
- Both peers send offers simultaneously
- The "polite" peer rolls back its offer and accepts the other's
- The "impolite" peer ignores the incoming offer and keeps its own
- Result: exactly one offer/answer exchange succeeds

### 4.3 Offer Rollback

```typescript
// Rollback is needed when:
// 1. Polite peer receives an offer while in 'have-local-offer' state
// 2. An offer needs to be abandoned before the answer arrives

await pc.setLocalDescription({ type: 'rollback' });
// signalingState returns to 'stable'
// Now safe to set the remote offer
```

**Rollback support:** Available in all modern WebRTC implementations (Chrome M87+, Safari 15+, react-native-webrtc).

### 4.4 SDP Munging for Codec Preferences

```typescript
// Preferred approach: use setCodecPreferences (no munging needed)
const transceiver = pc.getTransceivers().find(t => t.receiver.track?.kind === 'audio');
const codecs = RTCRtpReceiver.getCapabilities('audio')?.codecs || [];
const opus = codecs.filter(c => c.mimeType === 'audio/opus');
transceiver?.setCodecPreferences(opus);

// Opus configuration via SDP (when setCodecPreferences is not available):
// a=fmtp:111 minptime=10;useinbandfec=1;stereo=0;cbr=0;maxaveragebitrate=32000

// Key Opus parameters for VoIP:
// - minptime=10       -- minimum packet time (10ms for low latency)
// - useinbandfec=1    -- in-band Forward Error Correction (handles packet loss)
// - stereo=0          -- mono for voice calls (saves bandwidth)
// - cbr=0             -- variable bitrate (default, adapts to network)
// - maxaveragebitrate  -- cap bandwidth (32kbps for voice, 128kbps for music)
// - dtx=1             -- Discontinuous Transmission (silence suppression)
```

---

## 5. ICE Candidate Handling

### 5.1 Trickle ICE vs Full ICE

| Aspect | Trickle ICE | Full ICE |
|--------|------------|----------|
| **Speed** | Fast -- candidates sent as discovered | Slow -- wait for all candidates |
| **Connection time** | 500ms - 2s typical | 5-15s typical |
| **Complexity** | Higher (queuing, ordering) | Lower |
| **Standard** | RFC 8838 | RFC 8445 |
| **Recommendation** | USE THIS | Only for very simple scenarios |

**QRChat uses Trickle ICE** -- candidates are sent individually via `onicecandidate`.

### 5.2 ICE Candidate Queuing (CRITICAL)

The #1 race condition in WebRTC: **receiving ICE candidates before `setRemoteDescription()`**.

```typescript
// PROBLEM: Remote sends ICE candidates immediately after sending offer/answer.
// If your code hasn't called setRemoteDescription() yet, addIceCandidate() fails.

// SOLUTION: Queue candidates until remote description is set.
class ICECandidateQueue {
  private queue: Map<string, RTCIceCandidateInit[]> = new Map();

  enqueue(contactId: string, candidate: RTCIceCandidateInit) {
    if (!this.queue.has(contactId)) {
      this.queue.set(contactId, []);
    }
    this.queue.get(contactId)!.push(candidate);
  }

  async drain(contactId: string, pc: RTCPeerConnection) {
    const candidates = this.queue.get(contactId) || [];
    this.queue.delete(contactId);
    for (const candidate of candidates) {
      try {
        await pc.addIceCandidate(new RTCIceCandidate(candidate));
      } catch (e) {
        // Log but don't throw -- some candidates may be for closed connections
        console.warn(`Failed to add ICE candidate: ${e}`);
      }
    }
  }

  clear(contactId: string) {
    this.queue.delete(contactId);
  }
}
```

**When to queue vs apply immediately:**
- `pc.remoteDescription` is null -> QUEUE
- `pc.remoteDescription` is set -> APPLY IMMEDIATELY
- `pc.signalingState` is 'closed' -> DISCARD

### 5.3 ICE Restart for Network Changes

```typescript
// When to ICE restart:
// - connectionState === 'disconnected' (after 3s delay, it might recover)
// - connectionState === 'failed' (immediate restart)
// - Network change detected (WiFi -> Cellular)

async function performIceRestart(contactId: string, pc: RTCPeerConnection) {
  const offer = await pc.createOffer({ iceRestart: true });
  await pc.setLocalDescription(offer);
  signalingClient.sendOffer(contactId, {
    sdp: offer.sdp,
    type: offer.type,
    iceRestart: true, // Flag for remote peer
  });
}

// Limit retries to prevent infinite loops
const MAX_ICE_RESTARTS = 2; // Per call session, reset on new call
```

### 5.4 ICE Connection State Monitoring

```
States and what they mean:
  'new'           -- ICE agent created, no candidates yet
  'checking'      -- At least one candidate pair, checking connectivity
  'connected'     -- Found a working pair, but still checking for better ones
  'completed'     -- Best candidate pair found, checking stopped
  'disconnected'  -- Lost connectivity, may recover (WiFi blip, etc.)
  'failed'        -- All candidate pairs failed, manual intervention needed
  'closed'        -- ICE agent shut down

Handling strategy:
  'connected'/'completed' -> Mark call as active, start timer
  'disconnected'          -> Wait 3s, then attempt ICE restart
  'failed'                -> Immediate ICE restart (up to MAX_ICE_RESTARTS)
  'closed'                -> Clean up (normal teardown)
```

### 5.5 Continual Gathering (Signal's Approach)

```typescript
const config = {
  iceServers: [...],
  continualGatheringPolicy: 'gatherContinually', // KEY setting
  iceCandidatePoolSize: 1,
};
```

**What this does:**
- ICE gathering NEVER stops -- keeps discovering new candidates
- When network changes (WiFi -> 4G), new candidates are automatically discovered
- New candidates are sent to the remote peer without needing an ICE restart
- **More responsive** than ICE restart (which requires a new offer/answer round)
- **Signal uses this** -- it's their recommended approach

**Caveat:** You should also signal candidate removals (when network interfaces go away) to prevent the remote peer from trying dead candidates.

---

## 6. Audio Session Management on iOS

### 6.1 The Audio Architecture Stack

```
Layer 4: CallKit (CXProvider) -- owns audio session lifecycle
Layer 3: AVAudioSession -- iOS system audio management
Layer 2: RTCAudioSession (WebRTC) -- wrapper around AVAudioSession
Layer 1: WebRTC audio engine -- actual audio capture/playback

RULE: CallKit (Layer 4) controls when audio starts/stops.
      WebRTC (Layer 2) must NOT auto-configure audio.
      Your code coordinates the handoff between layers.
```

### 6.2 AVAudioSession Configuration for VoIP

```swift
// Category: .playAndRecord (bidirectional audio)
// Mode: .voiceChat (optimized for voice, echo cancellation, noise reduction)
// Options: .allowBluetooth | .allowBluetoothA2DP

// WebRTC sets this internally when useManualAudio=false.
// When useManualAudio=true, YOU manage it via CallKit.

// CallKit setup should specify matching audio session config:
await RNCallKeep.setup({
  ios: {
    appName: 'QRChat',
    audioSession: {
      categoryOptions: 0x1 | 0x20, // AllowBluetooth | AllowBluetoothA2DP
      mode: 'AVAudioSessionModeVoiceChat',
    },
  },
});
```

### 6.3 The useManualAudio + isAudioEnabled Pattern

This is THE critical pattern for CallKit + WebRTC audio. Used by Signal, Wire, LiveKit, Jitsi.

```
INITIALIZATION (AppDelegate / didFinishLaunchingWithOptions):
  RTCAudioSession.sharedInstance().useManualAudio = true   // Prevent WebRTC auto-config
  RTCAudioSession.sharedInstance().isAudioEnabled = false   // No audio yet

CALLKIT ACTIVATES AUDIO (CXProvider.didActivateAudioSession):
  RTCAudioSession.sharedInstance().audioSessionDidActivate(AVAudioSession.sharedInstance())
  RTCAudioSession.sharedInstance().isAudioEnabled = true    // NOW audio flows

CALLKIT DEACTIVATES AUDIO (CXProvider.didDeactivateAudioSession):
  RTCAudioSession.sharedInstance().isAudioEnabled = false
  RTCAudioSession.sharedInstance().audioSessionDidDeactivate(AVAudioSession.sharedInstance())
```

**Why this matters:**
- Without `useManualAudio`, WebRTC activates the audio session the moment you call `getUserMedia()` or `addTrack()`
- This conflicts with CallKit, which expects to OWN the audio session
- Result: speaker button resets, audio drops, one-way audio
- With `useManualAudio`, WebRTC waits until YOU tell it audio is ready
- CallKit controls the timing -- audio starts when CXProvider says so

### 6.4 Audio Session Activation Timing

```
INCOMING CALL (cold start):
  1. VoIP push -> reportNewIncomingCall() -> CallKit UI appears
  2. User taps Answer -> CXProvider.didActivateAudioSession fires
  3. RTCAudioSession.isAudioEnabled = true
  4. JS creates PeerConnection, getUserMedia, setRemoteDescription, createAnswer
  5. ICE negotiation completes
  6. Audio flows! (because isAudioEnabled was already set in step 3)

OUTGOING CALL:
  1. User taps Call button
  2. JS: RNCallKeep.startCall(uuid, callerName)
  3. CallKit activates audio session (CXProvider fires)
  4. RTCAudioSession.isAudioEnabled = true
  5. JS creates PeerConnection, getUserMedia, createOffer
  6. Remote answers, ICE completes
  7. Audio flows! (isAudioEnabled was set in step 4)

KEY INSIGHT: Audio session activation happens BEFORE WebRTC negotiation.
The audio engine is "armed" and waiting. When ICE connects, audio starts immediately.
```

### 6.5 Audio Routing (Speaker, Earpiece, Bluetooth)

```typescript
// Speaker toggle
import InCallManager from 'react-native-incall-manager';
InCallManager.setSpeakerphoneOn(true);  // Route to speaker
InCallManager.setSpeakerphoneOn(false); // Route to earpiece

// For CallKit integration, also use:
// RNCallKeep.setMutedCall(uuid, isMuted)
// This updates the CallKit UI mute button state

// Bluetooth: Handled automatically by categoryOptions .allowBluetooth
// When a Bluetooth device is connected, iOS routes audio to it
// User can switch via CallKit audio route picker

// Video calls: Default to speaker (isVideo ? true : false)
// Audio calls: Default to earpiece
```

### 6.6 Audio Interruption Handling

```swift
// Register in AppDelegate
NotificationCenter.default.addObserver(
  forName: AVAudioSession.interruptionNotification,
  object: nil, queue: .main
) { notification in
  guard let type = notification.userInfo?[AVAudioSessionInterruptionTypeKey] as? UInt else { return }

  if AVAudioSession.InterruptionType(rawValue: type) == .began {
    // Another app took audio (phone call, Siri, etc.)
    RTCAudioSession.sharedInstance().isAudioEnabled = false
  } else if AVAudioSession.InterruptionType(rawValue: type) == .ended {
    // Interruption ended, reactivate
    RTCAudioSession.sharedInstance().audioSessionDidActivate(AVAudioSession.sharedInstance())
    RTCAudioSession.sharedInstance().isAudioEnabled = true
  }
}
```

---

## 7. Node.js Signaling Server

### 7.1 What the Server Must Store During a Call

```javascript
// Active Calls Map (server-side)
// Key: calleeId (the person being called)
// Value: call state object
const activeCalls = new Map();

activeCalls.set(calleeId, {
  from: callerId,           // Who initiated the call
  offer: sdpOffer,          // The SDP offer (for cold start retrieval)
  timestamp: Date.now(),    // When the call started
  status: 'ringing',        // 'ringing' | 'accepted-pending' | 'connected' | 'ended'
  callerName: displayName,  // For push notification display
  isVideo: false,           // Audio or video call
  turnServers: [...],       // TURN credentials (for cold start)
});

// Cleanup: Remove stale calls after timeout (120s for slow cold starts)
setInterval(() => {
  const now = Date.now();
  activeCalls.forEach((call, calleeId) => {
    if (now - call.timestamp > 120000) {
      activeCalls.delete(calleeId);
    }
  });
}, 60000);
```

### 7.2 Message Delivery When Client is Disconnected

```javascript
// Pending message queue (per user)
// - Offline messages stored on server
// - Delivered when user reconnects and registers
// - TTL: 48 hours
// - Max: 1000 messages / 50MB per user (DoS protection)

// Call-specific queuing rules:
// QUEUE: call offers (isCall: true), call-ended, ice-candidates (if pending offer exists)
// SKIP: data channel offers (isCall: false), answers (if no pending offer)

// When callee reconnects:
ws.on('register', (userId) => {
  // 1. Check for active call (fastest path for cold start)
  const activeCall = activeCalls.get(userId);
  if (activeCall) {
    ws.send({ type: 'call-state', ...activeCall });
  }

  // 2. Deliver pending messages
  const pending = pendingQueue.get(userId) || [];
  // Skip duplicate call offers if already accepted-pending
  const filtered = filterDuplicateCallOffers(pending, activeCall?.status);
  filtered.forEach(msg => ws.send(JSON.stringify(msg)));
});
```

### 7.3 Call State Transitions on Server

```
Server-Side Call State Machine:

NONE -> RINGING
  Trigger: Caller sends 'offer' with isCall=true
  Action: Store in activeCalls, send VoIP push, queue offer

RINGING -> ACCEPTED_PENDING
  Trigger: Callee sends 'call-accepted-pending'
  Action: Update status, forward to caller

ACCEPTED_PENDING -> CONNECTED
  Trigger: Callee sends 'answer'
  Action: Forward answer, remove from activeCalls

RINGING -> ENDED
  Trigger: Caller sends 'call-ended'
  Action: Remove from activeCalls, clean pending queue, forward to callee

ANY -> ENDED (disconnect grace period)
  Trigger: Either peer disconnects
  Action: Wait 10s (cold start reconnection window), then send call-ended
```

### 7.4 TURN Server Credential Generation

```javascript
// Time-limited credentials using HMAC-SHA1 (RFC 5766, coturn compatible)
const crypto = require('crypto');

function generateTurnCredentials(userId, sharedSecret, ttlSeconds = 86400) {
  const timestamp = Math.floor(Date.now() / 1000) + ttlSeconds;
  const username = `${timestamp}:${userId}`;
  const hmac = crypto.createHmac('sha1', sharedSecret);
  hmac.update(username);
  const credential = hmac.digest('base64');

  return {
    username,
    credential,
    urls: [
      'turn:turn.example.com:443?transport=tcp',
      'turn:turn.example.com:3478?transport=udp',
      'turns:turn.example.com:443?transport=tcp', // TLS
    ],
  };
}

// Deliver via authenticated WebSocket only (not HTTP -- prevents credential scraping)
ws.on('get-turn-credentials', () => {
  const turnServers = generateTurnCredentials(userId, TURN_SHARED_SECRET);
  ws.send(JSON.stringify({ type: 'turn-credentials', servers: [turnServers] }));
});

// Cache on server for cold start (include in VoIP push + call-state response)
cachedTurnServers = [generateTurnCredentials('shared', TURN_SHARED_SECRET)];
```

### 7.5 Disconnect Grace Period

```javascript
// CRITICAL for cold start: When callee's WebSocket disconnects during app boot,
// DON'T immediately send call-ended to the caller.

ws.on('close', () => {
  // Check if this user has an active call
  const hasActiveCall = [...activeCalls.values()].some(
    c => c.from === userId || activeCalls.has(userId)
  );

  if (hasActiveCall) {
    // Grace period: 10-15 seconds for cold start reconnection
    setTimeout(() => {
      // Check if user reconnected
      if (!connectedClients.has(userId)) {
        // Still disconnected -- send call-ended to peer
        sendCallEndedToPeer(userId);
        activeCalls.delete(userId);
      }
    }, 10000);
  }
});
```

### 7.6 Call Offer Deduplication

```javascript
// Prevent duplicate call offers from same caller to same callee within 30s
const recentCallOffers = new Map(); // key: "callerId:calleeId", value: timestamp

function isDuplicateCallOffer(from, to) {
  const key = `${from}:${to}`;
  const last = recentCallOffers.get(key);
  if (last && Date.now() - last < 30000) {
    return true; // Duplicate within 30s window
  }
  recentCallOffers.set(key, Date.now());
  return false;
}

// Clear on call-ended (allow immediate re-call)
function clearCallOfferDedup(from, to) {
  recentCallOffers.delete(`${from}:${to}`);
  recentCallOffers.delete(`${to}:${from}`);
}
```

---

## 8. Common Pitfalls & Solutions

### 8.1 NO AUDIO After Answering (The #1 Issue)

**Root Cause:** WebRTC and CallKit fight over AVAudioSession control.

**Solution (definitive):**
```swift
// In AppDelegate (once, at startup):
RTCAudioSession.sharedInstance().useManualAudio = true
RTCAudioSession.sharedInstance().isAudioEnabled = false

// In CXProvider didActivateAudioSession:
RTCAudioSession.sharedInstance().audioSessionDidActivate(AVAudioSession.sharedInstance())
RTCAudioSession.sharedInstance().isAudioEnabled = true

// NEVER use InCallManager.start() for iOS audio session management
// NEVER call AVAudioSession.setActive() directly
// Let CallKit own the audio session lifecycle
```

### 8.2 ONE-WAY AUDIO

**Common causes:**
1. **Missing media tracks on one side:** Ensure both peers call `getUserMedia()` and `addTrack()` before creating offer/answer.
2. **Audio session not activated before answer:** On iOS, `isAudioEnabled` must be `true` before the answer SDP is sent.
3. **NAT traversal failure:** One peer's ICE candidates can't reach the other. Check TURN configuration.
4. **Track disabled after network change:** After ICE restart, verify track.enabled is still true.

**Debugging checklist:**
```
[ ] Both peers have audio tracks? (getAudioTracks().length > 0)
[ ] Audio tracks enabled? (track.enabled === true)
[ ] RTCAudioSession.isAudioEnabled? (must be true)
[ ] connectionState === 'connected'?
[ ] Check getStats() for inbound-rtp audio -- packets received > 0?
[ ] TURN servers configured? (check behind symmetric NAT)
```

### 8.3 COLD START: Call Screen Never Appears

**Root Causes:**
1. NavigationContainer not mounted when navigation is attempted
2. `didLoadWithEvents` events lost because listeners registered too late
3. JavaScript bridge not initialized when CallKit answer fires

**Solution:**
- Register CallKeep listeners in `index.js` (before AppRegistry.registerComponent)
- Use `didLoadWithEvents` to catch buffered events from cold start
- Store state in ColdStartCoordinator singleton (not global variables)
- Defer navigation until NavigationContainer `onReady` fires
- Use 3-path SDP retrieval with sequential fallback

### 8.4 CALL DROPS AFTER 30 SECONDS

**Root Cause:** ICE negotiation timeout. Both peers fail to find a working candidate pair.

**Solutions:**
- Ensure TURN servers are configured (STUN alone fails behind symmetric NAT)
- Use both UDP and TCP TURN (some firewalls block UDP)
- Add `turns:` (TLS) for corporate networks
- Increase `iceCandidatePoolSize` to 1 (pre-allocate)
- Enable `continualGatheringPolicy: 'gatherContinually'`
- Monitor ICE gathering state -- if stuck in 'gathering' for >10s, restart

### 8.5 SPEAKER BUTTON RESETS IN CALLKIT UI

**Root Cause:** WebRTC changes AVAudioSession mode/category, overriding CallKit's settings.

**Solution:** Match CallKit's audio session configuration with WebRTC's:
```javascript
// In RNCallKeep.setup():
audioSession: {
  categoryOptions: 0x1 | 0x20, // AllowBluetooth | AllowBluetoothA2DP
  mode: 'AVAudioSessionModeVoiceChat', // Match WebRTC's mode
}
```

### 8.6 DUPLICATE CALL NOTIFICATIONS

**Root Cause:** VoIP push arrives while WebSocket already delivered the offer.

**Solution:**
- When app is active (foreground), report and immediately end the VoIP push call
- Use call offer deduplication on server (30s window)
- Check ColdStartCoordinator state before reporting to CallKit

### 8.7 VIDEO NOT SHOWING AFTER TOGGLE

**Root Cause:** Adding/removing video track requires renegotiation.

**Solution:**
```typescript
// Toggle video (proper way):
async function toggleVideo(contactId: string, enable: boolean) {
  const pc = peers.get(contactId)?.connection;
  if (!pc) return;

  const senders = pc.getSenders();
  const videoSender = senders.find(s => s.track?.kind === 'video');

  if (enable && !videoSender) {
    // Add video track + renegotiate
    const stream = await mediaDevices.getUserMedia({ video: true });
    const videoTrack = stream.getVideoTracks()[0];
    pc.addTrack(videoTrack, stream);
    // Trigger renegotiation (onnegotiationneeded fires)
  } else if (!enable && videoSender) {
    // Remove video track
    pc.removeTrack(videoSender);
    videoSender.track?.stop();
  }
}
```

### 8.8 RACE CONDITIONS IN OFFER/ANSWER EXCHANGE

**Symptoms:** `InvalidStateError: setRemoteDescription called in wrong state`

**Common scenarios:**
1. Two offers arrive simultaneously (glare) -> Use Perfect Negotiation pattern
2. `setLocalDescription` called while previous negotiation in progress -> Guard with `makingOffer` flag
3. ICE restart offer arrives during answer creation -> Check `signalingState` before proceeding

**Defensive coding pattern:**
```typescript
// Before setRemoteDescription(offer):
if (pc.signalingState === 'have-local-offer') {
  if (isPolite) {
    await pc.setLocalDescription({ type: 'rollback' });
  } else {
    return; // Ignore incoming offer
  }
}

// Before createOffer:
if (pc.signalingState !== 'stable' && pc.signalingState !== 'have-local-offer') {
  console.log('Aborting offer -- wrong state:', pc.signalingState);
  return;
}
```

---

## 9. QRChat Gap Analysis

### 9.1 What QRChat Already Does Right

| Practice | Status | Notes |
|----------|--------|-------|
| `useManualAudio = true` in AppDelegate | DONE | Matches Signal pattern |
| `isAudioEnabled` managed by CallKit callbacks | DONE | AppDelegate observer pattern |
| didLoadWithEvents in index.js | DONE | Cold start events captured |
| ColdStartCoordinator singleton | DONE | 3-path SDP retrieval |
| SDP in VoIP push payload | DONE | With minification |
| TURN credentials in VoIP push | DONE | For cold start PATH A |
| Server-side call state (get-call-state) | DONE | For cold start PATH B |
| Call offer dedup on server | DONE | 30s window |
| Active call cleanup (120s timeout) | DONE | Extended for cold starts |
| ICE restart on disconnect/failed | DONE | Max 2 restarts |
| Continual gathering policy | DONE | `gatherContinually` set |
| Disconnect grace period | DONE | 10s on server |
| CallKit audio session mode matching | DONE | AVAudioSessionModeVoiceChat |
| Nullify handlers before pc.close() | DONE | Prevents ghost callbacks |
| Media track cleanup | DONE | Stop tracks on call end |
| Pending call peer tracking | DONE | ICE candidates queued correctly |
| call-accepted-pending signal | DONE | Cold start: callee ack before WebRTC ready |
| Outgoing call timeout (60s) | DONE | Managed by CallScreen |
| Call quality monitoring (RTT, loss, jitter) | DONE | Every 3 seconds |
| ICE candidate queuing | DONE | drainIceCandidateQueue() |
| Speaker default for video calls | DONE | isVideo ? true : false |

### 9.2 Potential Improvements

| Area | Current | Recommended | Priority |
|------|---------|-------------|----------|
| Perfect Negotiation pattern | Partial (makingOffer flag, state checks) | Full polite/impolite peer with rollback | MEDIUM |
| ICE candidate removal signaling | Not implemented | Signal removals for `continualGathering` | LOW |
| Opus codec preferences | Not explicitly set | Set `useinbandfec=1;dtx=1` via setCodecPreferences | LOW |
| Call state machine (explicit) | Implicit via callStatus string | Formal state machine with transitions | MEDIUM |
| Audio interruption handling | Handled in AppDelegate | Add JS-side notification for UI feedback | LOW |
| TURN credential TTL | Server generates per-request | Cache with refresh timer (e.g., 12h TTL) | LOW |
| Ringback tone management | System sound module | Standardize: start on 'ringing', stop on any state change | LOW |
| Multiple ICE restart strategies | Fixed 2 retries, then give up | Exponential backoff between restarts | LOW |
| Network change detection | Relies on continualGathering + ICE state | Add NetInfo listener for proactive restart | MEDIUM |
| Call log: capture cold start path | ColdStartCoordinator.getDiagnosticSummary() | Persist to call log database for analytics | LOW |

### 9.3 Architecture Quality Assessment

**Overall: PRODUCTION-GRADE (8.5/10)**

QRChat's call system already implements the vast majority of best practices from Signal, LiveKit, ConnectyCube, and other production VoIP apps. The cold start handling via ColdStartCoordinator with 3-path SDP retrieval is particularly well-engineered. The main areas for improvement are around edge cases (perfect negotiation with full rollback, proactive network change detection) rather than fundamental architecture issues.

---

## Sources

- [react-native-callkeep (GitHub)](https://github.com/react-native-webrtc/react-native-callkeep)
- [react-native-voip-push-notification (GitHub)](https://github.com/react-native-webrtc/react-native-voip-push-notification)
- [Troubleshooting VoIP Push Notifications on iOS (ConnectyCube)](https://connectycube.com/2025/11/06/troubleshooting-common-issues-with-voip-push-notifications-on-ios/)
- [How to Implement VoIP in iOS: CallKit, PushKit Guide](https://www.linkedin.com/pulse/how-implement-voip-ios-guide-callkit-pushkit-wagner-assis-ikhtf)
- [Mastering CallKit: Complete Guide to iOS VoIP Integration (VideoSDK)](https://www.videosdk.live/developer-hub/sip/mastering-callkit-guide-voip-integration-ios)
- [Using PushKit Notification for Incoming Calls (GetStream)](https://getstream.io/blog/pushkit-for-calls/)
- [iOS 13 PushKit VoIP restrictions (Apple Developer Forums)](https://developer.apple.com/forums/thread/117939)
- [Signal RingRTC (GitHub)](https://github.com/signalapp/ringrtc)
- [Signal signal-webrtc-ios (GitHub)](https://github.com/signalapp/signal-webrtc-ios)
- [Signal: How to Build E2EE Group Video Calls](https://signal.org/blog/how-to-build-encrypted-group-calls/)
- [WebRTC Perfect Negotiation Pattern (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API/Perfect_negotiation)
- [Perfect Negotiation in WebRTC (Mozilla Blog)](https://blog.mozilla.org/webrtc/perfect-negotiation-in-webrtc/)
- [Perfect Negotiation (WebRTC Samples)](https://webrtc.github.io/samples/src/content/peerconnection/perfect-negotiation/)
- [WebRTC Negotiation Patterns (Subspace)](https://subspace.com/resources/optimize-webrtc-negotiation-patterns)
- [Mastering VoIP Audio with CallKit and WebRTC on iOS (Medium)](https://medium.com/@tsivilko/mastering-voip-audio-with-callkit-and-webrtc-on-ios-0f2092402331)
- [Fix audio activate/deactivate with CallKit (react-native-webrtc #632)](https://github.com/react-native-webrtc/react-native-webrtc/issues/632)
- [RTCAudioSession Support Proposal (react-native-webrtc #1270)](https://github.com/react-native-webrtc/react-native-webrtc/issues/1270)
- [LiveKit React Native SDK (npm)](https://www.npmjs.com/package/@livekit/react-native)
- [Trickle ICE RFC 8838](https://www.rfc-editor.org/rfc/rfc8838)
- [ICE Candidates Tutorial (GetStream)](https://getstream.io/resources/projects/webrtc/basics/ice-candidates/)
- [WebRTC Handover WiFi/Cellular (WirelessMoves)](https://blog.wirelessmoves.com/2025/08/webrtc-handover-between-wi-fi-and-cellular.html)
- [ICE Restart (Mozilla Blog)](https://blog.mozilla.org/webrtc/just-begin-ice-restart/)
- [ICE Restarts (WebRTC Course)](https://webrtccourse.com/course/webrtc-codelab/module/fiddle-of-the-month/lesson/ice-restarts/)
- [SDP Munging and Structure (GetStream)](https://getstream.io/resources/projects/webrtc/advanced/sdp-munging/)
- [WebRTC Codecs (GetStream)](https://getstream.io/resources/projects/webrtc/advanced/codecs/)
- [WebRTC Signaling with WebSocket and Node.js (LogRocket)](https://blog.logrocket.com/webrtc-signaling-websocket-node-js/)
- [WebRTC Signaling Server (GetStream)](https://getstream.io/resources/projects/webrtc/basics/signaling-server/)
- [TURN Server Credential Generation (coturn Wiki)](https://github.com/coturn/coturn/wiki/turnserver/28dc2d9e2b313b8923b6fd50f2a84e03933ea9d9)
- [TURN Authentication (Medium / L7mp)](https://medium.com/l7mp-technologies/lets-talk-about-turn-authentication-c2767514bc0c)
- [Self-Hosted STUN/TURN Servers (WebRTC.ventures)](https://webrtc.ventures/2025/01/how-to-set-up-self-hosted-stun-turn-servers-for-webrtc-applications/)
- [Best Practices for Closing PeerConnections (Medium)](https://medium.com/@BeingOttoman/best-practices-for-closing-webrtc-peerconnections-b60616b1352)
- [RTCPeerConnection.close() (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection/close)
- [react-native-webrtc Resource Leak Issue #1783](https://github.com/react-native-webrtc/react-native-webrtc/issues/1783)
- [WebRTC Connectivity (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API/Connectivity)
- [RTCPeerConnection Tutorial (GetStream)](https://getstream.io/resources/projects/webrtc/basics/rtcpeerconnection/)
- [AVAudioSession playAndRecord (Apple Documentation)](https://developer.apple.com/documentation/avfaudio/avaudiosession/category-swift.struct/playandrecord)
- [ConnectyCube React Native Video Calling](https://developers.connectycube.com/reactnative/videocalling/)
