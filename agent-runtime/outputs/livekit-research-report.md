# LiveKit Integration Research Report for QRChat

**Date:** 2026-03-30
**Researcher:** Claude Opus 4.6
**Scope:** Feasibility and integration plan for LiveKit in QRChat (React Native 0.84, encrypted messenger with WebRTC calls)
**Overall Confidence:** HIGH (verified via official docs, npm registry, and GitHub issues)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [8 Mandatory Questions -- Answers](#8-mandatory-questions)
3. [QRChat Current Architecture](#qrchat-current-architecture)
4. [LiveKit Integration Plan](#livekit-integration-plan)
5. [npm Dependencies: Add/Remove](#npm-dependencies)
6. [Native iOS Changes](#native-ios-changes)
7. [Files Modified Estimate](#files-modified)
8. [Risks and Mitigations](#risks-and-mitigations)
9. [Decision Matrix: LiveKit Cloud vs Self-Hosted](#decision-matrix)
10. [Sources](#sources)

---

## Executive Summary

LiveKit is an SFU-based (Selective Forwarding Unit) real-time communication platform. It does NOT do peer-to-peer -- all media flows through the LiveKit server. This is the single most important architectural difference from QRChat's current P2P WebRTC implementation.

**The critical finding:** `@livekit/react-native-webrtc` and `react-native-webrtc` **CANNOT coexist** in the same project. They both bundle their own `webrtc.xcframework` and the iOS build fails with framework naming conflicts. This is officially confirmed by the LiveKit team (GitHub issue #2809, closed as "not planned").

**What this means for QRChat:** Since QRChat uses `react-native-webrtc` for BOTH calls AND P2P data channels (encrypted messaging), migrating to LiveKit for calls would require either:
- **Option A:** Replace `react-native-webrtc` entirely with `@livekit/react-native-webrtc` and rewrite the data channel messaging to use LiveKit's data API or a separate transport
- **Option B:** Abandon P2P data channels entirely and route all messaging through the signaling server (already the primary path)
- **Option C:** Use LiveKit for calls only via the `livekit-client` JS SDK without the native React Native bindings (untested, likely audio issues)

LiveKit does NOT manage CallKit, PushKit, or cold start flows automatically. All of those remain the developer's responsibility. LiveKit only manages the media connection (audio/video streams via its SFU).

---

## 8 Mandatory Questions

### Q1: Does LiveKit SDK manage CallKit automatically?

**Answer: NO.** Confidence: HIGH

LiveKit does not include any CallKit management. The official documentation explicitly recommends using `react-native-callkeep` for CallKit integration, treating it as a separate concern. The LiveKit React Native SDK handles only the media connection layer (room join/leave, track publish/subscribe).

QRChat's existing CallKit setup via `react-native-callkeep` (in `CallKitService.ts`, `AppDelegate.swift`, and `index.js`) would remain entirely manual and unchanged. The developer must continue to:
- Call `RNCallKeep.reportNewIncomingCall()` on VoIP push
- Handle `answerCall` / `endCall` events
- Manage `CXProvider` delegate callbacks

### Q2: Does LiveKit SDK manage PushKit/VoIP push automatically?

**Answer: NO.** Confidence: HIGH

LiveKit has zero VoIP push infrastructure. The entire PushKit flow remains manual:
- VoIP token registration (`PKPushRegistry` in `AppDelegate.swift`)
- VoIP push sending (server-side via APNs, currently in `server/push.js`)
- Push payload handling and SDP delivery

With LiveKit, the VoIP push payload would change: instead of sending the SDP offer in the push, you would send a LiveKit room name + token (or just a signal to fetch a token from your server).

### Q3: Does LiveKit SDK manage AVAudioSession (useManualAudio) automatically?

**Answer: PARTIALLY.** Confidence: HIGH

LiveKit provides the `useIOSAudioManagement` hook that dynamically configures `AVAudioSession` based on track publish/unpublish events. It sets audio category, mode, and options automatically.

However, for CallKit integration (which QRChat uses), you MUST handle `RTCAudioSession.audioSessionDidActivate()` / `audioSessionDidDeactivate()` manually in the `CXProvider` delegate, exactly as QRChat already does in `AppDelegate.swift` (lines 41-69) and `index.js` (lines 46-76).

LiveKit's `AudioSession.startAudioSession()` replaces the need for `useManualAudio = true` configuration -- LiveKit handles this internally. But the CallKit interplay remains manual.

### Q4: What happens with react-native-webrtc?

**Answer: @livekit/react-native-webrtc REPLACES it. They CANNOT coexist.** Confidence: HIGH

This is confirmed by:
- **LiveKit team statement** (GitHub issue #2809): "Unfortunately, this is unavoidable as LiveKit also bundles our own version of react-native-webrtc and WebRTC framework."
- **Build failure evidence**: Both packages bundle `webrtc.xcframework` in the iOS Pods target, causing "conflicting names" error
- **npm registry**: `@livekit/react-native-webrtc` v144.0.0 is a fork of `react-native-webrtc` with a different underlying WebRTC revision (v144 vs QRChat's v124)

**Impact on QRChat:**

| QRChat Feature | Uses react-native-webrtc? | Impact |
|----------------|--------------------------|--------|
| Voice/video calls | YES (RTCPeerConnection, mediaDevices, RTCView) | Must switch to @livekit/react-native-webrtc imports |
| P2P data channels (messaging) | YES (RTCPeerConnection, DataChannel) | **CRITICAL** -- must verify @livekit/react-native-webrtc exposes same APIs |
| RTCAudioSession (cold start) | YES (audioSessionDidActivate) | Must verify API compatibility |
| RTCView (video rendering) | YES | Must verify component exists in fork |

The good news: `@livekit/react-native-webrtc` is a fork that preserves the same JavaScript API surface. Imports like `RTCPeerConnection`, `RTCSessionDescription`, `RTCIceCandidate`, `mediaDevices`, and `RTCView` should all work by changing the import path from `react-native-webrtc` to `@livekit/react-native-webrtc`. This needs testing but is architecturally sound since it's a direct fork.

### Q5: Is there native support for cold start calls?

**Answer: NO.** Confidence: HIGH

LiveKit has no cold start call handling. The entire cold start flow -- which QRChat has invested heavily in building (`ColdStartCoordinator.ts` with PATH A/B/C SDP retrieval, `index.js` early event capture, `AppDelegate.swift` PendingVoIPCall storage) -- remains 100% the developer's responsibility.

With LiveKit, the cold start flow would simplify somewhat because you no longer need to pass SDP offers through VoIP push payloads. Instead:
1. VoIP push arrives with `{roomName, callerName, isVideo}` (no SDP needed)
2. CallKit shows native UI (same as now)
3. User answers
4. App generates/fetches a LiveKit token from your server
5. App connects to LiveKit room
6. Audio/video starts flowing through SFU

This eliminates the 3-path SDP retrieval complexity (PATH A/B/C) but introduces a new dependency: the app must reach your token server before audio can start. Currently QRChat can start audio using SDP from the VoIP push payload without any server round-trip.

### Q6: What's needed on server?

**Answer: Token generation on your server + a LiveKit server (SFU).** Confidence: HIGH

There are TWO server-side requirements:

**1. Token Generation (add to existing server/index.js)**
```
npm install livekit-server-sdk
```
Add an endpoint that generates JWT tokens with room permissions. This is lightweight -- just JWT signing with your API key/secret. Can be added directly to QRChat's existing Node.js server.

**2. LiveKit SFU Server (new infrastructure)**
This is the major new requirement. LiveKit is NOT just signaling -- it's an SFU that routes all media. You need either:

| Option | Cost | Maintenance | Latency |
|--------|------|-------------|---------|
| **LiveKit Cloud** (recommended) | Free tier: 5,000 WebRTC min/mo | Zero | Low (global edge) |
| **Self-hosted (Docker)** | Your server costs | You manage it | Depends on server location |
| **Self-hosted (Kubernetes)** | Higher server costs | Significant | Configurable |

**You CANNOT use LiveKit with "just token generation."** The SFU server is mandatory -- all audio/video streams pass through it. This is fundamentally different from QRChat's current P2P architecture where the server is only used for signaling and the media flows directly between phones.

### Q7: LiveKit Cloud free tier?

**Answer:** Confidence: HIGH (verified from livekit.com/pricing, March 2026)

| Resource | Free Tier (Build Plan) | Ship Plan ($50/mo) |
|----------|----------------------|---------------------|
| WebRTC participant minutes | 5,000/month | 150,000/month |
| Concurrent connections | 100 | Higher |
| Agent session minutes | 1,000/month | 5,000/month |
| Credit card required | No | Yes |

**Practical impact for QRChat:**

A "participant minute" = time one user is connected to a LiveKit room. A 1-to-1 call of 10 minutes = 20 participant minutes (2 users x 10 min).

5,000 free minutes = approximately 250 ten-minute 1-to-1 calls per month.

For a small user base (which QRChat currently is), this is sufficient for development and early users. Production at scale would require the Ship plan ($50/mo) or self-hosting.

### Q8: Known conflicts with react-native-callkeep?

**Answer: No known conflicts. Recommended combination.** Confidence: MEDIUM

LiveKit's own documentation recommends using `react-native-callkeep` alongside the LiveKit SDK. QRChat already uses `react-native-callkeep` v4.3.16. There are no reported incompatibilities.

The only caveat is that both `react-native-callkeep` and `@livekit/react-native-webrtc` are from the same `react-native-webrtc` GitHub organization, so they share compatible native WebRTC assumptions. Since `@livekit/react-native-webrtc` is a fork of `react-native-webrtc`, the native bridge that `react-native-callkeep` uses (`RNCallKeep`) is not affected -- it talks to `CallKit.framework` directly, not to the WebRTC framework.

---

## QRChat Current Architecture

### Call Flow (P2P, current)
```
Caller Phone ──────────────────────> Server ──────────────────────> Callee Phone
   |  1. Create SDP offer                 2. Store in activeCalls        |
   |  3. Send via WebSocket                  Send VoIP push             |
   |                                                                     |
   |  <──── 5. SDP answer via WebSocket ────                            |
   |  <──── 6. ICE candidates ──────────────>                           |
   |                                                                     |
   └──────── 7. Direct P2P media ──────────────────────────────────────┘
             (STUN/TURN for NAT traversal)
```

### Call Flow (LiveKit SFU, proposed)
```
Caller Phone ──────> LiveKit SFU Server <────── Callee Phone
   |  1. Connect to room                         |
   |  2. Publish audio track ─>  <── Subscribe   |
   |  3. Subscribe ──────────>  ─> Publish       |
   |                                              |
   ALL media flows through SFU (no direct P2P)
```

### Files Currently Used for Calls

| File | Role | Lines |
|------|------|-------|
| `WebRTCManager.ts` | P2P connection management, SDP exchange, ICE handling | ~500 (call-related) |
| `CallScreen.tsx` | Call UI, media stream management, call timer | ~500 |
| `CallKitService.ts` | CallKit bridge via react-native-callkeep | ~200 |
| `ColdStartCoordinator.ts` | Cold start SDP retrieval (3 paths) | ~420 |
| `AppDelegate.swift` | PushKit, CallKit native setup, RTCAudioSession | ~320 |
| `index.js` | Early CallKeep event capture for cold start | ~115 |
| `server/index.js` | Call signaling, activeCalls tracking, VoIP push | ~200 (call-related) |
| `SignalingClient.ts` | WebSocket client, call event handlers | ~100 (call-related) |

---

## LiveKit Integration Plan

### What LiveKit Replaces

| Current Component | Replaced by LiveKit? | Detail |
|-------------------|---------------------|--------|
| SDP offer/answer exchange | YES | LiveKit handles signaling internally |
| ICE candidate exchange | YES | LiveKit manages ICE/TURN internally |
| TURN server provisioning | YES | LiveKit Cloud includes TURN |
| RTCPeerConnection for calls | YES | LiveKit Room + Track API |
| mediaDevices.getUserMedia | PARTIALLY | LiveKit can manage tracks, but you can also pass your own |
| RTCView (video rendering) | YES | LiveKit's `VideoTrack` component |
| P2P data channel (messaging) | NO | Must keep or replace separately |
| CallKit / CallKitService | NO | Remains manual |
| PushKit / VoIP push | NO | Remains manual |
| ColdStartCoordinator | SIMPLIFIED | No SDP in push, but still need cold start coordination |
| AVAudioSession management | PARTIALLY | useIOSAudioManagement helps, but CallKit integration is manual |

### What Remains Manual

1. **CallKit integration** -- `react-native-callkeep`, `CallKitService.ts`, `AppDelegate.swift` CallKit code
2. **PushKit/VoIP push** -- `AppDelegate.swift` PKPushRegistry, `server/push.js`
3. **Cold start coordination** -- `ColdStartCoordinator.ts` (simplified but not eliminated)
4. **Call UI** -- `CallScreen.tsx` (layout, buttons, timer)
5. **Call state management** -- Server-side `activeCalls` tracking
6. **End-to-end encryption** -- LiveKit has E2EE support via `RNE2EEManager` but needs separate integration

---

## npm Dependencies

### Add
```json
{
  "@livekit/react-native": "^2.10.0",
  "@livekit/react-native-webrtc": "^144.0.0",
  "livekit-client": "^2.18.0",
  "livekit-server-sdk": "^2.15.0"  // server-side only
}
```

### Remove
```json
{
  "react-native-webrtc": "^124.0.7"  // REPLACED by @livekit/react-native-webrtc
}
```

### Keep (unchanged)
```json
{
  "react-native-callkeep": "^4.3.16",       // CallKit -- no conflict
  "react-native-voip-push-notification": "^3.3.3",  // PushKit -- no conflict
  "react-native-incall-manager": "^4.2.1"   // Proximity sensor, speaker toggle
}
```

### Version Compatibility (verified 2026-03-30)

| Package | Latest Version | Peer Dependencies | Compatible with RN 0.84? |
|---------|---------------|-------------------|--------------------------|
| @livekit/react-native | 2.10.0 (published today) | react-native: * | YES |
| @livekit/react-native-webrtc | 144.0.0 | react-native: >=0.60.0 | YES |
| livekit-client | 2.18.0 | N/A (pure JS) | YES |
| livekit-server-sdk | 2.15.0 | Node.js | YES |

---

## Native iOS Changes

### Podfile
```ruby
# Remove:
# pod 'react-native-webrtc', :path => '../node_modules/react-native-webrtc'

# Add (auto-linked by RN 0.84, but verify):
# @livekit/react-native-webrtc should auto-link
# @livekit/react-native should auto-link

# After changes:
# cd ios && pod install
```

### AppDelegate.swift

**Changes required:**
1. Import LiveKit native module:
```swift
// Add at top:
import LivekitReactNative  // or the equivalent ObjC header
```

2. Call LiveKit setup before React Native initialization:
```swift
// In didFinishLaunchingWithOptions, BEFORE factory.startReactNative:
LivekitReactNative.setup()
```

3. The existing RTCAudioSession setup (`useManualAudio = true`, `isAudioEnabled = false`) may conflict with LiveKit's audio management. This needs testing. LiveKit's `useIOSAudioManagement` hook manages AVAudioSession dynamically, but the manual setup in AppDelegate may override it.

4. The PushKit delegate (`didReceiveIncomingPushWith`), CallKit handling, and `RNCallKeep` calls remain unchanged.

### Info.plist
No changes needed -- `UIBackgroundModes` already includes `audio` and `voip`.

---

## Files Modified Estimate

### Direct Modifications (HIGH confidence)

| File | Change Type | Scope |
|------|-------------|-------|
| `package.json` | Dependency swap | Small |
| `WebRTCManager.ts` | Major rewrite of call methods (`startCall`, `answerCall`, `endCall`) to use LiveKit Room API. Data channel methods stay but use `@livekit/react-native-webrtc` imports | Large (~300 lines) |
| `CallScreen.tsx` | Replace `RTCView` with LiveKit `VideoTrack`, replace stream management with LiveKit track subscriptions | Large (~200 lines) |
| `ColdStartCoordinator.ts` | Simplify -- remove SDP passing, add token fetching | Medium (~100 lines) |
| `AppDelegate.swift` | Add LiveKit native setup call, potentially adjust RTCAudioSession handling | Small (~10 lines) |
| `index.js` | Potentially add `registerGlobals()` call, adjust RTCAudioSession references | Small (~5 lines) |
| `server/index.js` | Add token generation endpoint, simplify call signaling (no SDP relay needed) | Medium (~50 lines) |
| `server/push.js` | Simplify VoIP push payload (room name instead of SDP) | Small (~10 lines) |
| `SignalingClient.ts` | Simplify call-related message types | Medium (~30 lines) |
| `Podfile` | Pod install after dependency swap | Small |

### Possibly Modified

| File | Reason |
|------|--------|
| `CallKitService.ts` | May need minor adjustments for LiveKit room lifecycle vs call lifecycle |
| `NotificationService.ts` | No change expected |
| `constants.ts` | ICE server config may become unnecessary for calls |

### Total: ~12-15 files modified

---

## Risks and Mitigations

### RISK 1: P2P Data Channel Breakage (CRITICAL)

**Risk:** QRChat uses `react-native-webrtc` for P2P data channels (chat messaging). Replacing with `@livekit/react-native-webrtc` means the raw WebRTC API must still be available from the fork.

**Likelihood:** LOW (it's a fork, APIs are preserved)

**Mitigation:** Before starting migration:
1. Verify that `@livekit/react-native-webrtc` exports `RTCPeerConnection`, `RTCSessionDescription`, `RTCIceCandidate`, `mediaDevices`, `RTCView`
2. Test P2P data channel creation with the fork
3. If APIs are missing, use LiveKit's data channel API (`room.localParticipant.publishData()`) as fallback for messaging -- but this routes through SFU, not P2P

### RISK 2: Audio Quality Regression on Cold Start (HIGH)

**Risk:** QRChat's cold start audio flow is highly optimized (PATH A reads SDP from UserDefaults, avoiding server round-trip). LiveKit requires a server round-trip to get a token and then connecting to the SFU adds latency.

**Likelihood:** MEDIUM

**Mitigation:**
- Pre-generate LiveKit tokens during VoIP push processing on the server and include the token in the push payload
- Cache tokens with short TTL
- Measure cold-start-to-audio time before and after migration

### RISK 3: Increased Latency for 1-to-1 Calls (MEDIUM)

**Risk:** Current P2P calls have minimal latency (direct connection). LiveKit SFU adds a hop: Phone A -> SFU -> Phone B.

**Likelihood:** HIGH (this is architectural, not a bug)

**Mitigation:**
- LiveKit Cloud has global edge servers, so the additional hop is typically <50ms
- For 1-to-1 calls this is usually imperceptible
- Trade-off: reliability improves (no NAT traversal issues, no TURN dependency)

### RISK 4: react-native-webrtc v124 -> v144 Breaking Changes (MEDIUM)

**Risk:** QRChat currently uses `react-native-webrtc@124.0.7`. LiveKit's fork is based on a newer WebRTC version (144). Internal API changes could break existing data channel code.

**Likelihood:** LOW-MEDIUM

**Mitigation:**
- Review `react-native-webrtc` changelog from v124 to v144
- Focus on `RTCPeerConnection`, `DataChannel`, and `RTCAudioSession` API changes
- Run existing tests after swap

### RISK 5: Server Infrastructure Dependency (MEDIUM)

**Risk:** QRChat currently needs only a Node.js WebSocket server (Railway). LiveKit requires either LiveKit Cloud (external dependency) or a self-hosted SFU (additional infrastructure).

**Likelihood:** HIGH (architectural requirement)

**Mitigation:**
- Start with LiveKit Cloud free tier (5,000 min/month)
- The Node.js server remains for messaging, push, auth
- LiveKit Cloud SLA is production-grade
- Can self-host later if needed

### RISK 6: E2E Encryption Complexity (MEDIUM)

**Risk:** QRChat uses TweetNaCl for E2E encryption on P2P data channels. LiveKit has its own E2EE (`RNE2EEManager`, `RNKeyProvider`) but it's a different system. Calls routed through SFU are visible to the SFU unless E2EE is enabled.

**Likelihood:** HIGH (SFU sees media by default)

**Mitigation:**
- Enable LiveKit's built-in E2EE for calls using `RNE2EEManager`
- Keep TweetNaCl for messaging (separate transport)
- LiveKit E2EE uses WebCrypto under the hood, compatible with modern standards

---

## Decision Matrix: LiveKit Cloud vs Self-Hosted

| Factor | LiveKit Cloud | Self-Hosted |
|--------|--------------|-------------|
| Setup time | Minutes | Hours-days |
| Monthly cost (small scale) | $0 (free tier) | ~$20-40/mo (VPS) |
| Monthly cost (medium scale) | $50/mo (Ship plan) | ~$40-80/mo (VPS) |
| TURN servers | Included | Must configure separately |
| Global distribution | Yes (edge servers) | Manual (multiple regions) |
| Maintenance | Zero | You manage updates, monitoring |
| Data sovereignty | US/EU (configurable) | Full control |
| Reliability | 99.9%+ SLA | Depends on your ops |
| Media inspection risk | LiveKit sees encrypted media headers | You control the SFU |

**Recommendation:** Start with LiveKit Cloud for development and early production. Evaluate self-hosting only if:
- You need strict data sovereignty (all media in Moldova/EU)
- Monthly costs exceed $50-100
- You need to avoid any external dependency for media

---

## Summary: Should QRChat Integrate LiveKit?

### Arguments FOR LiveKit

1. **Eliminates TURN server management** -- Currently QRChat depends on Metered.ca TURN servers ($). LiveKit Cloud includes TURN.
2. **Eliminates SDP signaling complexity** -- No more 3-path SDP retrieval, no SDP in VoIP push payloads.
3. **Better reliability behind NAT** -- SFU bypasses NAT entirely (both phones connect outbound to SFU).
4. **Scalability** -- If QRChat ever needs group calls, LiveKit handles it natively.
5. **Professional call quality** -- LiveKit handles bitrate adaptation, codec selection, packet loss recovery.

### Arguments AGAINST LiveKit

1. **react-native-webrtc cannot coexist** -- Must swap globally, risking P2P data channel breakage.
2. **New infrastructure dependency** -- LiveKit Cloud or self-hosted SFU required.
3. **Added latency** -- SFU hop vs direct P2P (typically <50ms additional).
4. **SFU sees media** -- Unless E2EE is enabled, call audio/video passes through LiveKit servers unencrypted.
5. **Cold start regression risk** -- Current PATH A (SDP from VoIP push) is faster than token-fetch + SFU-connect.
6. **Cost at scale** -- Current P2P calls are free after TURN costs. LiveKit charges per participant minute.
7. **No P2P mode** -- LiveKit does not support direct P2P, even for 1-to-1 calls. Feature request exists but is not planned.

### Final Assessment

LiveKit is a **net improvement for call reliability** but comes with **significant integration risk** due to the `react-native-webrtc` conflict. The migration is non-trivial (~15 files, weeks of work) and carries regression risk for the already-working P2P messaging system.

**Recommended approach if proceeding:**
1. Create a feature branch
2. Swap `react-native-webrtc` to `@livekit/react-native-webrtc` FIRST
3. Verify ALL P2P data channel functionality still works (messaging, file transfer)
4. Only THEN proceed with LiveKit Room integration for calls
5. Keep existing CallKit/PushKit/ColdStart infrastructure
6. Use LiveKit Cloud free tier for development

---

## Sources

### Primary (HIGH confidence)
- [LiveKit React Native SDK GitHub](https://github.com/livekit/client-sdk-react-native) -- README, package.json, issues
- [LiveKit React Native Docs](https://docs.livekit.io/transport/sdk-platforms/react-native/) -- Official quickstart
- [LiveKit Pricing](https://livekit.com/pricing) -- Free tier details
- [GitHub Issue #2809](https://github.com/livekit/livekit/issues/2809) -- Confirmed webrtc.xcframework conflict
- [npm registry](https://www.npmjs.com/package/@livekit/react-native-webrtc) -- Version 144.0.0, peer dependencies
- [LiveKit Token Generation Docs](https://docs.livekit.io/frontends/authentication/tokens/endpoint/) -- Server-side token endpoint
- [LiveKit Self-Hosting Docs](https://docs.livekit.io/transport/self-hosting/) -- SFU requirements
- [LiveKit SFU Architecture](https://docs.livekit.io/reference/internals/livekit-sfu/) -- No P2P mode

### Secondary (MEDIUM confidence)
- [LiveKit Blog: React Native Beta](https://blog.livekit.io/react-native-beta-launch/) -- Historical context
- [LiveKit Blog: Pricing Model](https://blog.livekit.io/the-end-of-participant-minute/) -- Pricing changes
- [LiveKit Data Channel API](https://docs.livekit.io/transport/data/) -- Alternative messaging transport

### QRChat Source Files (READ-ONLY)
- `/Users/ruslanconstantinovici/QRChat/src/network/WebRTCManager.ts`
- `/Users/ruslanconstantinovici/QRChat/src/screens/CallScreen.tsx`
- `/Users/ruslanconstantinovici/QRChat/src/services/ColdStartCoordinator.ts`
- `/Users/ruslanconstantinovici/QRChat/server/index.js`
- `/Users/ruslanconstantinovici/QRChat/ios/QRChat/AppDelegate.swift`
- `/Users/ruslanconstantinovici/QRChat/App.tsx`
- `/Users/ruslanconstantinovici/QRChat/index.js`
- `/Users/ruslanconstantinovici/QRChat/package.json`
