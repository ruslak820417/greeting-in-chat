# VoIP Push Notifications for QRChat -- Research & Implementation Plan

**Researched:** 2026-03-23
**Author:** prompt-architect agent
**Confidence:** HIGH (based on current codebase analysis + web research)
**Target:** QRChat v4.3.0, React Native 0.84, iOS only (Android uses FCM, already partially implemented)

---

## Executive Summary

QRChat currently sends **regular APNs alert pushes** for incoming calls (`sendiOSCallPush` in `server/push.js`). This approach has a critical flaw: **regular pushes do not reliably wake the app from killed/suspended state to display the native iOS call screen**. The fix is to implement **VoIP Push Notifications via PushKit**, which Apple guarantees will:

1. Wake the app even when killed
2. Deliver with highest priority (no throttling like regular silent pushes)
3. Launch the app process automatically if terminated
4. Allow up to 5KB payload

The codebase already has most of the foundation in place:
- `PKPushRegistry` is registered in `AppDelegate.swift` (lines 34-37)
- `RNCallKeep` (CallKit) is integrated and functional
- `@parse/node-apn` is installed on the server
- VoIP background mode is in `Info.plist`

**What is missing:** The VoIP push delegate methods are empty stubs, there is no VoIP token forwarding to the server, the server sends regular `alert` pushes instead of VoIP pushes for calls, and there is no `react-native-voip-push-notification` library.

---

## A. Exactly What Changes Are Needed

### A1. New Dependency: `react-native-voip-push-notification`

```bash
cd /Users/ruslanconstantinovici/QRChat
npm install --save react-native-voip-push-notification
cd ios && pod install && cd ..
```

This library provides:
- Native PushKit registration (`RNVoipPushNotificationManager`)
- JS event bridge for VoIP push token and incoming push events
- Completion handler management for iOS 13+ compliance
- `didLoadWithEvents` for events fired before JS bridge is ready

### A2. iOS Native Changes -- `AppDelegate.swift`

**File:** `/Users/ruslanconstantinovici/QRChat/ios/QRChat/AppDelegate.swift`

The current `AppDelegate.swift` has PKPushRegistry registered but the delegate methods are **empty stubs**. The critical change is:

#### Current (broken -- lines 100-108):
```swift
// MARK: - PKPushRegistryDelegate
func pushRegistry(_ registry: PKPushRegistry, didUpdate pushCredentials: PKPushCredentials, for type: PKPushType) {
    // Token VoIP push -- nu e necesar server push acum, dar CallKit il cere
}

func pushRegistry(_ registry: PKPushRegistry, didReceiveIncomingPushWith payload: PKPushPayload, for type: PKPushType, completion: @escaping () -> Void) {
    // VoIP push primit -- CallKit va gestiona
    completion()
}
```

#### Required (working implementation):

```swift
// MARK: - PKPushRegistryDelegate
func pushRegistry(_ registry: PKPushRegistry, didUpdate pushCredentials: PKPushCredentials, for type: PKPushType) {
    // Forward VoIP token to react-native-voip-push-notification
    RNVoipPushNotificationManager.didUpdate(pushCredentials, forType: type.rawValue)

    // Also save VoIP token to UserDefaults for JS to read
    let voipToken = pushCredentials.token.map { String(format: "%02.2hhx", $0) }.joined()
    UserDefaults.standard.set(voipToken, forKey: "VoIPPushToken")
    UserDefaults.standard.synchronize()
    print("[PushKit] VoIP token: \(voipToken.prefix(16))...")
}

func pushRegistry(_ registry: PKPushRegistry, didReceiveIncomingPushWith payload: PKPushPayload, for type: PKPushType, completion: @escaping () -> Void) {
    // CRITICAL: Must report to CallKit IMMEDIATELY or iOS will kill the app
    let payloadDict = payload.dictionaryPayload
    let uuid = payloadDict["uuid"] as? String ?? UUID().uuidString
    let callerName = payloadDict["callerName"] as? String ?? "Unknown"
    let handle = payloadDict["handle"] as? String ?? callerName
    let hasVideo = payloadDict["hasVideo"] as? Bool ?? false

    // 1. Cache completion handler
    RNVoipPushNotificationManager.addCompletionHandler(uuid, completionHandler: completion)

    // 2. Forward to JS bridge
    RNVoipPushNotificationManager.didReceiveIncomingPush(with: payload, forType: type.rawValue)

    // 3. Report to CallKit IMMEDIATELY (before JS bridge is ready)
    RNCallKeep.reportNewIncomingCall(
        uuid,
        handle: handle,
        handleType: "generic",
        hasVideo: hasVideo,
        localizedCallerName: callerName,
        supportsHolding: false,
        supportsDTMF: false,
        supportsGrouping: false,
        supportsUngrouping: false,
        fromPushKit: true,
        payload: payloadDict as? [String: Any],
        withCompletionHandler: nil
    )
}
```

#### Bridging Header addition:

**File:** `/Users/ruslanconstantinovici/QRChat/ios/QRChat/QRChat-Bridging-Header.h`

Current content:
```objc
#import "RNCallKeep.h"
```

Add:
```objc
#import "RNCallKeep.h"
#import <RNVoipPushNotification/RNVoipPushNotificationManager.h>
```

#### Additional AppDelegate change -- remove manual PKPushRegistry setup:

The current `didFinishLaunchingWithOptions` manually creates a `PKPushRegistry` (lines 34-37). With `react-native-voip-push-notification`, registration is handled by the library. Change:

```swift
// OLD (remove):
let voipRegistry = PKPushRegistry(queue: DispatchQueue.main)
voipRegistry.delegate = self
voipRegistry.desiredPushTypes = [.voIP]

// NEW (replace with):
RNVoipPushNotificationManager.voipRegistration()
```

**IMPORTANT:** The `voipRegistry` must be retained. The old code creates it as a local variable which gets deallocated. `RNVoipPushNotificationManager.voipRegistration()` handles this correctly internally.

### A3. Server Changes -- VoIP Push Sending

**File:** `/Users/ruslanconstantinovici/QRChat/server/push.js`

The server currently sends regular `alert` pushes for calls via `sendiOSCallPush()`. A new function is needed for VoIP pushes:

#### New function: `sendVoIPPush()`

```javascript
/**
 * Send a VoIP push notification for incoming calls on iOS.
 * Uses PushKit topic (.voip suffix) and pushType 'voip'.
 *
 * CRITICAL: The iOS app MUST report to CallKit upon receiving this push,
 * or Apple will terminate the app and block future VoIP pushes.
 *
 * @param {string} userId - Recipient's userId
 * @param {string} senderUserId - Caller's userId
 * @param {object} callData - { callerName, isVideo, uuid }
 */
async function sendVoIPPush(userId, senderUserId, callData) {
  if (!apnsConfigured || !provider) return;

  const mailboxId = userMailboxes.get(userId);
  if (!mailboxId) return;

  const tokenEntry = pushTokens.get(mailboxId);
  if (!tokenEntry || !tokenEntry.voipToken) return;

  const uuid = callData.uuid || generateUUID();

  const note = new apn.Notification();
  note.topic = BUNDLE_ID + '.voip';        // MUST have .voip suffix
  note.pushType = 'voip';                  // MUST be 'voip'
  note.priority = 10;                      // Immediate delivery (required for voip)
  note.expiry = Math.floor(Date.now() / 1000) + 60; // 60s TTL
  note.payload = {
    uuid: uuid,
    callerName: callData.callerName || 'Unknown',
    handle: senderUserId,
    hasVideo: callData.isVideo || false,
    from: senderUserId,
  };
  // No aps.alert, no aps.sound -- VoIP pushes use CallKit for UI/sound

  try {
    const result = await provider.send(note, tokenEntry.voipToken);
    if (result.failed && result.failed.length > 0) {
      for (const failure of result.failed) {
        const reason = failure.response?.reason;
        if (reason === 'BadDeviceToken' || reason === 'Unregistered') {
          // Remove invalid VoIP token
          tokenEntry.voipToken = null;
          pushDirty = true;
          console.log(`[Push] Removed invalid VoIP token for mailbox ${mailboxId.substring(0, 8)}...`);
        } else {
          console.warn(`[Push] VoIP push failed: ${reason}`);
        }
      }
    } else {
      console.log(`[Push] VoIP push sent to ${mailboxId.substring(0, 8)}... (${callData.callerName})`);
    }
  } catch (err) {
    console.error('[Push] VoIP push error:', err.message);
  }
}
```

#### Key differences from current `sendiOSCallPush()`:

| Property | Current (alert push) | New (VoIP push) |
|----------|---------------------|-----------------|
| `note.topic` | `com.ruslan.qrchat` | `com.ruslan.qrchat.voip` |
| `note.pushType` | `'alert'` | `'voip'` |
| `note.sound` | `'default'` | None (CallKit handles) |
| `note.alert` | `{ title, body }` | None (CallKit handles) |
| Token used | APNs device token | VoIP push token (separate!) |
| Throttled by Apple | Yes | No |
| Wakes killed app | Unreliable | Guaranteed |

#### Storage change -- separate VoIP token:

The `pushTokens` Map entry must store BOTH tokens:

```javascript
// Current structure:
// mailboxId -> { platform, token, registeredAt }

// New structure:
// mailboxId -> { platform, token, voipToken, registeredAt }
```

The `registerPushToken` function needs updating:

```javascript
function registerPushToken(userId, mailboxId, platform, token, voipToken) {
  userMailboxes.set(userId, mailboxId);
  const existing = pushTokens.get(mailboxId) || {};
  pushTokens.set(mailboxId, {
    platform,
    token: token || existing.token,
    voipToken: voipToken || existing.voipToken,  // NEW
    registeredAt: Date.now(),
  });
  pushDirty = true;
  console.log(`[Push] Registered token for mailbox ${mailboxId.substring(0, 8)}... (${platform}, voip: ${!!voipToken})`);
}
```

#### Update `sendPush()` routing:

```javascript
async function sendPush(userId, senderUserId, callData) {
  const mailboxId = userMailboxes.get(userId);
  if (!mailboxId) return;
  const tokenEntry = pushTokens.get(mailboxId);
  if (!tokenEntry) return;

  if (tokenEntry.platform === 'android' && callData) {
    await sendAndroidPush(userId, { /* ... existing ... */ });
  } else if (tokenEntry.platform === 'android') {
    await sendAndroidPush(userId, { type: 'new-message', from: senderUserId });
  } else if (callData && tokenEntry.voipToken) {
    // iOS call with VoIP token -- use VoIP push (preferred)
    await sendVoIPPush(userId, senderUserId, callData);
  } else if (callData) {
    // iOS call without VoIP token -- fallback to regular alert push
    await sendiOSCallPush(userId, senderUserId, callData);
  } else {
    // iOS message -- regular alert push
    await sendSilentPush(userId, senderUserId);
  }
}
```

**File:** `/Users/ruslanconstantinovici/QRChat/server/index.js`

The `register-push-token` handler (search for this in index.js) needs to accept the optional `voipToken` field:

```javascript
case 'register-push-token': {
  if (message.mailboxId && message.platform && message.token) {
    registerPushToken(
      userId,
      message.mailboxId,
      message.platform,
      message.token,
      message.voipToken  // NEW -- optional VoIP push token
    );
  }
  break;
}
```

### A4. React Native JS Changes

**File:** `/Users/ruslanconstantinovici/QRChat/src/services/PushTokenService.ts` (exists already)

Add VoIP token registration:

```typescript
import VoipPushNotification from 'react-native-voip-push-notification';
import { Platform } from 'react-native';

class PushTokenService {
  private voipToken: string | null = null;

  async initialize() {
    if (Platform.OS !== 'ios') return;

    // Listen for VoIP push token
    VoipPushNotification.addEventListener('register', (token: string) => {
      console.log('[PushToken] VoIP token received:', token.substring(0, 16) + '...');
      this.voipToken = token;
      this.registerTokensWithServer();
    });

    // Listen for incoming VoIP push (JS side handler)
    VoipPushNotification.addEventListener('notification', (notification: any) => {
      // CallKit already displayed via AppDelegate native code
      // Signal completion to iOS
      if (notification.uuid) {
        VoipPushNotification.onVoipNotificationCompleted(notification.uuid);
      }
    });

    // Handle events that fired before JS bridge was ready
    VoipPushNotification.addEventListener('didLoadWithEvents', (events: any[]) => {
      if (!events || !Array.isArray(events) || events.length < 1) return;
      for (const event of events) {
        if (event.name === VoipPushNotification.RNVoipPushRemoteNotificationsRegisteredEvent) {
          this.voipToken = event.data;
          this.registerTokensWithServer();
        }
      }
    });

    // Trigger VoIP push registration
    VoipPushNotification.registerVoipToken();
  }

  async registerTokensWithServer() {
    // Send both APNs token and VoIP token to server
    const mailboxId = await this.getOrCreateMailboxId();
    const apnsToken = /* read from UserDefaults via APNsTokenModule */;

    SignalingClient.send({
      type: 'register-push-token',
      mailboxId,
      platform: 'ios',
      token: apnsToken,      // Regular APNs token (for message pushes)
      voipToken: this.voipToken,  // VoIP token (for call pushes)
    });
  }
  // ... existing methods ...
}
```

**File:** `/Users/ruslanconstantinovici/QRChat/src/services/CallKitService.ts`

No changes needed in CallKitService itself. The native AppDelegate handles the CallKit reporting directly in the `didReceiveIncomingPush` delegate. The existing `onAnswerCall` and `onEndCall` event handlers in CallKitService will work as-is because they listen for RNCallKeep events regardless of how the call was reported.

### A5. Xcode Project Changes

1. **VoIP Push Notifications entitlement** -- already present (VoIP background mode in Info.plist)
2. **Push Notifications capability** -- already present (aps-environment in entitlements)
3. **Background Modes > Voice over IP** -- already enabled in Info.plist (line 67: `<string>voip</string>`)

No additional Xcode configuration needed. The existing setup is correct.

---

## B. Agent Assignments

| Task | Agent | Why This Agent |
|------|-------|----------------|
| B1. Install `react-native-voip-push-notification`, run `pod install` | **release-engineer** | Dependency management, Podfile, build system |
| B2. Modify `AppDelegate.swift` (VoIP push delegates, bridging header) | **network-engineer** | Owns CallKit integration, PushKit is call-related networking |
| B3. Modify `server/push.js` (add `sendVoIPPush`, update token storage) | **backend-engineer** | Owns server code, push infrastructure |
| B4. Modify `server/index.js` (accept `voipToken` in register-push-token) | **backend-engineer** | Owns server routing |
| B5. Modify `PushTokenService.ts` (VoIP token registration JS side) | **network-engineer** | Push token is part of signaling/call infrastructure |
| B6. Security review of VoIP push payload | **security-engineer** | Verify zero-content policy, token storage privacy |
| B7. Test on physical device (VoIP push delivery, CallKit display) | **qa-engineer** | Manual testing, two-device verification |
| B8. Deploy server to Railway | **backend-engineer** | Server deployment |

---

## C. Implementation Order

```
Phase 1 (parallel, no dependencies):
  [backend-engineer] B3 + B4: Server-side VoIP push support
  [release-engineer] B1: Install react-native-voip-push-notification + pod install

Phase 2 (depends on Phase 1):
  [network-engineer] B2: AppDelegate.swift VoIP push delegates
  [network-engineer] B5: PushTokenService.ts VoIP token registration

Phase 3 (depends on Phase 2):
  [security-engineer] B6: Security review of VoIP payload + token storage
  [qa-engineer] B7: Physical device testing (requires 2 iPhones)

Phase 4 (depends on all above passing):
  [backend-engineer] B8: Deploy server to Railway with updated push.js
```

**Critical path:** B1 -> B2 -> B7

**Estimated total time:** 1-2 sessions (assuming no blockers)

---

## D. Risks and Gotchas

### D1. CRITICAL -- CallKit Must Be Reported Immediately (Apple Termination Risk)

**Risk:** If `pushRegistry:didReceiveIncomingPushWithPayload` does NOT call `reportNewIncomingCall` synchronously, iOS will:
1. Terminate the app process
2. After repeated failures, permanently stop delivering VoIP pushes to the device

**Mitigation:** The AppDelegate native code calls `RNCallKeep.reportNewIncomingCall()` **directly in the delegate method**, before any async JS bridge communication. This is why it must happen in Swift, not in JavaScript.

### D2. CRITICAL -- Two Separate Tokens (VoIP token != APNs token)

**Risk:** Sending a VoIP push to the regular APNs device token will fail silently. The server must store and use the **VoIP push token** (from `pushRegistry:didUpdatePushCredentials`) separately from the regular APNs token (from `application:didRegisterForRemoteNotificationsWithDeviceToken`).

**Mitigation:** The `pushTokens` Map stores both `token` (APNs) and `voipToken` (PushKit) per mailbox. The routing logic in `sendPush()` uses `voipToken` for calls and `token` for messages.

### D3. HIGH -- react-native-voip-push-notification + React Native 0.84 New Architecture

**Risk:** The library uses the old Native Modules bridge pattern, not TurboModules. It may have compatibility issues with RN 0.84's New Architecture (enabled: `RCTNewArchEnabled: true` in Info.plist).

**Mitigation:**
- RN 0.84 has backwards compatibility for old-style Native Modules via the interop layer
- The library's core value is in its Objective-C native code (`RNVoipPushNotificationManager`), which runs before the JS bridge and is not affected by New Architecture
- If JS bridge events fail, the critical CallKit reporting still works (it happens in native Swift)
- **Fallback:** If the library is incompatible, the VoIP token can be read from `UserDefaults` (where AppDelegate already saves it) via the existing `APNsTokenModule` native module, and sent to the server manually. The JS event bridge is nice-to-have but not strictly required.

### D4. MEDIUM -- VoIP Push Only for Calls (Apple Policy)

**Risk:** Apple explicitly states VoIP pushes must ONLY be used for reporting incoming calls. Using VoIP push for messages or other purposes will result in App Store rejection.

**Mitigation:** The architecture correctly separates:
- VoIP push (PushKit) -> only for incoming calls -> triggers CallKit
- Regular alert push (APNs) -> for messages -> triggers notification banner

The server's `sendPush()` routing enforces this: VoIP push is only sent when `callData` is present.

### D5. MEDIUM -- Cancelled/Missed Calls

**Risk:** If the caller hangs up before the callee answers, the CallKit UI is still showing. The callee sees a "ghost call."

**Mitigation:** When the caller cancels, the server should send a **regular APNs push** (not VoIP!) with a `cancel` flag, and the app should call `RNCallKeep.endCall(uuid)`. Do NOT send a VoIP push to cancel a call -- that would trigger another CallKit `reportNewIncomingCall` requirement.

### D6. LOW -- Simulator Testing

**Risk:** PushKit VoIP pushes cannot be tested on the iOS Simulator. They require a physical device.

**Mitigation:** QRChat already has a physical iPhone 16 Pro available for testing (UDID: 00008140-00066CA02229801C). Testing requires two physical devices (caller + callee) or one device + the server sending a test VoIP push.

### D7. LOW -- Same .p8 Key Works for Both

**Risk:** Developers sometimes think VoIP push requires a separate APNs certificate.

**Mitigation:** Token-based auth (.p8 key) works for both regular and VoIP pushes. The only difference is the `topic` header: `com.ruslan.qrchat` vs `com.ruslan.qrchat.voip`. The existing `.p8` key configuration on Railway works for both.

---

## E. Estimated Complexity

| Task | Complexity | Lines Changed | Time Estimate |
|------|-----------|---------------|---------------|
| B1. Install dependency + pod install | **Simple** | ~5 (Podfile, package.json) | 10 minutes |
| B2. AppDelegate.swift VoIP delegates | **Medium** | ~40 (AppDelegate + bridging header) | 30 minutes |
| B3. Server push.js VoIP function | **Medium** | ~80 (new function + storage update) | 45 minutes |
| B4. Server index.js voipToken field | **Simple** | ~3 | 5 minutes |
| B5. PushTokenService.ts VoIP token | **Medium** | ~50 | 30 minutes |
| B6. Security review | **Simple** | 0 (review only) | 15 minutes |
| B7. Physical device testing | **Medium** | 0 (manual testing) | 1 hour |
| B8. Server deploy to Railway | **Simple** | 0 | 10 minutes |
| **TOTAL** | **Medium** | ~180 lines | **~3 hours** |

---

## F. Key File Paths Reference

| File | What Changes |
|------|-------------|
| `/Users/ruslanconstantinovici/QRChat/package.json` | Add `react-native-voip-push-notification` dependency |
| `/Users/ruslanconstantinovici/QRChat/ios/Podfile` | Runs `pod install` (auto-linked) |
| `/Users/ruslanconstantinovici/QRChat/ios/QRChat/AppDelegate.swift` | VoIP push delegate methods (lines 100-108) |
| `/Users/ruslanconstantinovici/QRChat/ios/QRChat/QRChat-Bridging-Header.h` | Add RNVoipPushNotificationManager import |
| `/Users/ruslanconstantinovici/QRChat/server/push.js` | Add `sendVoIPPush()`, update `registerPushToken()`, update `sendPush()` |
| `/Users/ruslanconstantinovici/QRChat/server/index.js` | Accept `voipToken` in `register-push-token` handler |
| `/Users/ruslanconstantinovici/QRChat/src/services/PushTokenService.ts` | Add VoIP token registration via JS bridge |
| `/Users/ruslanconstantinovici/QRChat/ios/QRChat/QRChat.entitlements` | No change needed (aps-environment already present) |
| `/Users/ruslanconstantinovici/QRChat/ios/QRChat/Info.plist` | No change needed (voip background mode already present) |

---

## G. Sources

- [react-native-voip-push-notification (GitHub)](https://github.com/react-native-webrtc/react-native-voip-push-notification) -- primary library
- [react-native-voip-push-notification (npm)](https://www.npmjs.com/package/react-native-voip-push-notification) -- package info
- [react-native-callkeep (GitHub)](https://github.com/react-native-webrtc/react-native-callkeep) -- CallKit integration
- [react-native-callkeep (npm)](https://www.npmjs.com/package/react-native-callkeep) -- package info
- [Apple: Responding to VoIP Notifications from PushKit](https://developer.apple.com/documentation/pushkit/responding-to-voip-notifications-from-pushkit) -- official Apple docs
- [Apple: PushKit VoIP type](https://developer.apple.com/documentation/PushKit/PKPushType/voIP) -- Apple requirements
- [Apple: Establishing token-based connection to APNs](https://developer.apple.com/documentation/usernotifications/establishing-a-token-based-connection-to-apns) -- .p8 key auth
- [@parse/node-apn (npm)](https://www.npmjs.com/package/@parse/node-apn) -- server APNs library
- [node-apn VoIP push support (Issue #618)](https://github.com/node-apn/node-apn/issues/618) -- topic/pushType details
- [Troubleshooting VoIP Push on iOS (ConnectyCube)](https://connectycube.com/2025/11/06/troubleshooting-common-issues-with-voip-push-notifications-on-ios/) -- common issues
- [APNsPush: How to Send VoIP Push](https://apnspush.com/how-to-send-and-handle-voip-push-notifications) -- server implementation guide
- [VideoSDK: React Native iOS Video Call with CallKeep](https://www.videosdk.live/blog/react-native-ios-video-calling-app-with-callkeep) -- integration tutorial
- [Sendbird: Receive call in background](https://sendbird.com/docs/calls/sdk/v1/react-native/direct-call/receiving-a-call/receive-a-call-in-the-background) -- background wake pattern
- [How to integrate VoIP and CallKit into React Native (Coming.io)](https://coming.io/how-to-integrate-voip-and-callkit/) -- full walkthrough
