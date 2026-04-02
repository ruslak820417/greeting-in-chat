# WhatsApp Call System -- Deep Technical Research

**Date:** 2026-03-31
**Purpose:** Reference architecture for implementing production-grade calling in QRChat (React Native encrypted messenger)

---

## 1. CALL SIGNALING ARCHITECTURE

### Protocol Stack (Layered)

WhatsApp uses a **four-layer protocol stack** for calls:

| Layer | Protocol | Purpose |
|-------|----------|---------|
| Transport Encryption | **Noise Pipes** (Noise_XX_25519_AESGCM_SHA256) | Encrypts all TCP traffic between client and WhatsApp servers |
| Signaling | **FunXMPP** (custom binary XMPP variant) | Call initiation, control, termination signals |
| E2E Key Exchange | **Signal Protocol** (Double Ratchet + X3DH) | Encrypts SRTP master secret for delivery |
| Media Encryption | **SRTP** (AES-128-ICM) | Encrypts audio/video RTP packets |

### FunXMPP Signaling Details

- WhatsApp does NOT use standard XMPP. They use **FunXMPP**, a compressed binary encoding that reduces XMPP bandwidth by **50-70%**.
- TCP traffic runs on port **5222** (standard XMPP port).
- All XMPP stanzas are encrypted with **AES-256-GCM** via the Noise Pipes protocol before transmission.
- Call signaling messages (offer, answer, ICE candidates, bye) are embedded in binary XMPP stanzas with call metadata (call-id, participant JIDs).

### Call Setup Flow (Step by Step)

```
CALLER                          SERVER                          CALLEE
  |                               |                               |
  |  1. Generate 32-byte SRTP     |                               |
  |     master secret             |                               |
  |                               |                               |
  |  2. Serialize via protobuf    |                               |
  |     + padding                 |                               |
  |                               |                               |
  |  3. Encrypt master secret     |                               |
  |     with Signal Protocol      |                               |
  |     (AES-256-CBC + HMAC-SHA256)|                              |
  |                               |                               |
  |  4. Pack into Signal message  |                               |
  |     with sender ratchet keys  |                               |
  |                               |                               |
  |  5. Embed in XMPP stanza     |                               |
  |     with call-id, participants|                               |
  |                               |                               |
  |  6. Encrypt XMPP stanza with |                               |
  |     AES-256-GCM (Noise Pipes) |                               |
  |                               |                               |
  |  7. Send via TCP ------------>|                               |
  |                               |  8. Forward encrypted stanza  |
  |                               |     to callee (+ VoIP push    |
  |                               |     if app not connected) --->|
  |                               |                               |
  |                               |                               | 9. Decrypt Noise layer
  |                               |                               | 10. Decrypt Signal layer
  |                               |                               | 11. Extract SRTP master secret
  |                               |                               |
  |                               |                               | 12. Show incoming call UI
  |                               |                               |
  |                               |  13. Accept signal <--------- |
  |  14. <----------------------- |                               |
  |                               |                               |
  |  15. Start SRTP-encrypted     |                               |
  |      media via UDP ==========================================>|
  |                               |                               |
```

### Server Role During Active Call

- **During signaling:** Server forwards encrypted XMPP stanzas between peers. Server cannot read the content (E2E encrypted).
- **During active call:** Server acts as a **relay** for media packets (SRTP-encrypted UDP). Server caches a few seconds of packets for NACK-based retransmission. Server measures packet delay and loss and provides bandwidth feedback to devices.
- **Server CANNOT:** Decrypt media, modify packets, or access SRTP master secrets.

### Offline/Killed App Handling

When the recipient's app is not connected to the WhatsApp server:
1. Server sends a **VoIP push notification** (APNs PushKit on iOS, FCM high-priority on Android).
2. The push wakes the app / launches it from killed state.
3. App establishes Noise Pipes connection to server.
4. Server delivers the pending call signaling message.
5. App decrypts and presents incoming call UI.

---

## 2. VoIP PUSH / WAKE-UP SYSTEM (iOS)

### PushKit/CallKit Flow

```
APNs                  iOS                    APP                   CallKit
 |                     |                      |                      |
 | 1. VoIP Push ------>|                      |                      |
 |                     | 2. Wake/Launch app -->|                      |
 |                     |                      |                      |
 |                     |                      | 3. pushRegistry(     |
 |                     |                      |    didReceiveIncoming |
 |                     |                      |    PushWith:)         |
 |                     |                      |                      |
 |                     |                      | 4. reportNewIncoming  |
 |                     |                      |    Call() ----------->|
 |                     |                      |                      |
 |                     |                      |                      | 5. Show native
 |                     |                      |                      |    call UI
 |                     |                      |                      |
 |                     |                      | 6. Connect to server  |
 |                     |                      |    via Noise Pipes    |
 |                     |                      |                      |
 |                     |                      | 7. Receive SDP/ICE    |
 |                     |                      |    from signaling     |
 |                     |                      |                      |
 |                     |                      | 8. Set up WebRTC      |
 |                     |                      |    peer connection    |
 |                     |                      |                      |
 |                     |   didActivate ------->| 9. Activate audio    |
 |                     |   audioSession        |    session           |
 |                     |                      |                      |
```

### Critical iOS Requirements (iOS 13+)

1. **MUST report call to CallKit immediately** inside `pushRegistry(_:didReceiveIncomingPushWith:for:completion:)` -- in the same run loop, without delay.
2. **Failure to report = app termination.** iOS kills VoIP apps that fail to call `reportNewIncomingCall` after receiving a VoIP push. System error: `"Killing VoIP app because it failed to post an incoming call in time."`
3. **Repeated failures = permanent VoIP push block.** Apple will stop delivering VoIP pushes entirely to apps that repeatedly fail.
4. **No exact timeout documented** -- Apple says "without delay" / "same run loop." Observed enforcement ranges from ~2-8 seconds in practice, but do NOT rely on any grace period.

### Cold Start Strategy (App Was Killed)

This is the hardest problem. When the app is killed:

1. iOS launches the app process in response to VoIP push.
2. App has very limited time to initialize.
3. **You MUST call `reportNewIncomingCall` before doing anything else.**
4. The call details in the push payload must contain enough info (caller name, caller ID) to report the call immediately.
5. Full WebRTC setup happens AFTER the call is reported to CallKit.
6. If the caller hangs up before WebRTC connects, call `reportCallWithUUID:endedAtDate:reason:` to tear down the UI.

### WhatsApp's Special Entitlement

WhatsApp has a **restricted entitlement**: `com.apple.developer.pushkit.unrestricted-voip` that allows it to receive VoIP pushes WITHOUT reporting to CallKit. This is used for background sync (WhatsApp Web). **Regular apps cannot get this entitlement.**

### Best Practices for Cold Start

```
1. Keep VoIP push payload SMALL (faster delivery)
2. Include caller info in payload (name, avatar URL, call type)
3. Call reportNewIncomingCall IMMEDIATELY in push handler
4. Do NOT wait for server connection before reporting
5. Set up WebRTC asynchronously after reporting
6. If call fails to connect, end it via reportEndCall
7. Use apns-priority: 10 for immediate delivery
8. Set apns-push-type: voip header
9. Test with app KILLED and device LOCKED
10. Never use VoIP push for non-call purposes (Apple will block)
```

---

## 3. WebRTC / MEDIA IMPLEMENTATION

### WhatsApp's Actual Stack (NOT Pure WebRTC)

WhatsApp does **NOT** use standard WebRTC. They use a hybrid:

| Component | Library | Purpose |
|-----------|---------|---------|
| VoIP engine | **PJSIP** | Core voice/video call functionality |
| Echo cancellation | **WebRTC AEC/AECM** | Acoustic echo cancellation |
| Gain control | **WebRTC AGC** | Automatic gain control |
| Noise suppression | **WebRTC NS** | Background noise reduction |
| High-pass filter | **WebRTC HPF** | Audio quality improvement |
| Media encryption | **libsrtp** (Cisco) | SRTP stream encryption |
| Crypto primitives | **libsignal-protocol-c** | Signal Protocol for key exchange |
| TLS/crypto | **mbed TLS** | AES-GCM, TLS operations |

### Codec Details

**Audio Codecs:**
- **Opus/SILK** at 16kHz sampling, ~20kbit/s bandwidth
- **MLow** (Meta's custom codec) -- being rolled out as of 2024-2025
  - 2x better quality than Opus at 6kbps (POLQA MOS 1.89 vs 3.9)
  - 10% lower computational complexity than Opus
  - Split-band encoding: divides audio into low/high frequency bands
  - SuperWideBand (32kHz) at much lower bitrate than Opus
  - Classic CELP foundation with improved excitation generation
  - Better Forward Error Correction at lower bitrates
  - Designed for ARMv7 (10+ year old devices)

**Video:**
- Custom RTP payload type (PT=60, not in RFC standards)
- Adaptive resolution based on bandwidth
- Simulcast for group calls (high + low bitrate streams)

### ICE / NAT Traversal (Non-Standard)

WhatsApp does NOT use standard ICE. Their approach:

1. **No ICE attributes in STUN requests** -- they send raw STUN binding requests without ICE-specific attributes.
2. **Simultaneous TURN allocation to 8 servers** -- client sends allocation requests to 8 different geographically distributed TURN servers simultaneously.
3. **RTP/RTCP multiplexed** on the same port.
4. **Raw RTP over relay** -- not standard TURN send/data indications.
5. **No DTLS detected** -- uses SDES encryption approach instead.

### Relay-to-P2P Switch (Key Innovation)

WhatsApp's call setup prioritizes reliability then optimizes for quality:

```
Phase 1: RELAY (immediate, reliable)
  1. Query 8 TURN servers simultaneously
  2. Establish session through relay/conference bridge
  3. Media flows through relay (adds latency but works immediately)
  4. Call is "connected" from user perspective

Phase 2: P2P PROBE (background optimization)
  5. Client sends STUN binding requests to peer's public IP
  6. If peer responds, P2P path is viable

Phase 3: SEAMLESS SWITCH (if P2P available)
  7. RTP stream destination switches from relay to peer
  8. Sequence numbers maintain continuity
  9. Switch is transparent to users
  10. Falls back to relay if P2P drops
```

**Why this matters for QRChat:** This relay-first strategy ensures calls connect quickly even behind symmetric NATs. The P2P optimization reduces latency and server load when possible.

### Offer/Answer Exchange

WhatsApp uses a **custom offer/answer mechanism** (not standard SDP offer/answer as in WebRTC):

- Call initiation contains SRTP master secret + call parameters
- Responder accepts and media begins
- SDP-like negotiation happens but through the custom XMPP signaling
- Renegotiation (e.g., video toggle) appears to use similar custom mechanism

### Trickle ICE vs Full ICE

WhatsApp appears to use a **custom variant** that gathers all candidates (8 TURN servers + direct peer) simultaneously and starts media through the first available path (relay), rather than standard trickle ICE or full ICE.

---

## 4. AUDIO SESSION MANAGEMENT (iOS)

### AVAudioSession Configuration for WebRTC + CallKit

**CORRECT approach** (via RTCAudioSession):

```swift
// In AppDelegate / app startup
RTCAudioSession.sharedInstance().useManualAudio = true

// Configure via WebRTC's audio session (NOT AVAudioSession directly)
let rtcAudioSession = RTCAudioSession.sharedInstance()
rtcAudioSession.lockForConfiguration()
let configuration = RTCAudioSessionConfiguration.webRTC()
configuration.categoryOptions = [
    .allowBluetoothA2DP,
    .duckOthers,
    .allowBluetooth,
    .mixWithOthers
]
try rtcAudioSession.setConfiguration(configuration)
rtcAudioSession.unlockForConfiguration()
```

**WRONG approach:** Directly calling `AVAudioSession.setCategory()` -- this conflicts with WebRTC's internal audio management and causes speaker button resets.

### CallKit Audio Lifecycle

```
Call Flow              Audio State              Key Action
─────────────────────────────────────────────────────────────
VoIP push received     Audio INACTIVE           reportNewIncomingCall()
User answers           Audio INACTIVE           fulfill CXAnswerCallAction
                       Audio ACTIVATING         system triggers didActivate
didActivate fires      Audio ACTIVE             RTCAudioSession.audioSessionDidActivate()
                                                RTCAudioSession.isAudioEnabled = true
Call in progress       Audio ACTIVE             Media flows
User ends call         Audio ACTIVE             fulfill CXEndCallAction
didDeactivate fires    Audio DEACTIVATING       RTCAudioSession.audioSessionDidActivate()
                       Audio INACTIVE           setCategory(.playback, mode: .default)
```

### Critical Rules

1. **NEVER call `AVAudioSession.sharedInstance().setActive()` during an active call** -- use RTCAudioSession instead.
2. **NEVER activate audio in `perform` delegate methods** -- only activate in `didActivate`.
3. **Set `isAudioEnabled = true`** -- prevents speaker button from resetting during connection.
4. **Deactivate properly on call end** -- switch category back to `.playback` with `.default` mode.

### Speaker / Earpiece / Bluetooth Switching

```swift
// Listen for route changes
NotificationCenter.default.addObserver(
    self,
    selector: #selector(handleRouteChange),
    name: AVAudioSession.routeChangeNotification,
    object: nil
)

// Detect current output:
// .builtInSpeaker   -> Speaker
// .builtInReceiver  -> Earpiece
// .headphones       -> Wired headphones
// .bluetoothHFP     -> Bluetooth hands-free
// .bluetoothA2DP    -> Bluetooth audio
```

### Audio Interruptions (Another Call, Siri, etc.)

- CallKit automatically handles interruptions from cellular calls.
- If a cellular call comes in during a VoIP call, CallKit puts the VoIP call on hold.
- Siri interruptions temporarily suspend audio session.
- WhatsApp handles this by showing "Call on hold" state and attempting reconnection when audio resumes.

---

## 5. VIDEO CALL ARCHITECTURE

### Audio-to-Video Upgrade

Two approaches for toggling video mid-call:

**Approach A: SDP Renegotiation (addTrack)**
```
1. User taps "video" button
2. App calls addTrack() with camera stream on PeerConnection
3. This fires onnegotiationneeded event
4. New offer/answer exchange (SDP renegotiation)
5. Remote peer receives video track
6. Both sides render video
```

**Approach B: replaceTrack (NO renegotiation needed)**
```
1. Pre-negotiate with a dummy/disabled video track in initial SDP
2. When user enables video:
   - RTCRtpSender.replaceTrack(realVideoTrack)
   - No SDP renegotiation needed
   - Track just starts sending data
3. Much faster than Approach A
```

**Approach C: SSRC/MSID approach (Slack style)**
```
1. Include both audio AND video tracks in initial SDP
2. Video track initially disabled (no data flowing)
3. When user enables video:
   - Enable the track (start sending RTP packets)
   - Only SSRC MSID changes in local description
   - No full renegotiation needed
```

WhatsApp likely uses Approach B or C for fast video toggle.

### Camera Management

- Front/back switching uses `replaceTrack()` -- no renegotiation needed.
- The sender replaces the camera MediaStreamTrack on the existing RTCRtpSender.

### Resolution / Framerate Adaptation

WhatsApp uses **bandwidth-based adaptive quality:**

1. **Relay-level feedback:** Relay measures packet delay and loss, sends feedback to devices.
2. **Sender-side estimation:** Modern WebRTC uses TWCC (Transport-Wide Congestion Control) for bandwidth estimation.
3. **GCC (Google Congestion Control):** Sender and receiver collaborate to estimate available bandwidth via abs-send-time RTP header extensions.
4. **Simulcast for group calls:** Devices with good connectivity send multiple quality layers; relay selects appropriate layer per recipient.
5. **Dynamic video subscriptions:** Server turns video on/off per participant based on relevance (e.g., active speaker gets high quality).

### Video Rendering

- On native iOS/Android: Video is rendered in **native views** (not web views).
- For React Native: Use `RTCView` from react-native-webrtc, which renders as a native `UIView`/`SurfaceView`.
- WhatsApp renders video directly via native PJSIP video pipeline, not through a WebView.

---

## 6. NETWORK RESILIENCE

### Network Change Detection (WiFi -> Cellular)

WhatsApp handles network transitions through:

1. **ICE restart** -- when network changes are detected, trigger ICE restart to establish new media path.
2. **Relay re-routing** -- the relay infrastructure recomputes optimal routing when "significant changes in ongoing call conditions" occur.
3. **Continuous monitoring** -- system monitors for IP address changes, NAT timeout, carrier restrictions.

### ICE Restart Strategy

```
1. Monitor ICE connection state
2. When state changes to "disconnected":
   - Wait 3-4 seconds (NOT 30 seconds for "failed")
   - Trigger ICE restart: pc.restartIce()
   - This creates new ICE credentials
   - Re-gathers candidates
   - Performs new connectivity checks
   - Existing media continues during restart
3. Success rate: ~66% of ICE restarts recover the connection
4. If ICE restart fails, fall back to relay path
5. If relay also fails, show "Reconnecting..." to user
```

### Reconnection Logic

```
State: CONNECTED
  |
  |  Network interruption detected
  v
State: RECONNECTING (show to user)
  |
  |  Step 1: Attempt ICE restart (3-4 seconds)
  |  Step 2: If ICE restart succeeds -> CONNECTED
  |  Step 3: If ICE restart fails, try relay fallback
  |  Step 4: If relay works -> CONNECTED (via relay)
  |  Step 5: If nothing works after timeout -> ENDED
  |
  v
State: ENDED (call dropped)
```

### Call Quality Adaptation

WhatsApp's relay infrastructure provides:

1. **NACK-based retransmission** -- relay caches a few seconds of media packets and retransmits on NACK requests. More efficient than end-to-end retransmission because relay is geographically between the two peers.
2. **Bandwidth feedback** -- relay measures delay and loss, shares feedback with devices.
3. **MLow codec adaptation** -- better FEC at lower bitrates, handles packet loss better than Opus.
4. **Video simulcast** -- multiple quality layers, server selects per-recipient.

---

## 7. CALL STATE MACHINE

### Complete State Diagram

```
                         ┌─────────────┐
                         │    IDLE      │
                         └──────┬──────┘
                                │
                    ┌───────────┼───────────┐
                    │                       │
                    v                       v
           ┌──────────────┐        ┌──────────────┐
           │  CALLING     │        │  RINGING      │
           │  (outgoing)  │        │  (incoming)   │
           └──────┬───────┘        └──────┬───────┘
                  │                       │
                  │  callee accepts       │  user answers
                  │                       │
                  v                       v
           ┌──────────────────────────────┐
           │         CONNECTING           │
           │  (ICE + SRTP negotiation)    │
           └──────────────┬───────────────┘
                          │
                          v
           ┌──────────────────────────────┐
           │         CONNECTED            │
           │  (media flowing)             │
           └──┬───────────────────────┬───┘
              │                       │
              v                       v
     ┌────────────────┐     ┌─────────────────┐
     │  RECONNECTING  │     │   ON HOLD        │
     │  (ICE restart) │     │  (interruption)  │
     └───────┬────────┘     └────────┬─────────┘
             │                       │
             │  recovered            │  resumed
             v                       v
     ┌──────────────────────────────────┐
     │           CONNECTED              │
     └──────────────┬───────────────────┘
                    │
                    │  user/peer ends or timeout
                    v
           ┌──────────────────┐
           │      ENDED       │
           └──────────────────┘
```

### Call Timeouts

| Timeout | Duration (estimated) | Action |
|---------|---------------------|--------|
| Ring timeout | ~45-60 seconds | End call, show "No Answer" |
| Connect timeout | ~30 seconds | End call, show "Call Failed" |
| Reconnect timeout | ~30-60 seconds | Drop call, show "Call Ended" |
| ICE disconnect -> restart | ~3-4 seconds | Trigger ICE restart |
| ICE failed | ~30 seconds | Connection unrecoverable |

### Offer Glare / Simultaneous Calls

When both users call each other simultaneously, this is called "offer glare." The standard WebRTC solution is the **Perfect Negotiation Pattern:**

**Roles:**
- **Polite peer:** Rolls back its own offer when collision detected, accepts the other peer's offer.
- **Impolite peer:** Ignores incoming offers that collide with its own offer.

**Implementation:**

```javascript
// Collision detection
const readyForOffer = !makingOffer &&
  (pc.signalingState === "stable" || isSettingRemoteAnswerPending);
const offerCollision = description.type === "offer" && !readyForOffer;
ignoreOffer = !polite && offerCollision;

// Polite peer: accept incoming, rollback own
// Impolite peer: ignore incoming, keep own
if (ignoreOffer) return;
await pc.setRemoteDescription(description); // auto-rollback for polite
```

**Role assignment:**
- Assign based on deterministic comparison (e.g., lower user-ID = polite).
- Or assign at signaling server (first to connect = polite).

**For QRChat:** Use the caller with the lexicographically lower user ID as the "polite" peer.

### Call End Propagation

WhatsApp uses **BYE signals via SIP/XMPP** to reliably end calls:

1. User taps "End Call."
2. App sends BYE signal through signaling server.
3. Server forwards to other party.
4. Both sides tear down media.
5. If signaling delivery fails (network gone), the other side detects via ICE connection state change to "failed" and times out.
6. Server also monitors and can send timeout-based termination.

---

## 8. SECURITY

### E2E Encryption for Calls

**Key Exchange (Signal Protocol):**

1. Both users have long-term identity keys (Curve25519).
2. Signal Protocol uses X3DH (Extended Triple Diffie-Hellman) for initial key exchange.
3. Double Ratchet Algorithm provides forward secrecy for subsequent messages.
4. The SRTP master secret is encrypted using the established Signal Protocol session.

**SRTP Master Secret Flow:**

```
1. Initiator generates random 32-byte SRTP master secret
2. For EACH of recipient's devices:
   a. Encrypt master secret with Signal Protocol
      - AES-256-CBC encryption
      - HMAC-SHA256 authentication
   b. Include sender's ratchet keys in Signal message
3. Send encrypted master secrets via signaling
4. Recipient decrypts on answering device
5. Both sides derive SRTP keys from master secret
```

**SRTP Key Derivation (HKDF):**

```
Input:  32-byte master secret
KDF:    HKDF (RFC 5869) using HMAC-SHA256
Info:   Caller JID + Callee JID
Output: Keys, salts, and nonces for SRTP initialization

Specifically:
- Three successive HMAC-SHA256 computations
- Derives parameters for 6 SRTP streams (3 bidirectional pairs)
- Used with AES-128-ICM cipher mode
- 4-byte authentication tags for integrity
```

**Group Call Encryption:**

- Same E2E model, but keys are **reset** whenever a participant joins or leaves.
- Each new participant triggers new master secret generation and distribution.
- This ensures forward/backward secrecy within group calls.

### Known Security Considerations

From Google Project Zero and independent research:

1. **Four simultaneous SRTP streams** with distinct SSRCs for video calls.
2. **Some SRTP streams lack integrity checking** -- certain streams compute auth tags using zero-byte inputs rather than actual packets.
3. **Initial call messages lack proper sender verification** -- potential for caller impersonation.
4. **CVE-2018-6344** -- heap corruption in RTP packet processing (patched).
5. **No DTLS** -- WhatsApp uses SDES-style key exchange (master secret sent through Signal Protocol) rather than DTLS-SRTP.

### Why SDES over DTLS-SRTP?

WhatsApp's approach of encrypting the SRTP master secret through the Signal Protocol (which already provides E2E encryption) is arguably more secure than standard DTLS-SRTP because:
- DTLS-SRTP's key exchange can be MitM'd if certificates are not verified.
- Signal Protocol provides verified E2E encryption with forward secrecy.
- The master secret never passes through any server in decryptable form.

---

## 9. WHATSAPP RELAY INFRASTRUCTURE (At Scale)

### Scale

- **Well over 1 billion calls per day.**
- **Thousands of Points-of-Presence (PoPs)** worldwide, built on Meta's CDN.
- PoPs connected via **high-quality exclusive backbone links.**

### Architecture

```
User A  <--->  PoP (closest to A)  <==backbone==>  PoP (closest to B)  <--->  User B
                    ^                                     ^
                    |                                     |
              Relay Server                          Relay Server
              (caches packets,                      (caches packets,
               measures quality,                     measures quality,
               provides feedback)                    provides feedback)
```

### Key Features

1. **Sophisticated targeting algorithms** use historical latency data to select optimal relay cluster.
2. **Dynamic re-routing** -- relay selection can change mid-call (e.g., WiFi to cellular switch).
3. **NACK retransmission** -- relay caches seconds of packets, retransmits on request.
4. **Dominant speaker detection** -- devices report volume info to relay (privacy-preserving).
5. **Video simulcast** -- high+low bitrate streams, selective forwarding.
6. **Video subscriptions** -- dynamic on/off per participant based on relevance.

---

## 10. IMPLEMENTATION RECOMMENDATIONS FOR QRCHAT

### Architecture Decisions

| Decision | WhatsApp Approach | QRChat Recommendation |
|----------|-------------------|----------------------|
| Signaling | Custom FunXMPP | WebSocket + JSON (simpler, sufficient for scale) |
| Media | PJSIP + custom | Standard WebRTC (react-native-webrtc) |
| ICE | Custom 8-server probe | Standard ICE with trickle, 2-3 TURN servers |
| Encryption | Signal Protocol + SRTP | TweetNaCl for key exchange + SRTP (already have crypto) |
| Push | VoIP Push (PushKit) | PushKit + react-native-voip-push-notification |
| CallKit | Native | react-native-callkeep |
| Audio | PJSIP + WebRTC AEC | react-native-incall-manager + WebRTC built-in |
| Codec | MLow (custom) | Opus (WebRTC default, excellent quality) |

### Critical Implementation Checklist

```
[ ] PushKit VoIP push -> reportNewIncomingCall IMMEDIATELY
[ ] RTCAudioSession.useManualAudio = true at app startup
[ ] Perfect Negotiation pattern for offer/answer
[ ] Relay-first, P2P-optimize strategy for NAT traversal
[ ] ICE restart on disconnected state (3-4 second delay)
[ ] SRTP encryption via existing TweetNaCl crypto
[ ] Call state machine with all states
[ ] Cold start: report call to CallKit BEFORE WebRTC setup
[ ] Audio route change handling (speaker/earpiece/bluetooth)
[ ] Video toggle via replaceTrack (no renegotiation)
[ ] Proper audio deactivation on call end
[ ] Call timeout handling (ring, connect, reconnect)
[ ] Network change detection -> ICE restart
[ ] Offer glare resolution (polite/impolite peers)
```

### React Native Library Stack

```
react-native-webrtc          -- WebRTC peer connection
react-native-callkeep        -- CallKit (iOS) + ConnectionService (Android)
react-native-voip-push-notification  -- PushKit VoIP pushes (iOS)
react-native-incall-manager  -- Audio routing, proximity sensor
```

---

## Sources

- [WhatsApp and WebRTC Analysis - webrtcHacks](https://webrtchacks.com/whats-up-with-whatsapp-and-webrtc/)
- [Analyzing WhatsApp Calls with Wireshark - Marvin Schirrmacher](https://medium.com/@schirrmacher/analyzing-whatsapp-calls-176a9e776213)
- [WhatsApp Encryption Overview Whitepaper](https://docplayer.net/31371920-Whatsapp-encryption-overview-technical-white-paper.html)
- [Calling Relay Infrastructure at WhatsApp Scale](https://atscaleconference.com/calling-relay-infrastructure-at-whatsapp-scale/)
- [MLow: Meta's Low Bitrate Audio Codec](https://engineering.fb.com/2024/06/13/web/mlow-metas-low-bitrate-audio-codec/)
- [Google Project Zero: WhatsApp Video Conferencing](https://projectzero.google/2018/12/adventures-in-video-conferencing-part-3.html)
- [Mastering VoIP Audio with CallKit and WebRTC](https://medium.com/@tsivilko/mastering-voip-audio-with-callkit-and-webrtc-on-ios-0f2092402331)
- [WebRTC Perfect Negotiation Pattern - MDN](https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API/Perfect_negotiation)
- [PushKit for Calls - Stream](https://getstream.io/blog/pushkit-for-calls/)
- [VoIP Push Troubleshooting - ConnectyCube](https://connectycube.com/2025/11/06/troubleshooting-common-issues-with-voip-push-notifications-on-ios/)
- [ICE Restarts - Philipp Hancke](https://medium.com/@fippo/ice-restarts-5d759caceda6)
- [WebRTC Congestion Control - Kurento Docs](https://doc-kurento.readthedocs.io/en/stable/knowledge/congestion_rmcat.html)
- [Apple PushKit Documentation](https://developer.apple.com/documentation/pushkit/responding-to-voip-notifications-from-pushkit)
- [WhatsApp Better Calling Blog](https://blog.whatsapp.com/better-calling-across-desktop-and-mobile)
- [react-native-callkeep](https://github.com/react-native-webrtc/react-native-callkeep)
- [react-native-incall-manager](https://github.com/react-native-webrtc/react-native-incall-manager)
- [WhatsApp Network Forensics - ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1742287615000985)
- [Signal Protocol - Wikipedia](https://en.wikipedia.org/wiki/Signal_Protocol)
- [Meta Engineering: WhatsApp Interoperability](https://engineering.fb.com/2024/03/06/security/whatsapp-messenger-messaging-interoperability-eu/)
