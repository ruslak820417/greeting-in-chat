# Privacy Policy — Security Audit

**Auditor:** security-engineer
**Date:** 2026-03-21
**Codebase:** /Users/ruslanconstantinovici/QRChat
**Privacy Policy:** /Users/ruslanconstantinovici/QRChat/docs/privacy.html

---

## 1. Data Flow Audit

Complete inventory of all data that leaves the user's device and reaches the server or third-party services:

| Data | Destination | Encrypted E2E? | Server Stores? | Retention | Can be linked to identity? |
|------|------------|----------------|----------------|-----------|---------------------------|
| Public Key (User ID) | QRChat server (WebSocket `register`) | No (used as identifier) | In-memory only (`clients` Map) | Until WS disconnect | **IS** the user identity |
| Auth Challenge Signature | QRChat server (WebSocket `auth-response`) | No | Not stored | Transient | Yes (proves key ownership) |
| Mailbox ID | QRChat server (`register-push-token`) | No | Yes — `qrchat_user_mailboxes.json` (mapped to userId) | Until token invalidated | **YES** — linked to userId via `userMailboxes` Map |
| APNs Device Token | QRChat server (`register-push-token`) | No | Yes — `qrchat_push_tokens.json` (mapped to mailboxId) | Until BadDeviceToken/Unregistered | Indirectly — via mailboxId -> userId link |
| Encrypted Message Payload | QRChat server (`encrypted-message`) | **Yes** (nacl.box / Double Ratchet) | Yes — `qrchat_pending_messages.json` (only if recipient offline) | 48 hours max | No (opaque blob) |
| Sender userId (in push payload) | Apple APNs (field `s` in push notification) | No | Transient (APNs delivery) | APNs transient | **YES** — Apple sees sender's public key |
| Device ID (licensing) | QRChat server (`/redeem-promo`, `/check-license`) | No | Yes — `qrchat_licensed.json` | Indefinitely | Not linked to userId, but is a persistent device identifier |
| SDP Offer/Answer | QRChat server (WebSocket `offer`/`answer`) | No (but contains DTLS fingerprints, not message content) | Yes if recipient offline — pending queue | 48 hours max | Yes (contains `from` userId) |
| ICE Candidates | QRChat server (WebSocket `ice-candidate`) | No | Yes if recipient offline — pending queue | 48 hours max | Contains IP addresses of peers |
| TURN Relay Traffic | Metered.ca TURN servers | **Yes** (SRTP/DTLS encrypted by WebRTC) | No | Transient | Metered.ca sees IP addresses |
| Delivery/Read Receipts | QRChat server (relay) | No (messageId + timestamp) | Yes if recipient offline | 48 hours max | Yes (from/to userIds) |
| Typing Indicators | QRChat server (relay) | No | Not stored | Transient (live relay only) | Yes (from/to userIds) |
| Contact Requests | QRChat server (relay) | No (fromName, publicKey, fingerprint in cleartext) | Yes if recipient offline | 48 hours max | **YES** — contains display name in cleartext |
| Report Data | QRChat server (`/report`) | No | Yes — `qrchat_reports.json` | Indefinitely | **YES** — reporterId, reportedUserId, reason |
| IP Addresses | QRChat server (WebSocket connection, HTTP requests) | N/A | Transiently in rate-limit Map | 60s (rate limit window) | Potentially linkable |
| TURN Credentials Request | QRChat server (`get-turn-credentials`) | No | Not stored | Transient | Yes (authenticated connection) |

---

## 2. Privacy Policy Claim Verification

### Claim 1: "All messages are end-to-end encrypted before leaving your device"
**CONFIRMED**

- `src/crypto/KeyManager.ts:121-141` — `encryptMessage()` uses `nacl.box()` (XSalsa20-Poly1305 with X25519 ECDH)
- `src/crypto/DoubleRatchet.ts` — Double Ratchet protocol for forward secrecy (used when available)
- `src/services/MessagingService.ts:386-410` — Every text message is encrypted before sending (Double Ratchet first, fallback to legacy nacl.box)
- Server `index.js:675` — Server relays `message.payload` opaquely, never inspects content

### Claim 2: "Our server relays encrypted blobs it cannot decrypt"
**CONFIRMED**

- `server/index.js:656-708` — The `encrypted-message` handler simply forwards `message.payload` to the recipient or enqueues it. No decryption, no inspection.
- Server has no access to private keys. The only crypto library on server (`tweetnacl`) is used solely for auth challenge verification (`nacl.sign.detached.verify`).

### Claim 3: "QRChat requires no registration, no phone number, and no email address"
**CONFIRMED**

- Key pair generation happens locally in `src/crypto/KeyManager.ts:16-31`
- `src/screens/SetupScreen.tsx` — Setup only asks for a display name (stored locally)
- No server-side user registration, no account creation endpoint

### Claim 4: "Contact discovery happens exclusively via in-person QR code scanning"
**PARTIALLY CONFIRMED — NEEDS CLARIFICATION**

- QR-based contact exchange is the primary method: `src/crypto/KeyManager.ts:51-70` (createQRPayload), verified in `verifyQRPayload`
- **CONCERN:** `react-native-contacts` is a dependency (`package.json:32`) and contact permission is requested at startup (`src/services/MessagingService.ts:292-297`). The `Info.plist:45-46` contains `NSContactsUsageDescription`.
- While no evidence of uploading contacts to the server was found, requesting address book access contradicts the "exclusively via QR" claim
- Contact requests can also be sent via the signaling server (`contact-request` message type) — this is a remote request mechanism, not purely in-person

### Claim 5: "QRChat contains no analytics SDKs, no crash reporting services"
**CONFIRMED**

- No Firebase, Sentry, Crashlytics, Amplitude, Mixpanel, or Segment in `package.json` or `Podfile`
- `PrivacyInfo.xcprivacy:35-36` — `NSPrivacyTracking` = `false`
- `NSPrivacyCollectedDataTypes` = empty array
- Grep for analytics/tracking SDKs returned no relevant results

### Claim 6: "QRChat does not use IDFA, IDFV"
**CONFIRMED**

- No `AdSupport`, `AppTrackingTransparency`, `ASIdentifierManager`, or `identifierForVendor` usage found anywhere in the codebase
- `PrivacyInfo.xcprivacy` does not declare any advertising-related APIs

### Claim 7: "Private keys are stored exclusively in the iOS Keychain"
**CONFIRMED**

- `src/storage/Database.ts:754-764` — Private keys stored via `Keychain.setGenericPassword` with `WHEN_UNLOCKED_THIS_DEVICE_ONLY`
- `src/storage/Database.ts:772-773` — If Keychain is unavailable, the code **throws an error** rather than falling back to insecure storage
- `src/crypto/RatchetStore.ts:35-38` — Double Ratchet state also stored in Keychain with `WHEN_UNLOCKED_THIS_DEVICE_ONLY`

### Claim 8: "The database encryption key is stored in the iOS Keychain with WHEN_UNLOCKED_THIS_DEVICE_ONLY"
**CONFIRMED**

- `src/storage/Database.ts:66-85` — `getDbEncryptionKey()` generates a 32-byte random key, stored in Keychain with `accessible: Keychain.ACCESSIBLE.WHEN_UNLOCKED_THIS_DEVICE_ONLY`
- `src/storage/Database.ts:128` — SQLite DB opened with `encryptionKey` parameter (SQLCipher/op-sqlite)

### Claim 9: "Anonymous Mailbox ID: A random 128-bit identifier (not derived from any key material or personal data)"
**CONFIRMED**

- `src/services/PushTokenService.ts:42` — `nacl.randomBytes(16)` = 128 bits of cryptographic randomness
- Not derived from public key, private key, or any user data
- Stored in AsyncStorage with key `@qrchat_mailbox_id`

### Claim 10: "Push notification throttling (maximum 1 per 30 seconds per mailbox)"
**CONFIRMED**

- `server/push.js:22` — `THROTTLE_INTERVAL_MS = 30 * 1000`
- `server/push.js:160-164` — Throttle check using `lastPushTime` Map

### Claim 11: "Encrypted pending messages stored for maximum 48 hours"
**CONFIRMED**

- `server/index.js:38` — `MESSAGE_EXPIRY = 48 * 60 * 60 * 1000`
- `server/index.js:48-49` — Messages filtered on load from disk (expired ones dropped)
- `server/index.js:152-166` — Periodic cleanup every hour removes expired messages

### Claim 12: "WebSocket connections over TLS (wss://)"
**CONFIRMED (production only)**

- `src/network/SignalingClient.ts:15` — Production URL: `wss://exciting-success-production-d272.up.railway.app`
- `src/network/SignalingClient.ts:14` — Dev mode allows `ws://` (localhost/LAN only) — this is expected and acceptable
- `src/network/SignalingClient.ts:52-62` — Code enforces `wss://` for production, `ws://` only in `__DEV__` mode

### Claim 13: "Licensed Device ID — a hashed device identifier"
**INCORRECT — NOT HASHED**

- `src/services/LicensingService.ts:27-41` — Device ID is a **random UUID** generated via `Math.random()`, NOT a hash of any device identifier
- `server/licensing.js:192` — Stored as-is (raw UUID) in `qrchat_licensed.json`
- The privacy policy says "hashed device identifier" but the code generates a random UUID. While a random UUID is arguably better for privacy than a hashed hardware ID (it's not linkable to the physical device), **the privacy policy description is factually incorrect**.
- **Correction needed:** Change "a hashed device identifier" to "a randomly generated identifier stored locally on the device, not linked to any hardware identifier"

---

## 3. Privacy Concerns Identified

### 3.1 CRITICAL: Server Links userId to mailboxId

**File:** `server/push.js:119`
```javascript
userMailboxes.set(userId, mailboxId);
```

**Issue:** Despite the two-Map architecture (Pitfall 1 prevention), the server **does** maintain a direct `userId -> mailboxId` mapping in `qrchat_user_mailboxes.json`. This means:
- Anyone with server access can link a push token to a user identity by joining the two files
- The privacy policy's implication that mailboxId is "not linked to user identity" is technically misleading — the server has the link

**Impact:** Medium-High. The separation provides defense-in-depth but is not a true unlinking.

**Recommendation:** Acknowledge in privacy policy that the server temporarily maintains this mapping for routing purposes but emphasize that no human reviews these files.

### 3.2 HIGH: Sender Public Key in APNs Push Payload

**File:** `server/push.js:174`
```javascript
note.payload = { e: 1, s: senderUserId };
```

**Issue:** The sender's full public key (userId) is included in the push notification payload sent to Apple APNs. This means:
- Apple can see who is messaging whom (sender -> recipient mapping via device token)
- This is metadata leakage — not message content, but communication patterns

**Impact:** Medium. Apple already sees the device token; adding the sender identity increases the metadata exposure.

**Recommendation:** Consider hashing or encrypting the sender identifier in the push payload, or remove it entirely if the NSE can look up the sender from the pending message queue.

### 3.3 HIGH: Contact Request Metadata in Cleartext

**File:** `server/index.js:818-827`

**Issue:** Contact request payloads contain `fromName` (display name), `fromPublicKey`, `fromFingerprint` in cleartext. These are relayed and potentially stored (if recipient offline) without E2E encryption.

**Impact:** Medium. Display names are personal data. If the pending message store is compromised, contact request display names are exposed.

**Recommendation:** Encrypt contact request payloads E2E like regular messages.

### 3.4 MEDIUM: Report Endpoint Stores User Identifiers

**File:** `server/index.js:271-301`

**Issue:** The `/report` endpoint stores `reporterId`, `reportedUserId`, `messageId`, and `reason` in `qrchat_reports.json` **indefinitely** with no expiry. This data:
- Links two user IDs together
- Contains the reason for reporting
- Is not mentioned in the privacy policy

**Impact:** Medium. Required by App Store but must be disclosed in privacy policy.

**Recommendation:** Add report data to privacy policy data inventory, implement data retention policy (e.g., 90-day expiry).

### 3.5 MEDIUM: react-native-contacts Permission

**Files:** `src/services/MessagingService.ts:292-297`, `package.json:32`, `Info.plist:45-46`

**Issue:** The app requests access to the device's address book at startup, but the privacy policy states "Contact discovery happens exclusively via in-person QR code scanning" and "We never upload or access your device's address book for server-side matching."

**Impact:** Medium. Even if contacts aren't uploaded, requesting the permission contradicts the privacy-first messaging and triggers Apple's data collection declaration requirements.

**Recommendation:** Either remove the contacts permission entirely, or disclose its use in the privacy policy.

### 3.6 LOW: Server Logs Contain Truncated User IDs

**File:** `server/index.js:486,529,608` (multiple locations)

**Issue:** Server logs truncated public keys (first 8 chars): `${publicKey.substring(0, 8)}...`. Also logs message types and routing (`[->] offer: XXXX... -> YYYY...`).

**Impact:** Low. 8 chars of a base64 public key is a weak identifier, but combined with timestamps, it reveals communication patterns.

**Recommendation:** Consider reducing logging to aggregate counts only, or ensure logs are rotated/deleted regularly.

### 3.7 LOW: IP Address Exposure

**File:** `server/index.js:229`

**Issue:** WebSocket connections expose client IP addresses to the server. The admin rate limiter uses `req.ip`. IP addresses are not mentioned in the privacy policy.

**Impact:** Low. Standard for any web service, but should be disclosed.

**Recommendation:** Mention IP address processing in privacy policy (transient, for rate limiting and abuse prevention).

### 3.8 LOW: TURN Credentials Are Static (Not Per-Session)

**File:** `server/index.js:190-200, 780-794`

**Issue:** The TURN credentials (`TURN_USERNAME`, `TURN_CREDENTIAL`) are static environment variables, shared across all users. The privacy policy says "Temporary credentials; generated per session" but they are actually long-lived static credentials from Metered.ca.

**Impact:** Low. Metered.ca does provide the relay, but the credentials are not truly per-session.

**Recommendation:** Correct the privacy policy to say "shared credentials" or implement Metered.ca's REST API for per-session TURN credential generation.

### 3.9 INFO: Admin Secret Storage

**File:** `server/licensing.js:23,244-248`

**Issue:** `qrchat_admin_secret.json` stores the admin password in plaintext on disk. While not a user privacy issue, it's a security concern if the server is compromised.

**Impact:** Low for privacy, medium for security.

---

## 4. Recommendations for Privacy Policy

### 4.1 Items to Add

1. **Report data:** The `/report` endpoint collects `reporterId`, `reportedUserId`, `reason`, and timestamps. Must be disclosed with retention period.

2. **IP addresses:** Server processes IP addresses for rate limiting and WebSocket connections. Should be mentioned under "automatically collected data."

3. **Contact request metadata:** When a contact request is pending (recipient offline), display names are stored in cleartext on the server for up to 48 hours.

4. **Server-side data linkage:** Disclose that the server maintains a mapping between userId and mailboxId for push notification routing.

5. **Sender identity in push notifications:** The push payload includes the sender's identifier, which is transmitted through Apple's APNs infrastructure.

6. **Phone contacts permission:** If retained, the purpose of requesting address book access must be explained.

7. **Legal basis for processing (GDPR):** Specify legitimate interest or consent as the basis for data processing.

8. **International data transfer:** Server hosted on Railway.app (US). EU users' data is transferred to the US. Need to address adequacy/safeguards.

9. **Data Protection Officer:** If processing EU data, consider whether a DPO appointment is needed.

### 4.2 Items to Correct

1. **"Licensed Device ID — a hashed device identifier"** → The device ID is a randomly generated UUID, NOT a hash. Change to: "a randomly generated identifier, not derived from hardware identifiers."

2. **"Temporary TURN credentials; generated per session"** → Credentials are static env vars, not per-session. Change to: "TURN relay credentials for WebRTC connections" or implement actual per-session credentials.

3. **"Contact discovery happens exclusively via in-person QR code scanning"** → The app also supports remote contact requests via the signaling server, and requests phone contacts permission. Needs rewording.

### 4.3 Items to Clarify

1. **Two-Map push architecture:** The privacy policy implies mailboxId prevents identity linkage, but the server maintains the userId->mailboxId mapping. Clarify that this mapping exists for routing but is never exposed to third parties.

2. **"We never upload or access your device's address book"** → Technically true (no upload to server), but the app requests the permission. Clarify the purpose or remove the permission.

3. **WebSocket security:** Clarify that `wss://` (TLS) is enforced in production. Dev mode allows plaintext connections for local testing only.

4. **Data deletion rights:** Clarify how users can request deletion of server-side data (push tokens, mailbox IDs, report data). Currently only says "contact us."

5. **Promo code data:** When a promo code is redeemed, the device ID and usage timestamp are stored. This should be mentioned.

---

## 5. GDPR Technical Compliance Assessment

### Art. 5(1)(c) — Data Minimization
**LARGELY COMPLIANT**
- Server stores minimal data: encrypted message blobs (48h), push routing data, licensing records
- No user profiles, contact lists, or message history on server
- **Gap:** Contact request display names stored in cleartext; report data stored indefinitely

### Art. 25 — Privacy by Design
**COMPLIANT with minor gaps**
- E2E encryption by default for all messages
- Anonymous mailbox architecture for push notifications
- No registration required (key pair = identity)
- Private keys never leave the device
- **Gap:** The userId->mailboxId link undermines the anonymity architecture; contact requests not E2E encrypted

### Art. 32 — Technical Security Measures
**COMPLIANT**
- TweetNaCl (XSalsa20-Poly1305, X25519, Ed25519) for message encryption
- SQLCipher (AES-256) for local database
- iOS Keychain (WHEN_UNLOCKED_THIS_DEVICE_ONLY) for key storage
- Ed25519 challenge-response authentication on WebSocket
- Rate limiting (token bucket) on WebSocket connections
- Admin endpoint rate limiting

### Art. 35 — DPIA Requirement
**LIKELY NOT REQUIRED** but recommended as best practice. QRChat processes minimal personal data and uses E2E encryption. However, given the communication metadata (who talks to whom, when), a lightweight DPIA would strengthen the compliance posture.

### Recital 26 — Personal Data Classification
- **Public Key (userId):** Pseudonymous identifier — qualifies as personal data under GDPR because it can identify a specific device/user across sessions
- **Mailbox ID:** Pseudonymous, linked to userId on server — personal data
- **APNs Token:** Linked to a specific device — personal data
- **Device ID (licensing):** Random UUID, not hardware-derived — personal data (persistent identifier)
- **Display Name:** Direct personal data (if user provides real name)
- **Encrypted message content:** Not accessible by controller — likely excluded per Recital 26 (cannot be attributed without decryption keys held exclusively by data subjects)

---

## 6. Server-Side Data Inventory

### Files Created by Server on Disk

| File | Contents | Retention | Privacy Risk |
|------|----------|-----------|-------------|
| `qrchat_pending_messages.json` | Encrypted message blobs with timestamps, sender/recipient userIds, messageIds | Auto-purged after 48h | Low (messages encrypted, but metadata visible) |
| `qrchat_push_tokens.json` | `mailboxId -> {platform, token, registeredAt}` | Until token invalidated | Medium (APNs tokens are device identifiers) |
| `qrchat_user_mailboxes.json` | `userId -> mailboxId` | Until token invalidated | **HIGH** (links user identity to push token) |
| `qrchat_codes.json` | Promo codes with `{createdAt, usedAt, usedBy, deviceId, signature}` | Indefinitely | Medium (links promo usage to device) |
| `qrchat_licensed.json` | `deviceId -> true` | Indefinitely | Low (random UUID, not hardware ID) |
| `qrchat_admin_secret.json` | `{secret, changedAt}` | Indefinitely | Low for privacy (admin credential) |
| `qrchat_reports.json` | `[{reporterId, reportedUserId, messageId, reason, timestamp, receivedAt}]` | **Indefinitely (no expiry!)** | **HIGH** (links user IDs, contains reasons) |

### In-Memory Only (Not Persisted)

| Structure | Contents | Lifetime |
|-----------|----------|----------|
| `clients` Map | `userId -> WebSocket` | Until disconnect |
| `lastPushTime` Map | `mailboxId -> timestamp` | Until server restart |
| `adminRateLimit` Map | `ip -> {count, resetAt}` | 60s windows, cleaned every 5 min |
| `ws.rateBucket` | Token bucket per connection | Until disconnect |

### Data Location
- **Server host:** Railway.app (US data center)
- **Volume mount:** `RAILWAY_VOLUME_MOUNT_PATH` or `/tmp`
- **Save frequency:** Every 60 seconds (if dirty) + on SIGTERM/SIGINT

---

## Appendix: Success Criteria Checklist

- [x] Every privacy policy claim verified with code line reference
- [x] Complete data flow table (all data leaving device)
- [x] All server-side JSON persistence files identified (7 files)
- [x] Confirmed push notification payload does NOT contain message text (push.js:174 — only `{e:1, s:senderUserId}`)
- [x] Confirmed userId/mailboxId/pushToken separation architecture (two Maps in push.js, but linked via userMailboxes)
- [x] Assessed mailboxId/publicKey as pseudonymous personal data under GDPR Recital 26
- [x] Verified package.json and PrivacyInfo.xcprivacy for analytics/tracking SDKs (none found)
- [x] Reported 3 discrepancies between privacy policy and code (device ID not hashed, TURN not per-session, contacts permission)
- [x] Report written to `agent-runtime/outputs/privacy-security-audit.md`
