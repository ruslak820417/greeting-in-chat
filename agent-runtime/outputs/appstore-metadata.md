# QRChat — App Store Metadata (v4.0)

## App Name
QRChat — Encrypted Messenger

## Subtitle (30 chars max)
`Private. Encrypted. Yours.` (26 chars)

## Category
- Primary: **Social Networking**
- Secondary: **Utilities**

## Price
Free (with QRChat Unlimited in-app purchase / promo codes)

## Privacy Policy URL
https://exciting-success-production-d272.up.railway.app/privacy

## Age Rating / Content Rating
17+ (Frequent/Intense: User Generated Content — unrestricted peer-to-peer messaging)

---

## Description (English, 4000 chars max)

```
QRChat is a truly private messenger where your conversations stay yours — always.

ZERO data collection. ZERO tracking. ZERO cloud storage.

How it works:
1. Meet someone in person
2. Scan each other's QR code
3. Start chatting with military-grade encryption

Every message, photo, voice note, and call is end-to-end encrypted using NaCl (Networking and Cryptography library). Not even we can read your messages — because we never see them.

KEY FEATURES:

-- End-to-End Encrypted Messages
Text, images, audio, video, and files. All encrypted before leaving your device using TweetNaCl cryptography.

-- QR Code Contact Exchange
No phone number. No email. No account. Just scan a QR code in person to add a contact. Share your QR code via AirDrop, WhatsApp, email, or save it to Photos for remote exchange.

-- Voice & Video Calls
Peer-to-peer WebRTC calls. Encrypted. Direct. No middleman. With CallKit integration for native iOS call experience.

-- Voice Messages
Record, preview, and send encrypted voice notes with real-time duration and waveform display.

-- Self-Destructing Messages
Set a timer and messages disappear automatically. Live countdown displayed on message bubbles. Default timer configurable in Settings.

-- Zero Server Storage
Our relay server temporarily holds encrypted messages for offline delivery (max 48 hours), then deletes them. We cannot decrypt them.

-- No Registration Required
No phone number, no email, no account creation. Your identity is a cryptographic key pair generated on your device and stored in the iOS Keychain.

-- 4 Visual Themes
QRChat, Cipher, Vault, Ghost. Pick the look that fits your style. Light and dark mode support.

-- Multi-Language Support
Available in 4 languages: English, Romanian, Russian, and French. Auto-detects your device language on first launch.

-- Group Chats
Create encrypted group conversations. All group messages are end-to-end encrypted with the same security as direct messages.

-- Reply & Forward
Reply to any message type. Forward messages to other contacts with full encryption.

-- Read Receipts
See when your message was delivered and read.

-- Contact Approval
New contacts require mutual approval. Nobody can message you without your consent.

-- Multi-Select Messages
Long press to select multiple messages, then forward or bulk delete.

-- Encrypted Local Storage
Your message database is encrypted with SQLCipher (AES-256). Private keys are stored in the iOS Keychain with Secure Enclave protection.

PRIVACY BY DESIGN:
- No analytics SDKs
- No crash reporting
- No advertising frameworks
- No phone number or email required
- No contact list upload
- No location tracking
- Open-source NaCl cryptography

QRChat is for people who believe privacy is a right, not a feature.
```

Character count: ~2,100 (well within 4,000 limit)

---

## Keywords (100 chars max, comma separated)
```
private,messenger,encrypted,e2e,qr,secure,chat,calls,privacy,anonymous,secret,crypto
```
Character count: 83

---

## What's New (for version 4.0)

```
Version 4.0 — Security & Stability Release

- Enhanced server authentication and anti-spoofing protection
- Private keys now exclusively stored in iOS Keychain (Secure Enclave)
- SQLCipher database encryption (AES-256)
- Improved WebRTC connection reliability with ICE restart
- Accessibility labels across all screens (VoiceOver support)
- Fixed TypeScript errors and improved code stability
- Performance and memory optimizations
```

---

## Review Notes for Apple

```
QRChat requires two physical devices to test, as contacts are exchanged via QR code scanning in person. Alternatively, you can share a QR code as an image and import it on the second device.

Testing steps:
1. Install QRChat on two iPhones
2. Open the app on both devices — each generates a unique QR code
3. On Device A, tap the QR scanner icon (top-right) and scan Device B's QR code
4. Device B receives a contact request notification — tap "Accept"
5. Both devices now show each other as contacts
6. Tap on a contact to open the chat — send text, photos, audio, or files
7. To test calls: tap the phone or video icon in the chat header

Alternative remote setup:
1. On Device A, go to your profile and tap "Share QR Code"
2. Save the QR image or send it via AirDrop/email to Device B
3. On Device B, tap the QR scanner and select "Import from Gallery"
4. Select the QR image — contact request is sent automatically

Important notes:
- No login/registration is required — the app generates cryptographic keys on first launch
- All communication is end-to-end encrypted
- The relay server only temporarily stores encrypted messages for offline delivery (48h max)
- The app requires camera access for QR scanning, microphone for voice features, and photo library for sending/saving images
- Uses non-exempt encryption (TweetNaCl/NaCl, SQLCipher) — ITSAppUsesNonExemptEncryption is set to YES

Demo credentials: Not applicable — QRChat has no login system.
```

---

## Content Rating Questionnaire Answers

| Question | Answer |
|----------|--------|
| Made for Kids | No |
| Cartoon or Fantasy Violence | None |
| Realistic Violence | None |
| Prolonged Graphic or Sadistic Realistic Violence | None |
| Profanity or Crude Humor | None |
| Mature/Suggestive Themes | Infrequent/Mild |
| Horror/Fear Themes | None |
| Medical/Treatment Information | None |
| Simulated Gambling | None |
| Real Gambling | None |
| Contests | None |
| Alcohol, Tobacco, or Drug Use or References | None |
| Sexual Content or Nudity | None |
| Unrestricted Web Access | No |
| Frequent/Intense — User Generated Content | Yes (users can exchange messages and media, but only with mutually approved contacts) |

**Recommended Rating:** 17+ (Frequent/Intense User Generated Content)

**Rationale:** QRChat allows unrestricted peer-to-peer messaging including text, photos, files, and voice/video calls. While contacts require mutual QR-code-based approval (preventing unsolicited messages from strangers), the content exchanged between approved contacts is unmoderated and end-to-end encrypted. Apple rates apps with unmoderated UGC as 17+. This is consistent with other E2E encrypted messengers (Signal, Wickr).

---

## Localization Status

| Language | App UI | App Store Description |
|----------|--------|----------------------|
| English (en) | Complete | Complete (primary) |
| Romanian (ro) | Complete | TODO |
| Russian (ru) | Complete | TODO |
| French (fr) | Complete | TODO |

---

## Screenshots Plan

See `screenshot-plan.md` for detailed screenshot specifications.

Required screenshots:
1. Chat conversation (showing encrypted messages, bubbles, read receipts)
2. QR code screen (showing your QR code for scanning)
3. Contact list with approved contacts
4. Voice/video call screen
5. Profile screen with avatar
6. Theme showcase (optional — showing QRChat, Cipher, Vault, Ghost themes)

Required device sizes:
- iPhone 6.9" (1320x2868) — iPhone 16 Pro Max
- iPhone 6.7" (1290x2796) — iPhone 15 Pro Max
- iPhone 6.5" (1284x2778) — iPhone 14 Pro Max
- iPad Pro 12.9" (2048x2732) — if supporting iPad

---

## Encryption Export Compliance

- **Uses encryption:** Yes
- **Encryption type:** TweetNaCl (NaCl/libsodium derivative) for E2E message encryption; SQLCipher (AES-256) for local database encryption
- **Is it exempt?** Must verify — NaCl uses Curve25519, XSalsa20, Poly1305. Standard exemption (ECCN 5D002) may apply for messaging apps with standard encryption.
- **Action required:** File an encryption self-classification report with BIS (U.S. Bureau of Industry and Security) annually, or confirm exemption under Note 4 to Category 5, Part 2.
- **ITSAppUsesNonExemptEncryption:** Currently set to `YES` in Info.plist
