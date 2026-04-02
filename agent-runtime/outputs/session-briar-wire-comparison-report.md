# Privacy Messenger Comparison Report: Session, Briar, Wire vs QRChat

**Date:** 24 March 2026
**Author:** Research Agent (Claude Opus 4.6)
**QRChat Version:** 4.0.0 (build 16)
**Purpose:** Identify features, security patterns, and UX ideas QRChat can adopt from three leading open-source privacy messengers.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Session Messenger -- Deep Dive](#2-session-messenger)
3. [Briar Messenger -- Deep Dive](#3-briar-messenger)
4. [Wire Messenger -- Deep Dive](#4-wire-messenger)
5. [Feature-by-Feature Comparison Matrix](#5-comparison-matrix)
6. [What QRChat Already Does Well](#6-qrchat-strengths)
7. [Recommendations for QRChat](#7-recommendations)
8. [Implementation Priority Roadmap](#8-roadmap)

---

## 1. Executive Summary

QRChat occupies a unique position in the encrypted messenger landscape. Its QR-code-based contact exchange (no phone number, no email) is shared only by Briar among major messengers. Its use of TweetNaCl (X25519 + XSalsa20-Poly1305 + Ed25519) with Double Ratchet forward secrecy puts it on solid cryptographic ground. However, all three competitors offer features QRChat could adopt to become more compelling.

**Key takeaways:**
- **From Session:** Decentralized message storage (swarms), onion routing for metadata protection, disappearing messages with two modes, Session ID model (very similar to QRChat's approach)
- **From Briar:** Offline mesh networking (Bluetooth/WiFi), mutual QR verification protocol, forums/blogs/RSS, Mailbox for asynchronous delivery
- **From Wire:** MLS protocol for scalable group encryption, guest room links for external users, conference calls (up to 150 participants), automatic device verification (ID Shield), file encryption with AES-256

---

## 2. Session Messenger

**Repository:** github.com/session-foundation (formerly oxen-io/session-ios, now deprecated)
**License:** GPL-3.0
**Platform:** iOS, Android, Desktop (Electron)
**Fork of:** Signal (originally "Loki Messenger")

### 2.1 Identity System (No Phone Number)

Session generates an Ed25519 key pair on-device. The public key (converted to X25519) becomes the user's **Session ID** -- a 66-character hex string (e.g., `05...`). This is conceptually identical to QRChat's approach.

- No phone number, no email, no registration server
- Key pairs generated in seconds on-device
- Pseudonymous unless the user self-doxxes out-of-band
- Account recovery via mnemonic seed phrase (13 words)

**QRChat comparison:** QRChat does essentially the same thing with its KeyManager generating X25519 keypairs. The difference is Session gives users a mnemonic seed for backup, while QRChat stores keys in iOS Keychain with WHEN_UNLOCKED_THIS_DEVICE_ONLY.

**Recommendation:** Add mnemonic seed phrase backup to QRChat. This enables account migration between devices without needing a server.

### 2.2 Onion Routing (Lokinet / Session Network)

All messages are wrapped in 3 layers of encryption and routed through a 3-node path:

```
Sender -> Guard Node -> Service Node -> Exit Node -> Recipient's Swarm
```

Each node decrypts one layer and knows only the previous and next hop. No single node knows both sender and recipient.

In 2025, Session migrated from the Oxen blockchain to its own **Session Network** with staking via the $SESSION token.

**QRChat comparison:** QRChat routes messages through a central WebSocket relay server (Railway), which knows both sender and recipient IP addresses. QRChat's WebRTC P2P mode exposes IP addresses to the peer.

**Recommendation:** This is the single biggest architectural gap. QRChat should consider:
1. Short-term: Add a configurable relay/proxy option so the server does not see direct client IPs
2. Medium-term: Investigate Tor integration (like Briar does) for metadata protection
3. Long-term: Consider a multi-hop relay architecture

### 2.3 Decentralized Message Storage (Swarms)

Messages are stored in **swarms** of 5-7 Session Nodes:
- Each Account ID maps to a specific swarm (deterministic via DHT)
- Messages replicated across all nodes in the swarm for redundancy
- Messages have a TTL (time-to-live) and auto-delete after expiry
- Recipient retrieves messages via onion routing when coming online
- Messages deleted from nodes after retrieval

**QRChat comparison:** QRChat uses a centralized server with a pending message queue (max 1000 messages / 50MB per user). If the server goes down, messages are lost.

**Recommendation:** QRChat's DHT infrastructure (DHTManager.ts, BootstrapManager.ts) is already partially built. Consider extending it to store encrypted message blobs across multiple peers, creating a simple swarm-like redundancy system.

### 2.4 Group Chats (Closed Groups with Sender Keys)

**Closed Groups (up to 100 members):**
- Group creator generates a shared Ed25519 keypair
- Shared key distributed to members via pairwise 1-to-1 encrypted channels
- Messages encrypted with shared symmetric key, signed with sender's identity key
- When a member leaves/is kicked, new shared key is generated and redistributed
- Stored on decentralized network (no central server)

**Open Groups / Communities (unlimited members):**
- Hosted on Session Open Group Server (SOGS, written in Python)
- Messages encrypted in transit but NOT end-to-end encrypted (server can read)
- Self-hostable by anyone
- Good for public communities

**QRChat comparison:** QRChat has CreateGroupScreen.tsx and GroupInfoScreen.tsx but the group encryption mechanism is not documented in the project status. No open group / community feature exists.

**Recommendation:** Implement Sender Keys protocol for group chats (the same approach WhatsApp uses). For groups >100, consider a community/channel mode similar to SOGS.

### 2.5 Voice/Video Calls

- Uses WebRTC (DTLS + SRTP encryption)
- **Peer-to-peer** connections (not routed through onion network)
- Beta feature, opt-in only (off by default)
- Both participants must enable calls in settings AND be mutual contacts
- **IP addresses exposed** to peer and STUN/TURN server (operated by Session Foundation)
- No group calls yet
- Onion-routed calls via Lokinet (UDP support) are planned but not yet shipped

**QRChat comparison:** QRChat already has WebRTC calls with WebRTCManager.ts, CallKit integration, DTLS/SRTP, and even a glare-fix (Perfect Negotiation pattern). QRChat is ahead of Session in call stability features (45s timeout, reconnection backoff, stale call cleanup).

**Recommendation:** QRChat's call implementation is more mature than Session's beta. Consider making calls opt-in by default (like Session) for privacy-conscious users, with a clear disclosure about IP exposure.

### 2.6 File Attachments

- Files symmetrically encrypted on-device before upload
- Uploaded to Session File Server (centralized, run by Session Foundation)
- Encrypted message sent to recipient containing: download URL + decryption key
- File server cannot see file contents or metadata
- Upload/download through onion routing (IP hidden)
- Currently centralized; future plans for self-hosted file servers

**QRChat comparison:** QRChat has file transfer with progress tracking and chunk-based delivery. The current implementation uses WebRTC data channels or server relay.

**Recommendation:** Adopt Session's model for large files: encrypt locally with AES-256, upload to a storage service, send only the URL + key via the encrypted channel. This is more efficient than chunking large files through WebRTC.

### 2.7 Disappearing Messages

Two modes:
1. **Disappear after Send:** Timer starts when message is sent. Deleted from all devices and network at expiry.
2. **Disappear after Read:** Timer starts when recipient reads the message. Deleted from sender's side at send-time expiry, from recipient's side at read-time expiry.

**QRChat comparison:** No disappearing messages feature exists in QRChat.

**Recommendation:** Implement disappearing messages with both modes. This is a must-have for a privacy messenger and is expected by users.

### 2.8 Multi-Device

- **Currently broken/removed** due to too many bugs
- Original approach: shared Long-Term Key across devices
- Planned V2: per-device keys + per-account rotating keys + Config Messages sync
- No ETA for V2

**QRChat comparison:** QRChat has no multi-device support, which is actually fine -- Session tried it and failed badly.

**Recommendation:** Do not prioritize multi-device. Even Session could not get it right. Focus on making the single-device experience excellent. If ever implemented, use Wire's approach (per-device keys, up to 8 devices).

### 2.9 Encryption: Session Protocol vs Signal Protocol vs QRChat

| Property | Signal Protocol | Session Protocol V1 | QRChat (TweetNaCl + DR) |
|----------|----------------|--------------------|-----------------------|
| Forward Secrecy | Yes (Double Ratchet) | No (removed) | Yes (Double Ratchet) |
| Post-Compromise Security | Yes | No | Depends on DR impl |
| Deniability | Yes | No | Depends on impl |
| Encryption Algo | AES-256-CBC | XSalsa20 / AES-GCM (libsodium) | XSalsa20-Poly1305 (TweetNaCl) |
| Key Exchange | X3DH | ECDH (X25519) | X25519 DH |
| Signing | Ed25519 | Ed25519 | Ed25519 |
| Complexity | ~5000 lines | ~50 lines | Medium |
| Audit Status | Formally verified | Not yet audited | Not audited |

**Key insight:** Session deliberately sacrificed Perfect Forward Secrecy (PFS) for simplicity, arguing that PFS only matters when long-term keys are compromised -- which requires physical device access, at which point the attacker can read the local database anyway. This is a valid argument but controversial.

**QRChat advantage:** QRChat has Double Ratchet, which is stronger than Session's current protocol. This is a legitimate selling point.

---

## 3. Briar Messenger

**Repository:** code.briarproject.org/briar/briar (GitLab)
**License:** GPL-3.0
**Platform:** Android only (Desktop in beta via NLnet funding)
**Architecture:** Pure peer-to-peer, no central server whatsoever

### 3.1 Transport Layers (Tor, WiFi, Bluetooth)

Briar is unique in supporting three independent transport layers:

1. **Tor (Internet available):** All connections routed through Tor hidden services. Users never connect directly -- each device runs a Tor hidden service. Protects metadata (who talks to whom).

2. **Bluetooth (No Internet):** Devices sync messages when within ~10m Bluetooth range. Uses Bramble Transport Protocol over Bluetooth RFCOMM.

3. **WiFi Direct (No Internet):** Devices sync over local WiFi network. Range up to ~150m (500ft in clear conditions).

4. **Memory Cards (Extreme scenario):** Export encrypted messages to SD card, physically carry to recipient. Nuclear option for total surveillance environments.

**QRChat comparison:** QRChat uses WebRTC (P2P over internet) with WebSocket relay fallback. No offline/local transport.

**Recommendation:** Bluetooth/WiFi Direct messaging would be a killer feature for QRChat, especially given the QR code contact exchange already requires physical proximity. The flow would be: scan QR code -> exchange keys via Bluetooth -> continue messaging over Bluetooth when both nearby, internet when not.

### 3.2 QR Code Contact Exchange (Bramble QR Code Protocol)

This is the most relevant comparison for QRChat. Briar's BQP works as follows:

1. Both users open "Add Contact" simultaneously
2. Each device generates a fresh ephemeral Curve25519 keypair
3. Each device displays a QR code containing:
   - Commitment to their ephemeral public key
   - Bluetooth/WiFi transport descriptors
   - A hash binding the exchange to both parties
4. **Both users scan each other's QR code** (mutual verification)
5. Devices perform ECDH using the ephemeral keys to derive a shared master secret
6. The QR codes prove the keys were not intercepted (MITM protection)
7. Contact appears with a green verification badge

**Critical difference from QRChat:** Briar requires MUTUAL scanning (both users scan each other). QRChat only requires one-way scanning. Mutual scanning provides stronger MITM protection.

**QRChat comparison:** QRChat's QR exchange includes signPub, sig, and timestamp. One user generates, the other scans. The QR contains the Ed25519 public key + signature + timestamp for verification.

**Recommendations:**
1. Consider adding optional mutual QR scanning mode for high-security contacts
2. Add QR code expiry (Briar regenerates every time)
3. Add a visual verification badge (green checkmark) for QR-verified contacts
4. Add key re-verification flow (scan again to re-verify)

### 3.3 Bramble Protocol Suite

Briar uses five protocols, all custom-designed for delay-tolerant networking:

| Protocol | Purpose |
|----------|---------|
| BQP (QR Code Protocol) | Initial contact exchange via QR |
| BHP (Handshake Protocol) | Authenticated key exchange after QR |
| BRP (Rendezvous Protocol) | Finding each other on the network |
| BSP (Synchronisation Protocol) | Syncing messages across transports |
| BTP (Transport Protocol) | Encrypted frames over any transport |

**Encryption primitives:**
- Ed25519 for signatures
- XSalsa20-Poly1305 for authenticated encryption (same as QRChat)
- Curve25519 for key agreement (same as QRChat)
- BLAKE2 for hashing

**QRChat comparison:** QRChat uses the exact same cryptographic primitives (via TweetNaCl). The main difference is Briar has a formal protocol specification for each layer, while QRChat's protocol is implementation-defined.

**Recommendation:** Document QRChat's protocol formally. Having a spec document (like Briar's BTP.md, BQP.md etc.) would help with security audits and establishing credibility.

### 3.4 Offline Messaging (Briar Mailbox)

Briar Mailbox is a separate Android app that acts as a personal message relay:

1. Install Mailbox on a spare Android device
2. Link it to your Briar account by scanning a QR code
3. Leave the device connected to power and WiFi
4. Contacts can leave messages on your Mailbox when you are offline
5. When your main device comes online, it fetches messages from Mailbox
6. All connections via Tor, all messages encrypted

**QRChat comparison:** QRChat uses the Railway server as a message relay, which serves a similar purpose but is centralized and operated by QRChat.

**Recommendation:** This concept could inspire a self-hosted relay option for QRChat. Users could run a simple Node.js relay on a VPS or Raspberry Pi, giving them full control over their message buffer.

### 3.5 Groups, Forums, and Blogs

Briar has three distinct group communication types:

1. **Private Groups:** Encrypted group chats (like WhatsApp groups)
2. **Forums:** Semi-public threaded discussions. Anyone in a forum can invite anyone else. Messages propagate through the contact graph -- delivered to contacts when in range, who then carry them to their contacts.
3. **Blogs:** Personal feeds shared with contacts. Includes RSS reader and reblogging.

**QRChat comparison:** QRChat has basic group chat. No forums or blog features.

**Recommendation:** The forum concept (threaded, semi-public, propagates through contact graph) is unique and interesting but probably out of scope for QRChat v4. However, threaded replies within group chats would be valuable.

### 3.6 Key Agreement Without Central Server

Briar's BHP (Bramble Handshake Protocol) derives a shared master key using:

1. Both devices generate ephemeral Curve25519 keypairs
2. ECDH produces a shared secret
3. HKDF derives the master key from the shared secret
4. The QR code exchange (BQP) provides MITM protection
5. Forward secrecy via BTP key rotation

**Important limitation:** The ETH Zurich analysis notes that BHP "lacks forward security" for the initial handshake -- if long-term keys are compromised, past handshake data could be exposed. However, BTP provides forward secrecy for subsequent messages.

**QRChat comparison:** QRChat's Double Ratchet provides forward secrecy from the first message onward, which is stronger than Briar's handshake protocol.

### 3.7 Battery and Performance

Briar's always-on Bluetooth/Tor scanning drains battery approximately 4x faster than server-based messengers. This is a fundamental tradeoff of true P2P architecture.

**QRChat advantage:** By using a central relay server, QRChat avoids this problem entirely. The server handles message buffering efficiently.

---

## 4. Wire Messenger

**Repository:** github.com/wireapp/wire-ios, wire-android, wire-webapp
**License:** GPL-3.0 (clients), proprietary (server)
**Platform:** iOS, Android, Windows, macOS, Linux, Web
**Focus:** Business/enterprise secure communication

### 4.1 Proteus Protocol (Legacy) and MLS (Current)

**Proteus (Double Ratchet implementation in Rust):**
- Based on Signal Protocol / Axolotl
- Uses: ChaCha20, HMAC-SHA256, Curve25519, HKDF
- Written in Rust, cross-compiled for iOS/Android via libsodium
- Serialization via CBOR
- Suitable for 1-to-1 and small groups
- Problem: For a 400-person group, each message must be encrypted 399 times

**MLS (Messaging Layer Security, RFC 9420):**
- Wire is the FIRST messenger to deploy MLS in production
- Encrypt once, deliver to entire group
- Supports channels with up to 2,000 participants
- Supports calls with up to 150 participants
- Co-developed by Wire with IETF since 2016
- Provides Forward Secrecy AND Post-Compromise Security
- Post-quantum ready (cryptographic agility)

**QRChat comparison:** QRChat uses Double Ratchet (like Proteus) which works for 1-to-1 but will not scale for large groups. QRChat currently has no MLS-equivalent.

**Recommendation:** For QRChat v4-v5, Double Ratchet is fine (groups are small). For future scaling beyond 100 members, investigate MLS. The OpenMLS library (Rust, open-source) could be integrated via native modules.

### 4.2 Voice/Video Calls and Conferences

**1-to-1 Calls:**
- WebRTC with SRTP (Secure Real-time Transport Protocol)
- Key negotiation via DTLS handshake
- Fingerprint verification through existing Proteus/MLS session
- Standard quality

**Conference Calls (up to 150 participants):**
- Uses Selective Forwarding TURN (SFT) server
- All media encrypted with AES-GCM-256
- Key derivation via HKDF-SHA512
- Additional encryption layer via WebRTC Encoded Transforms / Insertable Streams
- SFT server cannot decrypt media content

**QRChat comparison:** QRChat has 1-to-1 WebRTC calls with DTLS/SRTP. No conference call support.

**Recommendations:**
1. Short-term: QRChat's 1-to-1 calls are solid. Add call quality indicators (signal strength, codec info).
2. Medium-term: Investigate SFU (Selective Forwarding Unit) architecture for group calls. LiveKit (open-source, Golang) or mediasoup (Node.js) are good options.
3. The double-encryption approach (SRTP + Encoded Transforms) is worth adopting for maximum security.

### 4.3 Guest Room Links

This is Wire's most unique feature and directly relevant to QRChat:

**How it works:**
1. Team member creates a guest room (group conversation)
2. Wire generates a shareable link (URL)
3. External users click the link
4. They can join **in a browser without downloading anything or creating an account**
5. All communication is still end-to-end encrypted
6. Guests without Wire accounts cannot share files and are auto-removed after 24h
7. A "GUESTS ARE PRESENT" banner warns team members
8. Link can be revoked at any time

**QRChat comparison:** QRChat requires QR code scanning for contact exchange (physical proximity). There is an InviteLinkCrypto.ts suggesting some invite link work has begun.

**Recommendation:** This is a HIGH-PRIORITY feature for QRChat growth:
1. Generate encrypted invite links that can be shared via any channel (SMS, email, other messengers)
2. Link contains: encrypted public key + one-time verification token + expiry timestamp
3. Recipient clicks link -> opens QRChat -> automatic key exchange (like QR scanning but remote)
4. Consider a web-based "lite mode" where recipients can chat from a browser without installing the app
5. Add link expiry and revocation capabilities

### 4.4 File Sharing

- Files encrypted with random AES-256 keys before upload
- Asset keys distributed via the encrypted messaging channel (Proteus/MLS)
- Files stored server-side but server cannot decrypt (no access to asset keys)
- Wire stores conversation history locally on device
- Supports any file type

**QRChat comparison:** QRChat has file transfer with progress tracking. The chunking approach works but may be inefficient for large files.

**Recommendation:** Adopt the "encrypt-upload-share-key" pattern for files >1MB. Use AES-256-GCM for file encryption, upload to a configurable storage backend (S3, Firebase Storage, or self-hosted), and send only the URL + decryption key through the encrypted channel.

### 4.5 Multi-Device (Up to 8 Devices)

Wire supports up to 8 simultaneous devices per account:
- Each device has its own keypair
- Messages encrypted separately for each device (Proteus) or group-delivered (MLS)
- Conversation history synced across all platforms
- New device alerts sent to contacts

**QRChat comparison:** Single device only.

**Recommendation:** Wire's multi-device approach is the gold standard. If QRChat ever implements multi-device, follow Wire's model: per-device keys, device list management, and new-device notifications to contacts.

### 4.6 ID Shield (Automatic Device Verification)

- Available on Wire Enterprise (on-premises/private cloud)
- Each device gets an X.509 certificate via automated enrollment
- Certificates regularly renewed
- Verification is automatic (no manual fingerprint comparison)
- Compromised device certificates can be revoked
- Verified contacts show a verification badge

**QRChat comparison:** QRChat verifies contacts at QR-scan time (signPub + sig + timestamp). No ongoing verification.

**Recommendation:** Add a "safety number" or verification code feature (like Signal) that changes when a contact's keys change. Alert users when a contact's key changes (potential MITM attack or device change).

### 4.7 Certifications and Audits

- ISO 27001 and ISO 27701 certified
- Cyber Essentials certified (UK government)
- External audit by Kudelski Security and X41 D-Sec
- Servers in Germany and Ireland (GDPR jurisdiction)
- Open-source clients on GitHub

**QRChat comparison:** No audits, no certifications.

**Recommendation:** Before or shortly after App Store launch, consider commissioning a security audit of the crypto layer (DoubleRatchet.ts, KeyManager.ts, RatchetStore.ts). Even a limited-scope audit by a single researcher would add credibility. Open-sourcing the crypto layer would also allow community review.

---

## 5. Feature-by-Feature Comparison Matrix

| Feature | Session | Briar | Wire | QRChat |
|---------|---------|-------|------|--------|
| **Identity** | Session ID (Ed25519) | Bramble ID | Email/phone | QR-exchanged X25519 key |
| **Registration** | None | None | Email required | None (QR only) |
| **E2E Encryption** | Session Protocol (libsodium) | Bramble (XSalsa20-Poly1305) | Proteus/MLS | TweetNaCl + Double Ratchet |
| **Forward Secrecy** | No (planned V2) | Partial (BTP rotation) | Yes (Double Ratchet + MLS) | Yes (Double Ratchet) |
| **Post-Quantum** | Planned (ML-KEM) | No | Planned (MLS agility) | No |
| **Metadata Protection** | Onion routing (3 hops) | Tor hidden services | Minimal (central server) | None (central server) |
| **Message Storage** | Decentralized swarms (5-7 nodes) | On-device only + Mailbox | Central server | Central server (Railway) |
| **Offline Transport** | No | Bluetooth, WiFi, memory card | No | No |
| **Contact Exchange** | Share Session ID (text) | Mutual QR scan | Email/username search | One-way QR scan |
| **Group Chat** | 100 (Sender Keys) | Yes (private + forums) | 2,000 (MLS) | Basic groups |
| **Voice Calls** | Beta (WebRTC P2P) | No | Yes (WebRTC + SFU) | Yes (WebRTC P2P) |
| **Video Calls** | Beta (WebRTC P2P) | No | Yes (up to 150) | Yes (WebRTC P2P) |
| **Conference Calls** | No | No | Yes (150 participants) | No |
| **File Transfer** | Encrypted upload + key sharing | Sync between devices | AES-256 + key sharing | Chunked transfer |
| **Disappearing Messages** | Yes (2 modes) | No | Yes (timer) | No |
| **Multi-Device** | Removed (too buggy) | No (Android only) | Yes (8 devices) | No |
| **Guest/Invite Links** | No | No | Yes (browser access) | InviteLinkCrypto.ts (WIP) |
| **Platforms** | iOS, Android, Desktop | Android (Desktop beta) | iOS, Android, Desktop, Web | iOS, Android |
| **Open Source** | Yes (GPL-3) | Yes (GPL-3) | Clients only (GPL-3) | Not yet |
| **Security Audit** | Not yet | ETH Zurich analysis | Kudelski + X41 audit | No |
| **Battery Impact** | Normal | High (4x normal) | Normal | Normal |

---

## 6. What QRChat Already Does Well

QRChat should not underestimate its existing strengths:

### 6.1 Cryptographic Foundation
- **TweetNaCl (X25519 + XSalsa20-Poly1305 + Ed25519):** The same primitives used by Briar. Battle-tested, well-audited library.
- **Double Ratchet:** Stronger than Session's current protocol (which lacks PFS). On par with Wire's Proteus.
- **SQLCipher encryption:** Database encryption at rest -- not all competitors do this client-side.
- **Keychain storage with WHEN_UNLOCKED_THIS_DEVICE_ONLY:** Strongest iOS key protection level.

### 6.2 QR Code Contact Exchange
- No phone number, no email, no registration -- just like Session and Briar
- Simpler than Briar (one-way scan vs. mutual scan), while still including signature verification
- The QR includes Ed25519 signature + timestamp for anti-replay

### 6.3 Call Infrastructure
- More mature than Session's beta calls
- WebRTC with Perfect Negotiation (glare fix) -- a sophisticated implementation
- CallKit integration for native iOS call experience
- 45-second timeout, reconnection backoff, stale call cleanup
- Call log with redesigned UI

### 6.4 UI/UX Polish
- WhatsApp/Telegram-inspired chat design (bubbles, swipe-to-reply, album grouping)
- Two themes (Light orange + Dark teal)
- 4-language i18n (EN/RO/RU/FR)
- Accessibility labels on all 19+ screens
- Photo viewer with swipe navigation

### 6.5 Security Hardening
- 9 security fixes already implemented (sender spoofing, admin secret, rate limiting, etc.)
- Server input validation with type whitelist
- Pending message queue limits (anti-DoS)
- Error Boundary for crash resilience

### 6.6 Unique Position
QRChat is the only messenger that combines:
- QR-based contact exchange (like Briar)
- No registration (like Session)
- Double Ratchet forward secrecy (like Signal/Wire)
- WebRTC voice/video calls (better than Session's beta)
- Clean, modern UI (better than both Briar and Session)
- React Native cross-platform (faster iteration than native-only)

---

## 7. Recommendations for QRChat

### TIER 1 -- High Impact, Moderate Effort (v4.x)

#### 7.1 Disappearing Messages
**Inspired by:** Session (2 modes), Wire (timer)
**Implementation:**
- Add per-conversation "Disappear after Send" and "Disappear after Read" options
- Timer options: 5s, 30s, 1m, 5m, 1h, 12h, 24h, 7d
- Use SQLite triggers or background task to purge expired messages
- Show disappearing message indicator in chat UI (clock icon on bubble)
- Estimated effort: 2-3 days

#### 7.2 Invite Links (Remote Key Exchange)
**Inspired by:** Wire (guest rooms)
**Implementation:**
- Generate a one-time invite link containing: encrypted public key, one-time token, expiry (24h)
- Use InviteLinkCrypto.ts (already exists) as foundation
- Recipient clicks link -> opens QRChat -> performs DH key exchange via server relay
- Less secure than QR (no physical verification) but enables remote contact addition
- Show "Invite Link" badge vs "QR Verified" badge to distinguish trust levels
- Estimated effort: 3-5 days

#### 7.3 Key Change Notifications
**Inspired by:** Wire (ID Shield), Signal (safety numbers)
**Implementation:**
- Generate a "safety number" from both parties' public keys
- Display in contact profile for manual verification
- Alert user when a contact's key changes (new device, reinstall)
- "This contact's security code has changed" warning banner
- Estimated effort: 1-2 days

#### 7.4 Contact Verification Badge
**Inspired by:** Briar (green circle), Wire (verified shield)
**Implementation:**
- QR-verified contacts get a green checkmark badge
- Invite-link contacts get a yellow badge (lower trust)
- Unverified key-change contacts get a red warning
- Badge visible in contact list, chat header, and contact profile
- Estimated effort: 1 day

#### 7.5 Large File Encryption and Upload
**Inspired by:** Session (encrypt + upload + share key), Wire (AES-256 + upload)
**Implementation:**
- For files >1MB: encrypt with AES-256-GCM using random key
- Upload encrypted blob to Firebase Storage or S3
- Send download URL + decryption key via encrypted chat
- Recipient downloads and decrypts locally
- Show upload/download progress bar
- Estimated effort: 3-4 days

### TIER 2 -- High Impact, Higher Effort (v5.x)

#### 7.6 Sender Keys for Group Encryption
**Inspired by:** Session (closed groups), WhatsApp (Sender Keys)
**Implementation:**
- Group creator generates symmetric group key
- Distribute key to members via pairwise Double Ratchet channels
- Messages encrypted once with group key, delivered to all members
- Rotate key when member leaves/joins
- Much more efficient than individual encryption per member
- Estimated effort: 1-2 weeks

#### 7.7 Mutual QR Verification Mode
**Inspired by:** Briar (BQP protocol)
**Implementation:**
- Add "High Security" contact exchange option
- Both users must scan each other's QR code
- Use ephemeral keys in QR (not long-term keys)
- Derive shared secret from both ephemeral keys via ECDH
- Provides stronger MITM protection than one-way scan
- Estimated effort: 3-5 days

#### 7.8 Group Voice Calls
**Inspired by:** Wire (SFU architecture, 150 participants)
**Implementation:**
- Deploy a Selective Forwarding Unit (mediasoup for Node.js or LiveKit)
- Each participant sends one stream to SFU, receives N-1 streams
- E2E encrypt media with per-call AES-GCM key distributed via group channel
- Use WebRTC Encoded Transforms for double encryption
- Start with 4-8 participants, scale later
- Estimated effort: 2-4 weeks

#### 7.9 Tor Integration for Metadata Protection
**Inspired by:** Briar (Tor hidden services), Session (onion routing)
**Implementation:**
- Integrate Arti (Tor in Rust) or use OrBot as a proxy on Android
- Route WebSocket connections through Tor
- Hide user IP from relay server
- Add toggle: "Route through Tor" in privacy settings
- Tradeoff: Higher latency, no real-time calls through Tor
- Estimated effort: 2-3 weeks

### TIER 3 -- Innovative, Long-Term (v6+)

#### 7.10 Bluetooth/WiFi Direct Messaging
**Inspired by:** Briar (mesh networking)
**Implementation:**
- Use React Native BLE (Bluetooth Low Energy) library
- When two QRChat contacts are nearby, establish BLE connection
- Sync messages over BLE when internet is unavailable
- Use MultipeerConnectivity framework on iOS for WiFi Direct
- Natural extension of QR code exchange (users are already physically close)
- Estimated effort: 4-6 weeks

#### 7.11 Self-Hosted Relay Option
**Inspired by:** Briar Mailbox, Session SOGS
**Implementation:**
- Publish QRChat relay server as a Docker image
- Users can run their own relay on VPS/Raspberry Pi
- App setting to configure custom relay URL
- Federated architecture: multiple relays can interconnect
- Estimated effort: 2-3 weeks

#### 7.12 Post-Quantum Key Exchange
**Inspired by:** Session V2 (ML-KEM), Wire MLS (crypto agility)
**Implementation:**
- Add ML-KEM (Kyber) key encapsulation alongside X25519
- Hybrid approach: X25519 + ML-KEM (same as Signal's PQXDH)
- Protects against "harvest now, decrypt later" quantum attacks
- Use liboqs (Open Quantum Safe) via native module
- Estimated effort: 2-4 weeks

#### 7.13 Protocol Documentation and Security Audit
**Inspired by:** Briar (formal specs), Wire (ISO certs + external audits)
**Implementation:**
- Write formal protocol specification for QRChat's key exchange, Double Ratchet usage, and message format
- Open-source the crypto layer (crypto/, Double Ratchet, KeyManager)
- Commission external audit (budget: $5K-$15K for focused crypto review)
- Publish audit results and protocol spec on website
- Estimated effort: 2-4 weeks for docs, audit timeline varies

---

## 8. Implementation Priority Roadmap

### Phase 1: Pre-Launch Essentials (v4.1-4.2, 1-2 weeks)
1. Disappearing messages (2 modes)
2. Key change notifications
3. Contact verification badges (QR-verified vs invite-link)
4. Protocol documentation (informal but thorough)

### Phase 2: Growth Features (v4.3-4.5, 2-4 weeks)
5. Invite links (remote contact addition)
6. Large file encryption + cloud upload
7. Sender Keys for group chat encryption
8. Mutual QR verification mode (high-security option)

### Phase 3: Competitive Differentiators (v5.0, 1-2 months)
9. Group voice calls (SFU-based)
10. Tor routing option
11. Self-hosted relay Docker image
12. Threaded replies in group chats

### Phase 4: Next-Generation (v6.0, 3-6 months)
13. Bluetooth/WiFi Direct offline messaging
14. Post-quantum hybrid key exchange
15. Formal security audit
16. MLS protocol for large groups (1000+)

---

## Sources

### Session Messenger
- [Session FAQ](https://getsession.org/faq)
- [Session Protocol Technical Information](https://getsession.org/session-protocol-technical-information)
- [Session Protocol Explained](https://getsession.org/session-protocol-explained)
- [Session Account IDs and Self-Managed Keys](https://docs.getsession.org/session-network/session-protocol/account-ids-and-self-managed-keys)
- [Session Swarms Documentation](https://docs.getsession.org/session-network/session-nodes/swarms)
- [Session Communities Documentation](https://docs.getsession.org/session-messenger/advanced-features/communities)
- [Session Calls Beta Release](https://getsession.org/blog/calls-beta-release)
- [Session Calls -- How to Opt-In](https://getsession.org/blog/calls-on-session-how-to-opt-in)
- [No Caller ID: Calls on Session](https://getsession.org/blog/calls-on-session)
- [Session Disappearing Messages V2](https://getsession.org/disappearing-messages-v2-a-new-way-to-protect-your-privacy-with-session)
- [Future of Session Multi-Device](https://getsession.org/future-of-multi-device)
- [Session and Lokinet -- Oxen](https://oxen.io/session-lokinet)
- [Session Foundation GitHub](https://github.com/session-foundation/session-desktop)
- [Session Messenger Review 2026 -- CyberInsider](https://cyberinsider.com/secure-encrypted-messaging-apps/session/)
- [Session Security Guide -- Protectstar](https://www.protectstar.com/en/blog/the-security-of-the-session-messenger-a-guide)
- [Session Whitepaper (arXiv)](https://arxiv.org/pdf/2002.04609)
- [Session Private Messenger Analysis -- Medium](https://osintph.medium.com/session-private-messenger-a-look-at-features-privacy-security-and-usage-db4504ebe605)
- [Session vs Signal -- Factually](https://factually.co/product-reviews/electronics-tech/session-vs-signal-encrypted-messengers-high-risk-conversations-598723)

### Briar Messenger
- [Briar Project -- How It Works](https://briarproject.org/how-it-works/)
- [Briar User Manual](https://briarproject.org/manual/)
- [Briar Mailbox Release Announcement](https://briarproject.org/news/2023-briar-mailbox-released/)
- [Bramble QR Code Protocol Spec (BQP)](https://code.briarproject.org/briar/briar-spec/-/blob/master/protocols/BQP.md)
- [Bramble Transport Protocol Spec (BTP)](https://code.briarproject.org/briar/briar-spec/blob/master/protocols/BTP.md)
- [Briar GitHub Mirror](https://github.com/briar/briar)
- [Briar Mailbox GitHub](https://github.com/briar/briar-mailbox)
- [ETH Zurich Briar Cryptography Analysis (PDF)](https://ethz.ch/content/dam/ethz/special-interest/infk/inst-infsec/appliedcrypto/education/theses/report_YuanmingSong.pdf)
- [Decoding Briar Messenger -- Satscryption](https://satscryption.substack.com/p/decoding-briar-messenger)
- [Briar Wikipedia](https://en.wikipedia.org/wiki/Briar_(software))
- [Briar Offline Mesh Analysis -- ByteIota](https://byteiota.com/briar-offline-mesh-when-internet-shutdowns-cut-85m-off/)
- [Briar on Hacker News](https://news.ycombinator.com/item?id=43363031)

### Wire Messenger
- [Wire Security and Privacy](https://wire.com/en/security)
- [Wire Features](https://wire.com/en/features)
- [Wire MLS Explained](https://wire.com/en/blog/messaging-layer-security-mls-explained)
- [Wire Proteus to MLS Migration](https://support.wire.com/hc/en-us/articles/18666343787293-Migration-from-Proteus-to-MLS-protocol)
- [Wire MLS Documentation](https://support.wire.com/hc/en-us/articles/12434725011485-Messaging-Layer-Security-MLS)
- [Wire Guest Rooms](https://support.wire.com/hc/en-us/articles/360000574069-Create-guest-rooms)
- [Wire Guests and Externals](https://wire.com/guests-and-externals)
- [Wire ID Shield](https://wire.com/en/id-shield)
- [Wire Proteus Protocol (GitHub)](https://github.com/wireapp/proteus)
- [Wire Axolotl and Proteus -- Medium](https://wireapp.medium.com/axolotl-and-proteus-788519b186a7)
- [Wire Security Explained](https://wire.com/en/blog/wire-messenger-security-explained)
- [Wire Wikipedia](https://en.wikipedia.org/wiki/Wire_(software))
- [Wire Secure File Sharing -- Medium](https://medium.com/@wireapp/secure-file-sharing-now-in-wire-27165540c6f5)
- [Wire Messenger Audit -- TechCrunch](https://techcrunch.com/2017/02/10/messaging-app-wire-now-has-an-external-audit-of-its-e2e-crypto/)
- [Wire Security Review -- TrustedSec](https://trustedsec.com/blog/wire-messenger-new-competitor-signal)
- [MLS RFC 9420 (IETF)](https://datatracker.ietf.org/doc/rfc9420/)
