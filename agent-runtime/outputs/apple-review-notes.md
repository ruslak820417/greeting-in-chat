# QRChat — Apple Review Notes

## Demo Account

**Not applicable.** QRChat has no login, registration, or account system. The app generates a cryptographic keypair on first launch — this IS the user's identity.

## How to Test QRChat

QRChat is a peer-to-peer encrypted messenger. Testing requires **two devices** (or one device + Simulator).

### Setup (both devices)

1. Install QRChat on Device A and Device B
2. Launch the app — each device automatically generates a unique QR code identity
3. No sign-up, no credentials, no configuration needed

### Adding a Contact

**Option A — In-person QR scan (recommended):**
1. On Device A, tap the QR scanner icon (top-right corner)
2. Point the camera at Device B's QR code (shown on the main screen)
3. Device B receives a contact request notification — tap "Accept"
4. Both devices now show each other as contacts

**Option B — Remote QR share:**
1. On Device A, go to Profile and tap "Share QR Code"
2. Save the QR image or send via AirDrop/email to Device B
3. On Device B, tap the QR scanner icon, then "Import from Gallery"
4. Select the QR image — contact request is sent automatically
5. Device A accepts the request

### Testing Core Features

| Feature | Steps |
|---------|-------|
| **Send text** | Open a contact chat, type a message, tap Send |
| **Send photo** | Tap camera/gallery icon, select or take a photo |
| **Voice message** | Hold the microphone button, speak, release to send |
| **Voice call** | In chat header, tap the phone icon |
| **Video call** | In chat header, tap the video icon |
| **Self-destruct** | In chat settings, enable self-destruct timer |
| **Group chat** | From contacts list, tap "New Group", select members |
| **Theme switch** | Settings > Appearance > toggle Light/Dark |
| **Language** | Settings > Language > select from 4 options |

### Important Technical Notes

- **P2P Architecture:** Messages are end-to-end encrypted. The relay server temporarily holds encrypted messages for offline delivery (max 48 hours) but CANNOT decrypt them.
- **No server-side content:** There is no server dashboard, admin panel, or way to view message content on the server side.
- **Encryption:** Uses TweetNaCl (NaCl) cryptography — X25519 key exchange, XSalsa20-Poly1305 authenticated encryption, Ed25519 signatures. Local database encrypted with SQLCipher (AES-256).
- **Non-exempt encryption:** ITSAppUsesNonExemptEncryption is set to YES in Info.plist.
- **Required permissions:** Camera (QR scanning + video calls), Microphone (voice messages + calls), Photo Library (send/save images), Contacts (optional, for discovery).
- **No analytics:** Zero third-party analytics, crash reporting, or advertising SDKs.

### Screenshots Flow

1. **Launch** — QR code identity screen (main screen)
2. **Scan QR** — Camera viewfinder scanning a QR code
3. **Contact request** — Notification + accept/decline
4. **Chat** — Encrypted message conversation with bubbles
5. **Call** — Active voice/video call screen
6. **Settings** — Profile, themes, language options
