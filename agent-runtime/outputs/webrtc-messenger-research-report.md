# Open-Source Messenger WebRTC Research Report

**Date:** 2026-03-27
**Purpose:** Comprehensive analysis of open-source messenger applications using WebRTC for audio/video calls, with focus on patterns applicable to QRChat's cold-start call audio issues.

---

## Table of Contents

1. [Project Inventory](#1-project-inventory)
2. [Comparison Tables](#2-comparison-tables)
3. [Detailed Project Analysis](#3-detailed-project-analysis)
4. [Critical Pattern Analysis](#4-critical-pattern-analysis)
5. [Key Learnings for QRChat](#5-key-learnings-for-qrchat)
6. [Recommended Implementation Plan](#6-recommended-implementation-plan)
7. [Sources](#7-sources)

---

## 1. Project Inventory

### Tier 1: Gold Standard (Native, Production-Grade)

| Project | GitHub | Stars | Language | License | Last Active |
|---------|--------|-------|----------|---------|-------------|
| Signal iOS | signalapp/Signal-iOS | 11,951 | Swift | AGPL-3.0 | 2026-03-26 |
| Signal Android | signalapp/Signal-Android | 28,548 | Kotlin | AGPL-3.0 | 2026-03-26 |
| Signal RingRTC | signalapp/ringrtc | 625 | Rust/Swift/Java | AGPL-3.0 | 2026-03-22 |
| Wire iOS | wireapp/wire-ios | 115 | Swift | GPL-3.0 | 2026-03-26 |
| Wire Android | wireapp/wire-android | 236 | Kotlin | GPL-3.0 | 2026-03-26 |
| Wire AVS | wireapp/wire-avs | 142 | C | GPL-3.0 | 2026-03-10 |

### Tier 2: React Native Implementations (Directly Applicable)

| Project | GitHub | Stars | Language | License | Last Active |
|---------|--------|-------|----------|---------|-------------|
| Jitsi Meet | jitsi/jitsi-meet | 28,883 | TypeScript | Apache-2.0 | 2026-03-26 |
| Rocket.Chat RN | RocketChat/Rocket.Chat.ReactNative | 2,373 | TypeScript | MIT | 2026-03-26 |
| Mattermost Mobile | mattermost/mattermost-mobile | 2,627 | TypeScript | Apache-2.0 | 2026-03-26 |
| LiveKit RN SDK | livekit/client-sdk-react-native | 252 | TypeScript | Apache-2.0 | 2026-03-26 |

### Tier 3: Core Libraries (Used by QRChat)

| Project | GitHub | Stars | Language | License | Last Active |
|---------|--------|-------|----------|---------|-------------|
| react-native-webrtc | react-native-webrtc/react-native-webrtc | 4,950 | Java/ObjC | MIT | 2026-03-26 |
| react-native-callkeep | react-native-webrtc/react-native-callkeep | 1,033 | Java/ObjC | ISC | 2026-03-25 |
| react-native-voip-push | react-native-webrtc/react-native-voip-push-notification | 235 | ObjC | ISC | 2026-02-20 |

### Tier 4: P2P / Matrix-Based

| Project | GitHub | Stars | Language | License | Last Active |
|---------|--------|-------|----------|---------|-------------|
| Element Call | element-hq/element-call | 924 | TypeScript | AGPL-3.0 | 2026-03-26 |
| Element X iOS | element-hq/element-x-ios | 777 | Swift | AGPL-3.0 | 2026-03-26 |
| LiveKit Server | livekit/livekit | 17,815 | Go | Apache-2.0 | 2026-03-26 |
| Jami Android | savoirfairelinux/jami-client-android | 189 | Kotlin | GPL-3.0 | 2026-03-25 |
| Jami iOS | savoirfairelinux/jami-client-ios | 23 | Swift | GPL-3.0 | 2026-03-23 |

---

## 2. Comparison Tables

### Call Architecture Comparison

| Project | WebRTC Library | Calling Model | CallKit | VoIP Push | Cold Start Support |
|---------|---------------|---------------|---------|-----------|-------------------|
| Signal | RingRTC (custom Rust) | P2P + SFU (group) | Native CXProvider | Yes | Full (native) |
| Wire | wire-avs (custom C) | P2P + SFU | Native CXProvider | Yes | Full (native) |
| Jitsi Meet | jitsi/react-native-webrtc (fork) | SFU (Jitsi Videobridge) | JMCallKitProxy | Partial | Via SDK bridge |
| Rocket.Chat RN | Jitsi SDK integration | SFU (delegates to Jitsi) | Via Jitsi | No (FCM) | Limited |
| Mattermost RN | react-native-webrtc | SFU (plugin server) | react-native-callkeep | No (FCM) | Limited |
| Element X iOS | WKWebView (Element Call) | SFU (LiveKit) | Native CXProvider | Yes | Workaround pattern |
| Jami | Custom (libwebrtc fork) | Pure P2P (DHT) | Native CXProvider | No (DHT direct) | Via daemon |
| LiveKit RN | @livekit/react-native-webrtc (fork) | SFU | Via integration | Via integration | Via integration |

### Audio Session Management Comparison

| Project | Audio Config Method | Manual Audio | Audio Activation Trigger | Speaker Routing |
|---------|-------------------|-------------|-------------------------|-----------------|
| Signal | RTCAudioSession + AVAudioSession | Yes (useManualAudio) | CXProvider didActivateAudioSession | Custom via CallAudioService |
| Wire | MediaManager (custom) | Yes | CXProvider didActivateAudioSession | MediaManager.startAudio() |
| Jitsi | JitsiAudioSession (wraps RTCAudioSession) | Delegates to RTCAudioSession | CXProvider via JMCallKitEmitter | Via RTCAudioSession |
| Mattermost | react-native-incall-manager | No | App-level | InCallManager |
| Element X | Delegates to CallKit | Minimal | CXProvider (logged only) | Via CallKit system |
| react-native-callkeep | configureAudioSession (PlayAndRecord) | No | Posts AVAudioSessionInterruptionNotification | Via CallKit |

### ICE/Reconnection Strategy Comparison

| Project | ICE Gathering | ICE Restart | Reconnection Strategy | Timeout Handling |
|---------|--------------|-------------|----------------------|-----------------|
| Signal | Continual (GATHER_CONTINUALLY) | Via RingRTC (automatic) | State machine: reconnecting -> reconnected | Background task expiration |
| Wire | Standard | Via AVS layer | CallKit observer callbacks | Timer-based |
| Jitsi | Trickle ICE | SFU-managed | Conference-level rejoin | SFU handles |
| Mattermost | Trickle ICE | WebSocket reconnect trigger | ws.send('reconnect') with original connID | 30s ICE stats collection |
| Element X | Via LiveKit/Element Call | SFU-managed | Room subscription monitoring | 90s ring timeout |

---

## 3. Detailed Project Analysis

### 3.1 Signal (Gold Standard)

**Repository Structure:**
- `signalapp/Signal-iOS` - iOS client (Swift)
- `signalapp/Signal-Android` - Android client (Kotlin)
- `signalapp/ringrtc` - WebRTC middleware (Rust 68.6%, Swift 10.9%, Java 5.3%)

**Key Files for Call Handling:**

iOS:
- `Signal/Calls/CallService.swift` - Main call orchestration
- `Signal/Calls/IndividualCallService.swift` - 1:1 call flow (offer/answer/ICE/reconnect)
- `Signal/Calls/CallAudioService.swift` - AVAudioSession management
- `Signal/Calls/CallKitCallManager.swift` - Call tracking
- `Signal/Calls/UserInterface/CallKitCallUIAdaptee.swift` - CXProviderDelegate implementation
- `Signal/Calls/IndividualCall.swift` - Call state model

RingRTC iOS:
- `src/ios/SignalRingRTC/SignalRingRTC/CallManager.swift` - Core call manager
- `src/ios/SignalRingRTC/SignalRingRTC/Connection.swift` - Peer connection wrapper
- `src/ios/SignalRingRTC/SignalRingRTC/GroupCall.swift` - Group call handling

RingRTC Android:
- `src/android/api/org/signal/ringrtc/CallManager.java` - Core call manager
- `src/android/api/org/signal/ringrtc/AudioConfig.java` - Audio configuration

**How Signal Handles Cold Start Incoming Calls:**

1. VoIP push received by iOS system
2. `reportNewIncomingCall(with:update:completion:)` called on CXProvider (synchronous, not async)
3. CallKit displays incoming call UI
4. If user answers while in `localRinging_Anticipatory` state, answer action is **deferred** (not immediately fulfilled)
5. `deferredAnswerCompletion` callback stored until RingRTC signals readiness
6. When ready, transitions to `localRinging_ReadyToAnswer`, then fulfills the deferred action
7. `didActivateAudioSession` fires -> `audioSessionRef.startAudioActivity()` -> `isRTCAudioEnabled = true` (ONLY for incoming individual calls)
8. RingRTC's `receivedOffer()` processes the SDP with identity keys and message age
9. `callManager.accept()` triggers WebRTC answer creation
10. ICE candidates exchange via `receivedIceCandidates()` / `shouldSendIceCandidates()`
11. Connection established -> `handleConnected()` -> audio unmuted

**Critical Signal Pattern - Audio Activation Guard:**
Signal ONLY enables RTC audio in `didActivateAudioSession` for incoming individual calls. For outgoing calls, audio is enabled when the recipient accepts. This prevents audio conflicts.

**Critical Signal Pattern - Deferred Answer:**
When a call arrives but RingRTC isn't ready yet (anticipatory state), Signal does NOT fulfill the CXAnswerCallAction immediately. It stores the completion handler and fulfills it later when the call system is ready. This prevents the race condition between CallKit and WebRTC setup.

**Critical Signal Pattern - Mute Suppression:**
After remote answer on outgoing calls, Signal sets `ignoreFirstUnmuteAfterRemoteAnswer = true` to suppress CallKit's automatic unmute, preventing an audio pop.

**ICE/Reconnection:**
- Uses `GATHER_CONTINUALLY` policy for continuous ICE candidate discovery
- State machine handles `.reconnecting` and `.reconnected` events
- Failed ICE produces `iceFailedWhileConnecting` or `iceFailedAfterConnected` end reasons
- Background task timeout for calls that don't connect

**Audio Session Configuration:**
```
Ringing:        category: .playback, mode: .default
Voice Call:     category: .playAndRecord, mode: .voiceChat (proximity ON)
Video Call:     category: .playAndRecord, mode: .videoChat (proximity OFF)
Idle:           category: .ambient, mode: .default
```

---

### 3.2 Wire

**Repository Structure:**
- `wireapp/wire-ios` - iOS client (Swift)
- `wireapp/wire-android` - Android client (Kotlin)
- `wireapp/wire-avs` - Audio/Video Signaling library (C)

**Key Files for Call Handling:**

iOS:
- `wire-ios-sync-engine/Source/Calling/CallKitManager.swift` - CXProviderDelegate
- `wire-ios-sync-engine/Source/Calling/CallKitCall.swift` - Call model
- `wire-ios-sync-engine/Source/Calling/CallKitCallRegister.swift` - Call tracking
- `wire-ios-sync-engine/Source/Notifications/VoIPPushManager.swift` - VoIP push handling
- `wire-ios-sync-engine/Source/SessionManager/SessionManager+CallKitManagerDelegate.swift`
- `wire-ios-sync-engine/Source/SessionManager/SessionManager+VoIPPushManagerDelegate.swift`

**Critical Wire Pattern - Synchronous Call Reporting:**
Wire explicitly avoids the async version of `reportNewIncomingCall`:
> "Don't use the async version, it's broken. It doesn't get executed when waking up the app from the background and ends up crashing."

**Wire's CallKit Audio Pattern:**
```swift
// didActivateAudioSession:
mediaManager?.startAudio()

// didDeactivateAudioSession:
mediaManager?.resetAudioDevice()

// CXAnswerCallAction / CXStartCallAction:
mediaManager?.setupAudioDevice()  // prepare, but don't start yet
```

Audio is prepared during answer/start, but only actually started when `didActivateAudioSession` fires.

**Wire's Preemptive Reporting:**
Wire has a `reportIncomingCallPreemptively()` method that reports calls from push notifications before the UI loads, preventing iOS from killing the app for not reporting VoIP pushes to CallKit.

**Wire's Answer Flow:**
1. Registers observers for `onEstablished`, `onFailedToJoin`, `onTerminated`
2. Syncs mute state
3. Joins call via `conversation.voiceChannel?.join(video: false)`
4. Processes pending call events before joining

---

### 3.3 Jitsi Meet (React Native)

**Repository:** `jitsi/jitsi-meet` (28,883 stars)

**Key Files for Call Handling:**

Native iOS:
- `ios/sdk/src/callkit/JMCallKitProxy.m` - CallKit proxy (provider config, call reporting)
- `ios/sdk/src/callkit/JMCallKitEmitter.m` - CXProviderDelegate (broadcasts to listeners)
- `ios/sdk/src/JitsiAudioSession.m` - Audio session wrapper (delegates to RTCAudioSession)

React Native:
- `react/features/mobile/call-integration/CallKit.ts` - JS CallKit middleware
- `react/features/conference/conference.js` - Conference management
- `react/features/base/media/` - Media management

**Jitsi's CallKit Integration:**
```objc
// Provider Configuration:
configuration.maximumCallGroups = 1;
configuration.maximumCallsPerCallGroup = 1;
configuration.supportsVideo = YES;

// Audio: delegates entirely to RTCAudioSession
+ (RTCAudioSession *)rtcAudioSession {
    return [RTCAudioSession sharedInstance];
}
```

**Jitsi's Audio Architecture:**
Jitsi takes the simplest approach: it wraps RTCAudioSession and lets WebRTC handle everything. The `JitsiAudioSession` is a thin abstraction over `RTCAudioSession.sharedInstance`. Audio activation/deactivation events are broadcast to listeners via `JMCallKitEmitter`.

**Jitsi's Mute Ping-Pong Prevention:**
The emitter maintains a `pendingMuteActions` set. When JS initiates a mute, the UUID is added to pending. When the CallKit delegate receives a mute action, it checks: if the UUID is in pending (JS-initiated), it skips notifying listeners to prevent circular updates.

**Jitsi's Event System (JS side):**
- `performAnswerCallAction` - User pressed answer in CallKit
- `performEndCallAction` - Call ended (user or system initiated)
- `performSetMutedCallAction` - Mute toggled with `muted` attribute

---

### 3.4 Mattermost (React Native)

**Repository:** `mattermost/mattermost-mobile` (2,627 stars)

**Key Files for Call Handling:**
- `app/products/calls/calls_manager.ts` - App state lifecycle
- `app/products/calls/connection/connection.ts` - WebRTC peer connection
- `app/products/calls/connection/websocket_client.ts` - Signaling
- `app/products/calls/connection/websocket_event_handlers.ts` - Event handling
- `app/products/calls/components/audio_device_button.ios.tsx` - iOS audio routing
- `app/constants/calls.ts` - Constants
- `patches/react-native-webrtc+124.0.5.patch` - Custom WebRTC patches

**Mattermost's WebRTC Connection Pattern:**
```typescript
// 1. Create peer with ICE servers
peer = new RTCPeer({
    iceServers: iceConfigs || [],
    dcSignaling: config.EnableDCSignaling,
});

// 2. Audio track creation (on-demand, starts disabled)
stream = await mediaDevices.getUserMedia({ video: false, audio: true });
voiceTrack = stream.getAudioTracks()[0];
voiceTrack.enabled = false;

// 3. ICE candidates via WebSocket
peer.on('candidate', (candidate) => {
    ws.send('ice', { data: JSON.stringify(candidate) });
});

// 4. SDP compressed with zlib before sending
const sdpHandler = (sdp) => {
    ws.send('sdp', { data: zlibSync(strToU8(JSON.stringify(sdp))) }, true);
};
```

**Mattermost's Reconnection Pattern:**
```typescript
ws.send('reconnect', {
    channelID,
    originalConnID,  // original connection ID preserved
    prevConnID,       // previous connection ID for session continuity
});
```

**Mattermost's ICE Stats Collection:**
`collectICEStats()` monitors candidate pair state changes for 30 seconds, logging transitions and reporting metrics back to the server for diagnostics.

---

### 3.5 Rocket.Chat (React Native)

**Repository:** `RocketChat/Rocket.Chat.ReactNative` (2,373 stars)

**Call Architecture:**
Rocket.Chat does NOT implement its own WebRTC calling. Instead, it integrates Jitsi Meet via the `@jitsi/react-native-sdk`. Calls are initiated via `/jitsi` command or the video call icon, which generates a Jitsi room URL and launches the Jitsi SDK.

**Key Integration:**
- `generateUrl()` method constructs the Jitsi conference URL
- Configuration through Rocket.Chat admin settings for Jitsi domain and protocol
- Mobile users may be redirected to browser for authentication

**Relevance to QRChat:** Limited. Rocket.Chat delegates all WebRTC complexity to Jitsi.

---

### 3.6 Element X iOS / Element Call

**Repository:** `element-hq/element-x-ios` (777 stars)

**Key Files:**
- `ElementX/Sources/Services/ElementCall/ElementCallService.swift` - Main call service
- `ElementX/Sources/Services/ElementCall/CXProviderProtocol.swift` - CallKit abstraction
- `ElementX/Sources/Services/Audio/AudioSessionProtocol.swift` - Audio abstraction

**Element's Unique WebRTC Challenge:**
Element X runs WebRTC inside a `WKWebView` (Element Call), not natively. This creates a conflict with CallKit:
> "Reporting an ongoing call through reportNewIncomingCall + CXAnswerCallAction will give exclusive access for media to the ongoing process, which is different than the WKWebKit is running on, making EC unable to acquire media streams."

**Element's Workaround:**
When user answers via CallKit, Element immediately:
1. Fulfills the answer action
2. Waits 1 second
3. Reports the call as ended with `.remoteEnded`
4. Publishes `startCall(roomID:)` action to navigate to the call screen

This releases CallKit's audio session lock so WebRTC in the WebView can acquire media.

**Element's Cold Start Race Condition Fix:**
```swift
// Dual observation triggers:
// 1. When clientProxy is assigned -> observeIncomingCall()
// 2. When incomingCallID is set -> observeIncomingCall()
// This ensures observation proceeds regardless of which arrives first
```

The service stores the incoming call ID from VoIP push and watches for the client proxy to become available. Only when both are present does it begin monitoring the call state.

**Element's Ring Timeout:**
Ring duration is computed as: `min(90 seconds, time until expiration from push payload)`

---

### 3.7 Jami (GNU)

**Repository:** `savoirfairelinux/jami-client-android` (189 stars), `savoirfairelinux/jami-client-ios` (23 stars)

**Architecture:**
- Pure P2P using DHT (Distributed Hash Table) for peer discovery
- No central server for call relay
- TLS 1.3 with perfect forward secrecy for all calls
- ICE protocol for NAT traversal
- Native clients (not React Native)

**Relevance to QRChat:** Jami's P2P calling via DHT is conceptually similar to QRChat's P2P design. However, Jami uses a native daemon that runs persistently, handling wake-up and call setup at the system level rather than through VoIP push + React Native bridge initialization.

---

### 3.8 LiveKit (SFU Infrastructure)

**Repository:** `livekit/livekit` (17,815 stars)

**Architecture:**
- SFU media server written in Go (Pion WebRTC)
- `@livekit/react-native-webrtc` - forked react-native-webrtc with enhancements
- `@livekit/client-sdk-react-native` - React Native client SDK

**Relevance to QRChat:** LiveKit is SFU-based, not P2P, but its React Native WebRTC fork (`@livekit/react-native-webrtc`) may contain iOS audio session improvements over the standard `react-native-webrtc`. Worth investigating for patches.

---

## 4. Critical Pattern Analysis

### 4.1 Pattern: VoIP Push -> App Wakes -> WebRTC Established -> Audio Flows

**The Problem:** When a React Native app is killed and receives a VoIP push, there is a race between:
1. Native CallKit needing to display the call UI immediately
2. React Native bridge needing time to initialize
3. WebRTC peer connection needing to be created and connected
4. Audio session needing to be properly configured

**How Signal Solves It (Native):**
1. VoIP push arrives -> `reportNewIncomingCall()` called immediately (synchronous)
2. CallKit shows UI
3. User answers -> if RingRTC not ready, **defer the answer action** (store completion handler)
4. Meanwhile, `receivedOffer()` processes SDP with message age calculation
5. When RingRTC ready -> fulfill deferred answer
6. `didActivateAudioSession` -> enable RTC audio
7. ICE candidates exchange
8. Connection established

**How react-native-callkeep Solves It (React Native):**
1. VoIP push arrives -> Native code calls `reportNewIncomingCall()` on `sharedProvider`
2. CallKit shows UI
3. If JS bridge not ready, events queue in `_delayedEvents` array
4. When JS bridge initializes and listeners attach, `startObserving` fires
5. All queued events delivered via `RNCallKeepDidLoadWithEvents`
6. JS processes the events (answer, end, etc.)

**Key Insight:** The native layer MUST handle the VoIP push and CallKit reporting. The JS layer receives events only after the bridge is ready. The `didLoadWithEvents` mechanism is critical for cold start.

### 4.2 Pattern: AVAudioSession Configuration vs WebRTC Track Creation on iOS

**The Correct Order (from Signal and the "Mastering VoIP Audio" article):**

```
STEP 1 (App Launch):
  RTCAudioSession.sharedInstance().useManualAudio = true
  // This prevents WebRTC from auto-configuring audio

STEP 2 (Call Setup):
  // Create RTCPeerConnection, add tracks
  // But do NOT touch AVAudioSession yet

STEP 3 (CXAnswerCallAction / CXStartCallAction):
  // Do NOT configure audio here
  // Just fulfill the action (or defer for Signal's pattern)

STEP 4 (CXProvider didActivateAudioSession):
  // NOW configure audio
  rtcAudioSession.lockForConfiguration()
  try rtcAudioSession.setConfiguration(RTCAudioSessionConfiguration.webRTC())
  try rtcAudioSession.setActive(true)
  rtcAudioSession.isAudioEnabled = true  // CRITICAL - without this, no audio
  rtcAudioSession.unlockForConfiguration()

STEP 5 (Call Connected):
  // Audio should now be flowing
  // Enable the audio track: audioTrack.isEnabled = true

STEP 6 (CXProvider didDeactivateAudioSession):
  rtcAudioSession.isAudioEnabled = false
  rtcAudioSession.lockForConfiguration()
  try rtcAudioSession.setActive(false)
  rtcAudioSession.unlockForConfiguration()
```

**CRITICAL RULES:**
1. NEVER call `AVAudioSession.sharedInstance().setActive()` directly during a call - use `RTCAudioSession` instead
2. ALWAYS set `useManualAudio = true` at app launch
3. ALWAYS set `isAudioEnabled = true` in `didActivateAudioSession` - `setActive(true)` alone is not enough
4. ALWAYS lock configuration with `lockForConfiguration()` before changes
5. Use `RTCAudioSessionConfiguration.webRTC()` for the configuration, not custom categories

### 4.3 Pattern: ICE Connection Failures and Automatic Reconnection

**Signal's Approach:**
```
State Machine:
  connected -> (ICE failure detected) -> reconnecting -> (ICE restored) -> reconnected
                                                      -> (timeout) -> ended (iceFailedAfterConnected)

Configuration:
  RTCConfiguration.continualGatheringPolicy = .gatherContinually
  // This enables ongoing ICE candidate discovery even after initial connection
```

**Mattermost's Approach:**
```
WebSocket-based reconnection:
  1. Detect disconnect
  2. ws.send('reconnect', { channelID, originalConnID, prevConnID })
  3. Server restores session context
  4. New ICE negotiation with preserved session
  5. collectICEStats() for 30 seconds to monitor recovery
```

**Best Practice ICE Restart Pattern:**
```javascript
// Monitor connection state
peerConnection.oniceconnectionstatechange = () => {
  if (peerConnection.iceConnectionState === 'failed') {
    // Trigger ICE restart
    peerConnection.restartIce();
    // This causes negotiationneeded event
    // Which triggers new offer with iceRestart flag
  }
  if (peerConnection.iceConnectionState === 'disconnected') {
    // Start a timer (e.g., 5 seconds)
    // If not recovered to 'connected', then restartIce()
    // Don't restart immediately - 'disconnected' is volatile
  }
};
```

**Key Rules:**
1. Use `GATHER_CONTINUALLY` (not `GATHER_ONCE`) for ongoing candidate discovery
2. Don't restart ICE on `disconnected` state immediately - it's volatile (single dropped packet)
3. Use a timer (3-5 seconds) before deciding to restart
4. Use the Perfect Negotiation pattern for handling simultaneous ICE restarts from both sides
5. Track `originalConnID` for session continuity across reconnections

### 4.4 Pattern: CallKit Delegate Methods Critical for WebRTC Audio

**Method: `provider(_:didActivate:AVAudioSession)`**
- THE most important method for WebRTC audio
- This is WHERE you enable RTCAudioSession: `isAudioEnabled = true`
- Signal: starts audio activity + enables RTC audio (incoming only)
- Wire: `mediaManager?.startAudio()`
- Jitsi: broadcasts to all registered listeners
- react-native-callkeep: posts `AVAudioSessionInterruptionNotification` + configures PlayAndRecord

**Method: `provider(_:didDeactivate:AVAudioSession)`**
- Disable RTCAudioSession: `isAudioEnabled = false`
- Signal: disables RTC audio + ends audio activity
- Wire: `mediaManager?.resetAudioDevice()`

**Method: `provider(_:perform:CXAnswerCallAction)`**
- DO: Fulfill the action (or defer if not ready like Signal)
- DO: Start WebRTC setup if not already started
- DO NOT: Configure audio here - wait for didActivateAudioSession
- Signal: May defer fulfillment if in anticipatory state
- Wire: Registers observers, syncs mute, joins call
- Element: Fulfills immediately, then ends call after 1s (WebView workaround)

**Method: `provider(_:perform:CXStartCallAction)`**
- For outgoing calls
- Wire: `setupAudioDevice()` (prepare but don't start)
- Signal: Reports connecting, updates call info

**Method: `provider(_:perform:CXSetMutedCallAction)`**
- Handle mute state
- Signal: Ignores first unmute after remote answer
- Jitsi: Checks pendingMuteActions to prevent ping-pong

### 4.5 Pattern: Signaling Channel Setup vs WebRTC Offer/Answer Race Condition

**The Problem:** On cold start:
1. VoIP push arrives with call offer data
2. App needs to establish signaling connection (WebSocket)
3. But the offer is already available from the push payload
4. ICE candidates may be queued on the server
5. If WebSocket connects AFTER offer processing, candidates may arrive before the remote description is set

**Signal's Solution:**
- Offer data is embedded in the push notification payload (opaque bytes)
- `receivedOffer()` processes it directly without needing signaling channel first
- ICE candidates are delivered via the messaging protocol (encrypted messages)
- Message age is calculated from server timestamps for timeout handling
- No WebSocket needed for the initial offer - it comes via the push message queue

**Mattermost's Solution:**
- WebSocket connection established first
- Join message sent with channelID
- Server responds with ICE configs
- SDP exchange happens over WebSocket with zlib compression
- Reconnection preserves session with originalConnID

**Perfect Negotiation Pattern (MDN/Mozilla recommended):**
- Assign roles: "polite" peer and "impolite" peer
- Polite peer uses ICE rollback on collision (drops its offer, accepts remote)
- Impolite peer ignores incoming offers during collision (its offer wins)
- This handles the glare condition where both sides create offers simultaneously

**Recommendation for QRChat:**
1. Embed call offer in the VoIP push payload
2. Process offer immediately in native code, before WebSocket connects
3. Use the messaging queue (already encrypted) for initial signaling
4. WebSocket reconnection provides ongoing ICE candidate relay
5. Implement Perfect Negotiation for glare handling

---

## 5. Key Learnings for QRChat

### LEARNING 1: Native Code MUST Handle VoIP Push (iOS Hard Requirement)

On iOS 13+, failing to call `reportNewIncomingCall()` from a VoIP push will cause Apple to:
1. Terminate your app
2. Potentially block future VoIP push delivery

The native `AppDelegate.m` (or `AppDelegate.swift`) must:
1. Register for VoIP push in `PKPushRegistry`
2. In `didReceiveIncomingPushWith`, immediately call `reportNewIncomingCall()` on CXProvider
3. NEVER use the async version (Wire discovered it's broken for background wake)
4. Queue events for the React Native bridge via `didLoadWithEvents`

### LEARNING 2: RTCAudioSession.useManualAudio = true is MANDATORY

Every production app that uses CallKit + WebRTC enables manual audio at launch. Without it:
- WebRTC auto-configures AVAudioSession when tracks are created
- This conflicts with CallKit's audio session lifecycle
- Results in: no audio, audio cutting out, speaker button resetting

**Implementation:** Set this in `AppDelegate` before any WebRTC code runs.

### LEARNING 3: isAudioEnabled is Separate from setActive

The most common mistake is calling `rtcAudioSession.setActive(true)` without also setting `rtcAudioSession.isAudioEnabled = true`. Both are required:
- `setActive(true)` - activates the AVAudioSession
- `isAudioEnabled = true` - tells WebRTC's audio device module it can start processing

### LEARNING 4: Audio Configuration Belongs in didActivateAudioSession, NOT in performAnswerCallAction

Signal, Wire, and the "Mastering VoIP Audio" article all agree:
- `performAnswerCallAction`: just accept the call, maybe prepare resources
- `didActivateAudioSession`: this is where you configure and start audio
- Configuring audio before CallKit activates the session leads to conflicts

### LEARNING 5: Deferred Answer Pattern Prevents Cold-Start Race

Signal's deferred answer pattern is the safest approach:
1. If WebRTC/signaling isn't ready when user answers, store the completion handler
2. Don't fulfill `CXAnswerCallAction` yet
3. When ready, fulfill the deferred action
4. This ensures the CallKit -> WebRTC sequence is correct

For React Native: The `didLoadWithEvents` mechanism serves a similar purpose by caching events until the bridge is ready.

### LEARNING 6: Use continualGatheringPolicy for ICE

Signal uses `GATHER_CONTINUALLY` which enables ongoing ICE candidate discovery. Combined with state-machine reconnection handling (`reconnecting` -> `reconnected`), this provides resilient connectivity.

### LEARNING 7: Perfect Negotiation Prevents Glare

When both peers try to create offers simultaneously (common on reconnection), the Perfect Negotiation pattern prevents deadlocks by assigning polite/impolite roles.

### LEARNING 8: Audio Session Category Modes Matter

```
Audio-only call:  .playAndRecord + .voiceChat  (enables echo cancellation, proximity sensor)
Video call:       .playAndRecord + .videoChat  (disables proximity sensor)
Ringing:          .playback + .default         (for playing ringtone)
Idle:             .ambient + .default          (normal app state)
```

### LEARNING 9: Embed Offer in VoIP Push Payload

Signal embeds the call offer opaque data in the push notification itself. This eliminates the need to:
1. Wait for WebSocket connection
2. Re-fetch the offer from the server
3. Handle the race between signaling and offer delivery

### LEARNING 10: Track Message Age for Timeout

Signal calculates `messageAgeSec` from server delivery timestamps. If the offer is too old by the time the app processes it, the call is expired. This prevents answering calls that have already been missed.

---

## 6. Recommended Implementation Plan for QRChat

### Phase 1: Fix Audio Session Management (CRITICAL)

1. **Add to AppDelegate (native iOS):**
   ```objc
   // In application:didFinishLaunchingWithOptions:
   RTCAudioSession *rtcAudioSession = [RTCAudioSession sharedInstance];
   rtcAudioSession.useManualAudio = YES;
   ```

2. **In CallKitService (or native CXProviderDelegate):**
   ```
   didActivateAudioSession:
     -> RTCAudioSession.lockForConfiguration()
     -> RTCAudioSession.setConfiguration(webRTC config)
     -> RTCAudioSession.setActive(true)
     -> RTCAudioSession.isAudioEnabled = true
     -> RTCAudioSession.unlockForConfiguration()

   didDeactivateAudioSession:
     -> RTCAudioSession.isAudioEnabled = false
     -> RTCAudioSession.setActive(false)
   ```

3. **DO NOT configure audio in performAnswerCallAction**

### Phase 2: Fix Cold Start VoIP Push Handling

1. Ensure `reportNewIncomingCall()` is called synchronously in native code
2. Implement the `didLoadWithEvents` listener in JS for queued CallKeep events
3. Consider embedding SDP offer in VoIP push payload (like Signal)
4. Add message age calculation for call expiry

### Phase 3: Fix ICE Reconnection

1. Set `continualGatheringPolicy: 'gatherContinually'` in RTCConfiguration
2. Add ICE connection state monitoring:
   - `disconnected`: start 5-second timer
   - `failed`: trigger `restartIce()` + new offer
   - `connected`/`completed`: clear timers
3. Implement the Perfect Negotiation pattern for glare prevention
4. Track connection IDs for session continuity

### Phase 4: Audio Route Management

1. Use `RTCAudioSessionConfiguration.webRTC()` as base config
2. Category options: `.allowBluetooth`, `.allowBluetoothA2DP`, `.duckOthers`
3. Switch mode based on call type (voiceChat vs videoChat)
4. Use `AVAudioSession.routeChangeNotification` for route monitoring
5. Don't directly call `AVAudioSession.setActive()` during calls

---

## 7. Sources

### Signal
- [Signal iOS - GitHub](https://github.com/signalapp/Signal-iOS) (11,951 stars)
- [Signal Android - GitHub](https://github.com/signalapp/Signal-Android) (28,548 stars)
- [RingRTC - GitHub](https://github.com/signalapp/ringrtc) (625 stars)
- [How to build large-scale end-to-end encrypted group video calls](https://signal.org/blog/how-to-build-encrypted-group-calls/)

### Wire
- [Wire iOS - GitHub](https://github.com/wireapp/wire-ios) (115 stars)
- [Wire Android - GitHub](https://github.com/wireapp/wire-android) (236 stars)
- [Wire AVS - GitHub](https://github.com/wireapp/wire-avs) (142 stars)

### Jitsi Meet
- [Jitsi Meet - GitHub](https://github.com/jitsi/jitsi-meet) (28,883 stars)
- [Jitsi Meet Architecture](https://jitsi.github.io/handbook/docs/architecture/)
- [Jitsi React Native SDK](https://jitsi.github.io/handbook/docs/dev-guide/dev-guide-react-native-sdk/)
- [Jitsi react-native-webrtc fork](https://github.com/jitsi/react-native-webrtc)

### Mattermost
- [Mattermost Mobile - GitHub](https://github.com/mattermost/mattermost-mobile) (2,627 stars)
- [Mattermost Plugin Calls - GitHub](https://github.com/mattermost/mattermost-plugin-calls) (136 stars)

### Element / Matrix
- [Element Call - GitHub](https://github.com/element-hq/element-call) (924 stars)
- [Element X iOS - GitHub](https://github.com/element-hq/element-x-ios) (777 stars)

### Rocket.Chat
- [Rocket.Chat React Native - GitHub](https://github.com/RocketChat/Rocket.Chat.ReactNative) (2,373 stars)

### LiveKit
- [LiveKit Server - GitHub](https://github.com/livekit/livekit) (17,815 stars)
- [LiveKit React Native SDK - GitHub](https://github.com/livekit/client-sdk-react-native) (252 stars)

### Jami
- [Jami Android Client - GitHub](https://github.com/savoirfairelinux/jami-client-android) (189 stars)
- [Jami iOS Client - GitHub](https://github.com/savoirfairelinux/jami-client-ios) (23 stars)
- [Jami Official Site](https://jami.net/)

### Core React Native Libraries
- [react-native-webrtc - GitHub](https://github.com/react-native-webrtc/react-native-webrtc) (4,950 stars)
- [react-native-callkeep - GitHub](https://github.com/react-native-webrtc/react-native-callkeep) (1,033 stars)
- [react-native-voip-push-notification - GitHub](https://github.com/react-native-webrtc/react-native-voip-push-notification) (235 stars)
- [react-native-callkeep Issue #847: VoIP Push Cold Start Problem](https://github.com/react-native-webrtc/react-native-callkeep/issues/847)

### Technical Articles
- [Mastering VoIP Audio with CallKit and WebRTC on iOS](https://medium.com/@tsivilko/mastering-voip-audio-with-callkit-and-webrtc-on-ios-0f2092402331)
- [WebRTC Perfect Negotiation Pattern - MDN](https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API/Perfect_negotiation)
- [RTCPeerConnection.restartIce() - MDN](https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection/restartIce)
- [ICE Restarts - Fippo](https://medium.com/@fippo/ice-restarts-5d759caceda6)
- [react-native-webrtc iOS Installation Guide](https://github.com/react-native-webrtc/react-native-webrtc/blob/master/Documentation/iOSInstallation.md)
- [CallKit Not Activating Audio Session - Apple Forums](https://developer.apple.com/forums/thread/64544)
- [Audio Challenges in React Native iOS Calls - QuickBlox](https://quickblox.com/blog/audio-challenges-in-react-native-ios-calls-troubleshooting-and-solutions/)
