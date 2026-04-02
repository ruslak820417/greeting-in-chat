# QRChat Android — Security Audit Report

**Date:** 2026-03-23
**Auditor:** Security Engineer (Agent)
**Project:** QRChat-Android v4.2.0 (React Native 0.84)
**Path:** `/Users/ruslanconstantinovici/QRChat-Android`

---

## Executive Summary

QRChat Android has a **strong security posture** overall. The E2E encryption is well-implemented using the Signal Double Ratchet protocol, key storage uses Android Keystore (via react-native-keychain), the database is encrypted with SQLCipher, and WebSocket connections enforce TLS with relay pinning.

**2 critical issues** and **3 medium-priority improvements** were identified.

| # | Check | Status | Severity |
|---|-------|--------|----------|
| 1 | E2E — Double Ratchet | PASS | — |
| 2 | Keychain → Android Keystore | PASS | — |
| 3 | SQLCipher activation | PASS | — |
| 4 | AndroidManifest permissions | PASS (warnings) | Medium |
| 5 | google-services.json in git | PASS (risk) | Medium |
| 6 | Release keystore in git | CRITICAL | Critical |
| 7 | Server auth — Ed25519 challenge | PASS | — |
| 8 | Firebase service account exposure | PASS | — |
| 9 | WebSocket — wss:// TLS | PASS | — |
| 10 | Relay pinning | PASS | — |

---

## 1. E2E Encryption — Double Ratchet

**Status: PASS**

**File:** `src/crypto/DoubleRatchet.ts`

Full Signal Double Ratchet implementation using TweetNaCl primitives:
- **DH ratchet:** X25519 ephemeral keypairs rotated on each DH exchange
- **KDF:** HMAC-SHA512 based HKDF with domain-separated labels (`QRChatRootKey`, `QRChatChainKey`)
- **Encryption:** XSalsa20-Poly1305 (nacl.secretbox) with random 24-byte nonces
- **Forward secrecy:** New sending keypair generated on every DH ratchet step
- **Skipped message keys:** Capped at `MAX_SKIP=100` per chain, `MAX_MKSKIPPED_TOTAL=500` globally — prevents memory exhaustion attacks
- **Initialization:** Shared secret from mutual QR scan → `nacl.box.before()` → initiator/responder roles assigned by peerId comparison

This is pure JavaScript/TypeScript code that runs identically on Android and iOS via Hermes. No platform-specific crypto differences.

**Ratchet state persistence:** Stored in Keychain (see #2), survives app restarts, encrypted by OS.

---

## 2. Keychain → Android Keystore

**Status: PASS**

**Files:** `src/crypto/RatchetStore.ts`, `src/storage/Database.ts`

`react-native-keychain` v10.0.0 on Android uses **Android Keystore** with hardware-backed encryption:
- Cipher storage options: `KeystoreAESGCM`, `KeystoreAESCBC`, `KeystoreRSAECB`
- Keys are generated and stored in Android KeyStore (hardware-backed on supported devices)
- `WHEN_UNLOCKED_THIS_DEVICE_ONLY` accessibility level is correctly set

**What is stored in Keychain:**
| Data | Service Key |
|------|------------|
| Private keys (X25519 + Ed25519) | `qrchat.private_keys.<installId>` |
| Double Ratchet state (per contact) | `com.qrchat.ratchet.<contactId>` |
| SQLCipher DB encryption key | `qrchat.db_encryption_key` |
| File-at-rest encryption key | `qrchat.file_encryption_key` |

**Note:** No direct use of `EncryptedSharedPreferences` — `react-native-keychain` provides equivalent or better security via Keystore-backed AES-GCM encryption. This is the correct approach for React Native.

---

## 3. SQLCipher Activation

**Status: PASS**

**File:** `src/storage/Database.ts:124-141`

- Uses `@op-engineering/op-sqlite` with `encryptionKey` parameter (SQLCipher under the hood)
- 32-byte random encryption key generated via `crypto.getRandomValues()`
- Key stored in Android Keystore via `react-native-keychain`
- **Migration path:** If existing unencrypted DB detected, data is exported, old DB deleted, new encrypted DB created — no data loss
- **File encryption:** Received files encrypted at rest with separate Keychain-stored key (`getFileEncryptionKey()`)

---

## 4. AndroidManifest Permissions

**Status: PASS with warnings**

**File:** `android/app/src/main/AndroidManifest.xml`

| Permission | Justification | Issue |
|-----------|---------------|-------|
| `INTERNET` | Signaling, push | OK |
| `CAMERA` | QR scanning, video calls | OK |
| `RECORD_AUDIO` | Voice/video calls | OK |
| `READ_CONTACTS` | Phone contacts import | OK |
| `VIBRATE` | Notifications | OK |
| `POST_NOTIFICATIONS` | Push notifications (API 33+) | OK |
| `USE_FULL_SCREEN_INTENT` | Incoming call screen | OK |
| `FOREGROUND_SERVICE` | Call/notification service | OK |
| `WAKE_LOCK` | Keep alive during calls | OK |
| `READ_MEDIA_IMAGES` | Media picker (API 33+) | OK |
| `READ_EXTERNAL_STORAGE` | Legacy media access | **Medium** |
| `WRITE_EXTERNAL_STORAGE` | Legacy file write | **Medium** |

**Medium issue:** `READ_EXTERNAL_STORAGE` and `WRITE_EXTERNAL_STORAGE` are unnecessary on API 33+ (targetSdk=36). They grant broad file access on older devices.

**Recommendation:** Add `android:maxSdkVersion="32"` to both legacy storage permissions:
```xml
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" android:maxSdkVersion="32" />
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" android:maxSdkVersion="32" />
```

**Good:** `android:allowBackup="false"` is set — prevents ADB backup of app data.

---

## 5. google-services.json

**Status: PASS (with risk)**

**File:** `android/app/google-services.json`

The file contains **placeholder values only**:
```json
"project_id": "REPLACE_WITH_YOUR_PROJECT_ID",
"current_key": "REPLACE_WITH_YOUR_API_KEY"
```

The file is **NOT tracked in git** (confirmed via `git ls-files`).

**Medium risk:** The `.gitignore` does NOT explicitly exclude `google-services.json`. A `git add .` or `git add -A` would accidentally commit it once real credentials are added.

**Recommendation:** Add to `.gitignore`:
```
android/app/google-services.json
```

---

## 6. Release Keystore — NOT in .gitignore

**Status: CRITICAL**

**Files:**
- `android/app/qrchat-release.keystore` — release signing keystore (exists on disk)
- `android/keystore.properties` — contains **plaintext passwords**:
  ```
  storePassword=QRChat2026Release
  keyPassword=QRChat2026Release
  ```

**Current state:** Neither file is tracked in git (good). However, **neither is listed in `.gitignore`**.

**Current `.gitignore`:**
```
node_modules/
.git/
ios/build/
android/build/
*.jsbundle
/tmp/
vendor/
.env
```

**Risk:** A single `git add .` or `git add -A` command would commit both the keystore and its passwords to the repository. If the repo is ever made public or shared, the signing key is compromised permanently.

**Required fix — add to `.gitignore` immediately:**
```
# Signing keys
android/keystore.properties
android/app/qrchat-release.keystore
*.jks
```

---

## 7. Server Auth — Ed25519 Challenge

**Status: PASS**

**Files:** `server/index.js:414-488`, `src/network/SignalingClient.ts:156-201`

**Server flow:**
1. On new WebSocket connection, server generates 32-byte random nonce (`nacl.randomBytes(32)`)
2. Sends `auth-challenge` with base64-encoded nonce
3. Client signs nonce with Ed25519 signing key (`nacl.sign.detached`)
4. Server verifies with `nacl.sign.detached.verify(nonce, signature, publicKey)`
5. On success: `ws.authenticated = true`
6. On failure: connection closed

**Client flow (Android):**
- `SignalingClient._tryConnect()` handles `auth-challenge` message
- Uses `KeyManager.signMessage()` with Ed25519 signing key
- Falls back to direct register only if no signing keys available (legacy support)

**Auth gate:**
- All message types except `auth-response` require `ws.authenticated === true`
- Grace period (`GRACE_PERIOD`) controlled by env var `QRCHAT_GRACE_PERIOD`, not hardcoded

**This works identically from Android** — the crypto is pure JS/TypeScript via TweetNaCl, platform-agnostic.

---

## 8. Firebase Service Account

**Status: PASS**

No Firebase service account key files (`serviceAccount.json`, `firebase-admins-sdk-*.json`) found in client code. Server-side push notification handling is in `server/push.js` (server-only module, not bundled in the app).

The `google-services.json` in the Android app contains only client-side Firebase config (API keys, project IDs) — these are safe to ship in apps per Google's documentation.

---

## 9. WebSocket — wss:// TLS

**Status: PASS**

**File:** `src/network/SignalingClient.ts:55-79`

Production enforcement:
```typescript
// Production: require wss:// and pinned domain
if (protocol !== 'wss') {
  console.warn(`[SignalingClient] Rejected non-TLS relay: ${url}`);
  return false;
}
```

**Dev mode only:** Allows `ws://localhost` and `ws://192.168.*` (local testing). These are stripped from `FALLBACK_RELAY_URLS` in production builds via `__DEV__` flag.

Production URL: `wss://exciting-success-production-d272.up.railway.app` — TLS enforced.

---

## 10. Relay Pinning

**Status: PASS**

**File:** `src/network/SignalingClient.ts:19-23, 46-79`

```typescript
export const PINNED_RELAY_DOMAINS = new Set([
  'exciting-success-production-d272.up.railway.app',
]);
```

- All relay URLs (from BootstrapManager or fallback) must pass `validateRelayUrl()` before connection
- Unpinned domains are rejected: `"Rejected unpinned relay domain: ${hostname}"`
- If ALL URLs fail pinning, the client **refuses to connect**: `"No trusted relay URLs available"`
- GossipProtocol peers cannot inject rogue relay URLs
- Works identically on Android (pure JS/TypeScript)

---

## Additional Findings

### Proguard / R8 — DISABLED (Medium)

**File:** `android/app/build.gradle:62`
```groovy
def enableProguardInReleaseBuilds = false
```

Release APK is **not obfuscated**. The JavaScript bundle is minified by Metro/Hermes, but native Java/Kotlin code and any embedded strings remain readable.

**Recommendation:** Enable R8 minification for release builds:
```groovy
def enableProguardInReleaseBuilds = true
```

### Admin Secret — NOT Hardcoded (Good)

**File:** `server/licensing.js:90`

Admin secret loaded from `process.env.QRCHAT_ADMIN_SECRET` with optional disk persistence. Timing-safe comparison via `crypto.timingSafeEqual()`. Rate limited to 5 attempts per IP per minute. Admin endpoints disabled entirely if env var not set.

### Rate Limiting (Good)

Token bucket rate limiting: 200 burst tokens, 20 tokens/second refill, 1.5MB max payload per WebSocket message.

### Pending Queue DoS Protection (Good)

- `MAX_PENDING_PER_USER = 1000` messages
- `MAX_PENDING_SIZE_PER_USER = 50MB`
- Messages expire after 48 hours

---

## Summary of Required Actions

### Critical (Fix before release)
1. **Add to `.gitignore`:** `android/keystore.properties`, `android/app/qrchat-release.keystore`, `*.jks`
2. **Rotate keystore password** if the repo has ever been shared — the password `QRChat2026Release` is visible in plaintext

### Medium (Recommended)
3. **Add `maxSdkVersion="32"`** to `READ_EXTERNAL_STORAGE` and `WRITE_EXTERNAL_STORAGE` permissions
4. **Add `google-services.json`** to `.gitignore` before adding real Firebase credentials
5. **Enable Proguard/R8** for release builds (`enableProguardInReleaseBuilds = true`)

### Already Good
- E2E Double Ratchet with perfect forward secrecy
- Android Keystore integration via react-native-keychain
- SQLCipher database encryption
- Ed25519 challenge-response authentication
- wss:// TLS enforcement in production
- Relay domain pinning
- Admin secret from env var with timing-safe comparison
- allowBackup="false"
- Rate limiting and DoS protections
