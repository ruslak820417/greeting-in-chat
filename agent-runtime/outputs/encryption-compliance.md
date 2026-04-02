# QRChat — Encryption Export Compliance Report

## App Information
- **App Name:** QRChat
- **Bundle ID:** com.ruslanconstantinovici.QRChat
- **Version:** 4.0.0
- **Date:** 2026-03-21

## Encryption Declaration

QRChat uses **non-exempt encryption** as defined by U.S. Bureau of Industry and Security (BIS) export regulations.

### ITSAppUsesNonExemptEncryption: YES

The app implements custom end-to-end encryption for user communication and local data storage. This is NOT limited to standard OS-provided encryption (HTTPS/TLS).

## Cryptographic Algorithms Used

| Algorithm | Library | Purpose | Key Size |
|-----------|---------|---------|----------|
| X25519 (Curve25519) | TweetNaCl | Key exchange / Diffie-Hellman | 256-bit |
| XSalsa20-Poly1305 | TweetNaCl | Authenticated symmetric encryption (messages) | 256-bit key + 192-bit nonce |
| Ed25519 | TweetNaCl | Digital signatures (identity verification) | 256-bit |
| AES-256-CBC | SQLCipher | Local database encryption | 256-bit |
| SHA-512 | TweetNaCl (internal) | Hashing (key derivation) | 512-bit |

## Purpose of Encryption

1. **User Authentication** — Ed25519 keypairs are used for identity verification. Each user generates a cryptographic identity on-device, stored in iOS Keychain with Secure Enclave protection.

2. **Data Confidentiality** — All messages, files, photos, voice notes, and calls are encrypted end-to-end using NaCl's `crypto_box` (X25519 + XSalsa20-Poly1305) before transmission. The relay server cannot decrypt any content.

3. **Local Storage Protection** — The SQLite message database is encrypted at rest using SQLCipher (AES-256).

## NOT Used For

- Government use or government contracts
- Military applications
- Mass surveillance
- Circumvention of content restrictions
- Financial transactions or DRM

## Export Classification

- **ECCN:** 5D002 — Information Security software using encryption
- **License Exception:** ENC (Section 740.17(b)(1)) — Mass-market encryption software available to the general public via app store download
- **Annual Self-Classification Report:** Required to be filed with BIS (Commerce Department) and ENC Encryption Request Coordinator (NSA) by February 1 of each year

## Compliance Steps for Apple Submission

1. In App Store Connect > App Information > Export Compliance:
   - "Does your app use encryption?" -> **Yes**
   - "Does your app qualify for any exemptions?" -> **No** (custom E2E encryption beyond HTTPS)
   - "Does your app implement any encryption algorithms not listed as exempt?" -> **Yes**
   - Upload or reference this compliance document

2. Info.plist keys set:
   ```xml
   <key>ITSAppUsesNonExemptEncryption</key>
   <true/>
   <key>ITSEncryptionExportComplianceCode</key>
   <string></string>
   ```

3. File annual self-classification report with BIS if required under EAR Section 742.15(b).

## Declaration

QRChat's encryption is used solely for the purpose of protecting user privacy in peer-to-peer communication. The cryptographic libraries used (TweetNaCl, SQLCipher) are open-source and publicly available. The app is distributed as mass-market software through the Apple App Store.
