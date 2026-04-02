# VoIP Push Security Review

**Reviewer:** Security Engineer
**Date:** 2026-03-23
**Files reviewed:**
- `/Users/ruslanconstantinovici/QRChat/server/push.js` (494 lines)
- `/Users/ruslanconstantinovici/QRChat/server/index.js` (register-voip-token handler)
- `/Users/ruslanconstantinovici/QRChat/ios/QRChat/AppDelegate.swift` (193 lines)
- `/Users/ruslanconstantinovici/QRChat/src/services/CallKitService.ts` (163 lines)
- `/Users/ruslanconstantinovici/QRChat/ios/QRChat/QRChat-Bridging-Header.h`

---

## Check 1: Zero-Content Policy

**Result: PASS (iOS VoIP) / FAIL (Android FCM)**

### iOS VoIP Push Payload (push.js line 364-369)

The `sendVoIPPush()` function sends:

```js
note.payload = {
  type: 'incoming-call',   // event flag -- OK
  from: senderUserId,      // sender ID -- OK (server already knows this)
  callerName: callData.callerName || 'Unknown',  // display metadata -- OK
  isVideo: callData.isVideo || false,             // call type flag -- OK
};
```

This is clean. No encryption keys, no message text, no conversation IDs, no WebRTC offer/SDP.

### Android FCM Call Payload (push.js line 460-466, via sendPush)

```js
await sendAndroidPush(userId, {
  type: 'incoming-call',
  from: senderUserId,
  callerName: callData.callerName || '',
  isVideo: String(callData.isVideo || false),
  offer: callData.offer || '',          // <-- ISSUE
});
```

**ISSUE:** The Android call push includes the full WebRTC SDP offer in the FCM payload. This is a security concern:
- The SDP offer contains ICE candidates, IP addresses, media capabilities, and session descriptions.
- This data transits through Google's FCM infrastructure in plaintext (FCM data messages are not end-to-end encrypted).
- While not "message content" per se, the SDP offer is cryptographically sensitive session establishment data.

**Recommendation:** Remove `offer` from the FCM payload. The Android client should fetch the offer via the WebSocket after being woken by the push, same pattern as iOS. The push should only contain: `type`, `from`, `callerName`, `isVideo`.

### iOS Regular Call Push (sendiOSCallPush, line 293-297)

The fallback path when no VoIP token exists:

```js
note.alert = { title: callerName, body: `Incoming ${callType}` };
note.payload = { e: 1, s: senderUserId, call: true };
```

This is clean -- no SDP offer, no message content.

---

## Check 2: Token Isolation

**Result: PASS (with note)**

### Two-Map Design
- `userMailboxes`: Map of `userId -> mailboxId` (separate map)
- `pushTokens`: Map of `mailboxId -> { platform, token, voipToken, registeredAt }`

The two-map design correctly prevents any single data structure from linking userId directly to push token. This follows Pitfall 1 prevention as documented.

### VoIP Token Storage
The VoIP token is stored alongside the regular APNs token in the same `pushTokens` entry under the `voipToken` field (push.js line 88, 159, 174). Both are keyed by the same anonymous `mailboxId`.

**Note:** The VoIP token is not stored in a separate map -- it shares the same `mailboxId` entry as the APNs token. This is acceptable because:
1. Both tokens belong to the same device/user
2. The mailboxId indirection still prevents direct userId-to-token linking
3. Storing them together avoids orphaned token entries

The `register-voip-token` handler in index.js (line 591-611) correctly requires authentication (or grace period), validates inputs (mailboxId max 256 chars, voipToken max 512 chars), and uses the same anonymous mailboxId pattern.

---

## Check 3: No Server-Side Logging of Sensitive Data

**Result: FAIL**

### Issue Found (push.js line 371)

```js
console.log(`[Push] Sending VoIP push to mailbox ${mailboxId.substring(0, 8)}... (caller: ${callData.callerName || 'Unknown'})`);
```

**ISSUE:** The caller's display name is logged to server stdout. While this is metadata (not message content), in a privacy-focused encrypted messenger, caller names should not appear in server logs. An attacker with access to server logs (or a Railway/hosting provider with log retention) could observe who is calling whom (by correlating truncated mailboxId with caller name patterns).

### Other Logging (acceptable)

All other log statements properly truncate identifiers to first 8 characters:
- `userId.substring(0, 8)` -- OK (public key prefix, not identifiable)
- `mailboxId.substring(0, 8)` -- OK (anonymous, truncated)
- No full tokens logged anywhere

**Recommendation:** Remove the caller name from the log line:

```js
console.log(`[Push] Sending VoIP push to mailbox ${mailboxId.substring(0, 8)}...`);
```

---

## Check 4: CallKit Report in Native Code

**Result: PASS**

### AppDelegate.swift (line 108-136)

The `pushRegistry(_:didReceiveIncomingPushWith:for:completion:)` delegate method handles VoIP push reception and immediately calls:

```swift
RNCallKeep.reportNewIncomingCall(
  callUUID,
  handle: from,
  handleType: "generic",
  hasVideo: isVideo,
  localizedCallerName: callerName,
  ...
  fromPushKit: true,
  payload: payloadDict as [AnyHashable: Any],
  withCompletionHandler: nil
)
```

This happens synchronously in native Swift code (AppDelegate), not in JavaScript. The comment on line 119-120 correctly notes: "MUST report to CallKit synchronously in native code -- Apple kills the app if reportNewIncomingCall is not called before this method returns."

The `RNCallKeep` bridge (`QRChat-Bridging-Header.h` imports `RNCallKeep.h`) calls through to the native CXProvider, so the CallKit report is fully in native land.

**Confirmed:** CallKit reporting happens in native AppDelegate, not deferred to JS bridge.

---

## Check 5: Token Cleanup (BadDeviceToken / Unregistered Handling)

**Result: PASS**

### VoIP Push Token Cleanup (push.js line 379-384)

```js
if (reason === 'BadDeviceToken' || reason === 'Unregistered') {
  tokenEntry.voipToken = null;
  pushTokens.set(mailboxId, tokenEntry);
  pushDirty = true;
}
```

When a VoIP push fails with BadDeviceToken or Unregistered, only the `voipToken` field is nullified (the regular APNs token is preserved). This is correct -- the VoIP token can become invalid independently of the regular push token.

### Regular APNs Token Cleanup (push.js line 229-234, 306-311)

Both `sendSilentPush()` and `sendiOSCallPush()` properly handle BadDeviceToken/Unregistered by deleting the full token entry and userMailbox mapping.

### FCM Token Cleanup (push.js line 430-436)

`sendAndroidPush()` handles `messaging/registration-token-not-registered` and `messaging/invalid-registration-token` by cleaning up all three maps (pushTokens, userMailboxes, lastPushTime).

### Fallback on Invalid VoIP Token (push.js line 350-355)

When no VoIP token is present (either never registered or cleaned up), `sendVoIPPush()` gracefully falls back to `sendiOSCallPush()` (regular alert-based call push).

**Confirmed:** All token cleanup paths are correctly implemented across VoIP, APNs, and FCM.

---

## Additional Observations

### A. VoIP Push Topic Configuration (PASS)

The VoIP push correctly uses `BUNDLE_ID + '.voip'` as the topic (push.js line 360) and `pushType: 'voip'` (line 361). This is the Apple-mandated format for PushKit VoIP notifications.

### B. Authentication Gate (PASS)

The `register-voip-token` handler (index.js line 591-611) properly requires authentication, with the same grace period handling as `register-push-token`. Input validation checks string presence and max length.

### C. No Throttle on VoIP Calls (ACCEPTABLE)

VoIP pushes have no throttle (push.js line 358 comment). This is correct -- Apple does not throttle VoIP pushes on their end, and every call attempt must reach the device. The 5-second throttle on Android FCM (line 318) provides minimal DoS protection without blocking legitimate rapid re-dials.

### D. PushKit Delegate Token Persistence (PASS)

The VoIP token is saved to UserDefaults in AppDelegate (line 103) and exposed to JS via `getVoIPToken()` native module (line 158-161). The token is only printed truncated to 16 chars (line 105).

---

## Summary

| # | Check | Result |
|---|-------|--------|
| 1 | Zero-content policy (iOS VoIP push) | PASS |
| 1 | Zero-content policy (Android FCM call push) | **FAIL** -- SDP offer in payload |
| 2 | Token isolation (anonymous mailboxId) | PASS |
| 3 | No server-side logging of sensitive data | **FAIL** -- caller name logged |
| 4 | CallKit report in native code | PASS |
| 5 | Token cleanup (BadDeviceToken/Unregistered) | PASS |

---

## Overall Verdict: NEEDS FIXES

Two issues must be resolved before this implementation can be considered security-compliant:

### Fix 1 (HIGH): Remove SDP offer from Android FCM payload

**File:** `/Users/ruslanconstantinovici/QRChat/server/push.js` line 460-466
**Action:** Remove `offer` field from Android call push. The Android client should wake from FCM push, reconnect WebSocket, and retrieve the offer through the encrypted signaling channel.

### Fix 2 (MEDIUM): Remove caller name from VoIP push log

**File:** `/Users/ruslanconstantinovici/QRChat/server/push.js` line 371
**Action:** Remove `(caller: ${callData.callerName || 'Unknown'})` from the console.log statement. Truncated mailboxId is sufficient for debugging.

---

*Security Engineer -- QRChat Agent Team*
