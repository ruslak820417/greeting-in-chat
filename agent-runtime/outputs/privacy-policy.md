# Privacy Policy — QRChat

**Effective Date:** March 21, 2026
**Last Updated:** March 21, 2026
**App:** QRChat — Encrypted Messenger
**Bundle ID:** com.ruslan.qrchat
**Developer:** Ruslan Constantinovici

---

## 1. Introduction

QRChat is a privacy-first encrypted messenger. This Privacy Policy explains what information QRChat collects, how it is used, and your rights regarding your data.

QRChat is designed with a fundamental principle: **your conversations are yours alone**. We cannot read your messages, and we collect the minimum data necessary to deliver the service.

---

## 2. Information We Collect

### 2.1 Information You Provide

- **Display Name:** A name you choose during setup. This is shared only with contacts you approve and is stored locally on your device.
- **Profile Photo:** Optional. Stored locally and shared directly with approved contacts via encrypted peer-to-peer connections.

### 2.2 Information Generated Automatically

- **Cryptographic Key Pair:** A public/private key pair is generated on your device during first launch using the TweetNaCl cryptography library. The private key never leaves your device and is stored in the iOS Keychain (protected by the Secure Enclave). The public key serves as your user identifier on the signaling server.
- **Anonymous Mailbox ID:** A random 128-bit identifier (not derived from any key material or personal data) used solely to route push notifications. This prevents linking your push token to your user identity.
- **APNs Device Token:** Your Apple Push Notification service token, stored on our server mapped only to your anonymous mailbox ID, not to your user identity. Used exclusively to deliver silent push notifications when you have offline messages waiting.

### 2.3 Information We Do NOT Collect

- **Message content** — All messages are end-to-end encrypted before leaving your device. Our server relays encrypted blobs it cannot decrypt.
- **Phone number or email** — QRChat requires no registration, no phone number, and no email address.
- **Phone contacts** — Contact discovery happens exclusively via in-person QR code scanning. We never upload or access your device's address book for server-side matching.
- **Location data** — QRChat does not request or collect location information.
- **Analytics or usage data** — QRChat contains no analytics SDKs, no crash reporting services (e.g., Sentry, Crashlytics, Firebase), and no tracking pixels.
- **Advertising identifiers** — QRChat does not use IDFA, IDFV, or any advertising framework.
- **Browsing history or search queries** — Not applicable.

---

## 3. How We Use Information

| Data | Purpose | Retention |
|------|---------|-----------|
| Public Key (User ID) | Identify connected WebSocket clients for message routing | In-memory only; cleared on server restart |
| Anonymous Mailbox ID | Route push notifications without linking to user identity | Stored on server until push token is invalidated |
| APNs Device Token | Deliver silent push notifications for offline messages | Stored on server; automatically deleted when token becomes invalid (BadDeviceToken/Unregistered) |
| Encrypted Pending Messages | Deliver messages to offline recipients | Stored on server for a maximum of 48 hours, then automatically deleted. Server cannot decrypt these messages. |
| Licensed Device ID | Verify promo code redemption for QRChat Unlimited | Stored on server; a hashed device identifier, not linked to user identity or messages |
| TURN Relay Credentials | Facilitate peer-to-peer WebRTC connections when direct connection fails | Temporary credentials; generated per session via Metered.ca |

---

## 4. End-to-End Encryption

QRChat uses the **TweetNaCl** (Networking and Cryptography library) for all message encryption:

- **Key Exchange:** Contacts are added exclusively by scanning QR codes in person, which exchanges public keys directly between devices.
- **Message Encryption:** Every message (text, image, audio, video, file) is encrypted on the sender's device before transmission. Only the intended recipient's device can decrypt it.
- **Local Storage Encryption:** The on-device message database is encrypted using **SQLCipher** (AES-256). The database encryption key is stored in the iOS Keychain with `WHEN_UNLOCKED_THIS_DEVICE_ONLY` protection.
- **Private Key Storage:** Private keys are stored exclusively in the iOS Keychain, backed by the Secure Enclave where available.

**We have zero ability to read, scan, or analyze your message content.**

---

## 5. Data Storage

### 5.1 On Your Device

All personal data (messages, contacts, keys, settings, profile) is stored locally on your device in an encrypted SQLite database. If you delete the app, this data is permanently erased.

### 5.2 On Our Server

Our signaling server (hosted on **Railway.app**, data center in US) stores only:

- Encrypted message blobs for offline delivery (auto-deleted after 48 hours)
- Anonymous push notification routing data (mailbox ID + APNs token)
- Licensed device records (for promo code verification)

The server **does not** maintain user profiles, contact lists, message history, or any decrypted content.

---

## 6. Third-Party Services

QRChat uses the following third-party services:

### 6.1 Apple Push Notification Service (APNs)
- **Purpose:** Deliver silent push notifications to wake the app when offline messages are waiting.
- **Data shared:** Anonymous APNs device token and a minimal payload containing only an event flag and sender's public key (no message content).
- **Provider:** Apple Inc.
- **Privacy Policy:** https://www.apple.com/legal/privacy/

### 6.2 Metered.ca (TURN Relay)
- **Purpose:** Relay encrypted WebRTC traffic when a direct peer-to-peer connection cannot be established (e.g., behind strict NATs/firewalls).
- **Data shared:** Encrypted media streams only. Metered.ca cannot decrypt the content. Temporary TURN credentials are generated per session.
- **Provider:** Metered Video Inc.
- **Privacy Policy:** https://www.metered.ca/privacy

### 6.3 Railway.app (Server Hosting)
- **Purpose:** Hosts the QRChat signaling server.
- **Data processed:** Only the server-side data described in Section 5.2.
- **Provider:** Railway Corp.
- **Privacy Policy:** https://railway.app/legal/privacy

QRChat does **not** use any analytics, advertising, crash reporting, or social media SDKs.

---

## 7. Data Retention

| Data | Retention Period |
|------|-----------------|
| Encrypted pending messages | Maximum 48 hours, then automatically purged |
| Push notification tokens | Until the token is invalidated by Apple (device token change, app uninstall) |
| Anonymous mailbox IDs | Until the associated push token is invalidated |
| Licensed device records | Indefinitely (required for ongoing license verification) |
| On-device data (messages, contacts, keys) | Until you delete the app or clear app data |

---

## 8. Data Sharing

We do **not** sell, rent, trade, or share your personal data with any third party for marketing, advertising, or any purpose beyond the service delivery described in this policy.

We may disclose information only if required by law, but given our architecture:
- We cannot provide message content (it is end-to-end encrypted and we do not hold decryption keys).
- We can only provide the limited server-side data described in Section 5.2.

---

## 9. Your Rights

You have the right to:

- **Access:** Request information about what data we store associated with your anonymous identifiers.
- **Deletion:** Delete all your local data by uninstalling the app. Server-side pending messages are automatically purged within 48 hours. To request immediate deletion of push token and mailbox data, contact us.
- **Portability:** Your messages and contacts are stored locally on your device and can be accessed through the app.

### For EU/EEA Residents (GDPR)
You have additional rights under GDPR including the right to rectification, restriction of processing, and the right to lodge a complaint with a supervisory authority. Given our minimal data collection and end-to-end encryption architecture, the data we process is extremely limited.

### For California Residents (CCPA)
QRChat does not sell personal information. We do not use personal information for targeted advertising. You may request deletion of any server-side data by contacting us.

---

## 10. Children's Privacy

QRChat is not directed at children under 13. We do not knowingly collect personal information from children under 13. Since QRChat requires no registration and collects no personal information, the risk is minimal. If you believe a child under 13 is using QRChat inappropriately, please contact us.

---

## 11. Security

We implement the following security measures:

- End-to-end encryption (TweetNaCl) for all messages and media
- SQLCipher (AES-256) encryption for the local database
- iOS Keychain with Secure Enclave protection for private keys
- Anonymous mailbox architecture to prevent push token/identity linkage
- No plaintext message storage on the server at any point
- WebSocket connections over TLS (wss://)
- Server-side message expiry (48 hours maximum)
- Push notification throttling (maximum 1 per 30 seconds per mailbox)

---

## 12. Encryption Export Compliance

QRChat uses encryption (TweetNaCl / NaCl, SQLCipher). The `ITSAppUsesNonExemptEncryption` flag is set to `YES` in Info.plist. A proper encryption registration (ERN/CCATS) or exemption filing may be required depending on distribution countries.

---

## 13. Changes to This Policy

We may update this Privacy Policy from time to time. We will notify users of significant changes through the app or by updating the "Last Updated" date. Continued use of QRChat after changes constitutes acceptance of the updated policy.

---

## 14. Contact

If you have questions about this Privacy Policy or your data:

- **Email:** [developer contact email]
- **Website:** [privacy policy URL to be hosted]

---

*This privacy policy is designed to be hosted at a public URL and referenced in App Store Connect, the QRChat Settings screen, and Info.plist.*
