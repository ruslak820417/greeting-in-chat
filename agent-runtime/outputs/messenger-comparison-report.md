# SimpleX Chat vs Element (Matrix) vs QRChat — Comprehensive Comparison Report

**Date:** 2026-03-24
**Author:** Agent Teams Research
**QRChat Version:** 4.0.0 (build 16)

---

## Table of Contents

1. [SimpleX Chat — Architecture Deep Dive](#1-simplex-chat--architecture-deep-dive)
2. [Element / Matrix Protocol — Architecture Deep Dive](#2-element--matrix-protocol--architecture-deep-dive)
3. [Feature-by-Feature Comparison Table](#3-feature-by-feature-comparison-table)
4. [QRChat Gap Analysis & Recommendations](#4-qrchat-gap-analysis--recommendations)
5. [Priority Roadmap for QRChat](#5-priority-roadmap-for-qrchat)

---

## 1. SimpleX Chat — Architecture Deep Dive

### 1.1 No User Identifiers — How It Works

SimpleX is the first messaging network that operates **without any user identifiers at all** — no phone number, no email, no username, not even a random number or cryptographic key used as an identifier.

**How contacts connect:**
- Users share a one-time invitation link or QR code to initiate contact
- Each conversation uses a pair of **unidirectional simplex message queues** (one for each direction)
- Each queue has its own temporary, disposable address — these addresses are NOT user identifiers
- The server only sees isolated message deliveries to opaque queue identifiers and cannot link sender and receiver

**Key implication:** Nobody can contact you unless you explicitly share an invitation link/QR code. This eliminates spam by design.

### 1.2 Double-Hop Relay Design (Private Message Routing)

Since v5.8/v6.0, SimpleX implements **two-hop packet routing** enabled by default:

1. Client encrypts the message for the **destination server** (layer 1)
2. Client wraps it in another encryption layer for a **forwarding server** (layer 2)
3. The forwarding server decrypts its layer and forwards to the destination server
4. The destination server decrypts its layer and delivers to the recipient's queue

**Result:** The forwarding server knows the sender but not the destination. The destination server knows the recipient queue but not the sender. Neither server sees both ends. This is similar to onion routing (Tor) but with exactly 2 hops for performance.

### 1.3 XFTP Protocol (File Transfer)

SimpleX uses a dedicated file transfer protocol called **XFTP** instead of sending files through message queues:

- Files are encrypted with a **random symmetric key** using NaCl `secret_box` (XSalsa20-Poly1305)
- Files are split into **fixed-size chunks** (256KB, 1MB, or 4MB)
- Chunks are uploaded to XFTP relay servers with separate identifiers
- Each chunk is additionally encrypted in transit via **NaCl `crypto_box`** (Curve25519 + XSalsa20-Poly1305) with ephemeral DH keys per recipient
- The **file description** (containing chunk addresses, keys, and the symmetric decryption key) is sent through the secure SimpleX Chat channel
- Mobile apps randomly inflate the declared recipient count to hide the actual number of recipients from the XFTP relays
- No relay sees all chunks; chunks from the same file are unlinkable across relays

### 1.4 Voice/Video Calls

- End-to-end encrypted audio and video calls via **WebRTC**
- Routed through a **TURN relay server by default** (hides IP addresses)
- Optional P2P mode (direct connection, exposes IP)
- Users can configure **self-hosted WebRTC ICE/TURN servers**
- Call signaling happens through the existing SimpleX message queues
- **Group calls are NOT supported** — only 1:1 calls

### 1.5 Groups (Decentralized, No Central Server)

- Groups are **fully decentralized** — the server has zero knowledge of a group's existence
- No global group identifier exists; only members have local database references
- Each member has an **independent pairwise connection** to every other member
- When sending a group message, the client sends it individually to each member
- **Secret groups** have additional restrictions: disappearing messages, no forwarding
- Group owners have moderation capabilities (remove messages, block members, approve new members)
- Practical limit: works best for groups under ~100 members; larger groups (thousands) exist but are expensive in bandwidth and battery
- Large groups improvement ongoing (January 2025 blog post)

### 1.6 Message Deletion / Disappearing Messages

**Disappearing messages:**
- Configurable per-conversation timer (set by group owner or agreed between contacts)
- Messages auto-delete after the timer expires on both devices
- Disabled by default; can be enabled per contact or per group

**Delete for everyone:**
- `x.msg.del` protocol message enables soft-delete
- Receiving clients replace the original message with a "message deleted" indicator
- Time-limited: clients are recommended to restrict deletion window

### 1.7 Offline Messages

- SMP relay servers **store encrypted messages while the recipient is offline**
- Messages are held temporarily (up to a configurable period, then purged)
- Once acknowledged by the recipient client, messages are deleted from the server
- No long-term server-side storage; the server is a temporary transit point

### 1.8 Spam Prevention Without Identifiers

SimpleX's no-identifier design inherently prevents spam:
- You can only receive messages from contacts YOU have explicitly invited (via QR/link)
- No user discovery mechanism exists — you cannot search for or find users
- One-time invitation links can be used once and then become invalid
- Temporary user addresses can be rotated or revoked at any time
- Group owners can require member approval before allowing messages

### 1.9 Encryption Stack

| Layer | Algorithm | Purpose |
|-------|-----------|---------|
| E2E encryption | **Double Ratchet** (Signal-style) | Forward secrecy, post-compromise security |
| DH key exchange | **X25519** (Curve25519) | Asymmetric key agreement |
| Symmetric encryption | **XSalsa20-Poly1305** (NaCl `secretbox`) | Message & file encryption |
| Authenticated encryption | **NaCl `crypto_box`** (X25519 + XSalsa20-Poly1305) | Transport encryption to relays, XFTP chunks |
| Signatures | **Ed25519** | Message authenticity |
| KDF | **HKDF-SHA512** | Key derivation |
| Post-quantum | **Streamlined NTRU Prime** (NOT ML-KEM/Kyber) | Quantum-resistant key exchange |
| PQ integration | Augmented Double Ratchet | PQ KEM added to each DH ratchet step |

**Why NTRU Prime instead of ML-KEM/Kyber:** SimpleX rejected NIST's ML-KEM standard because it removed a critical hashing step that mitigates attacks via compromised random number generators. They chose NTRU Prime (already adopted in SSH) as a safer alternative.

**PQ status:** Post-quantum encryption is opt-in per contact since v5.6. When enabled, all new contacts use the quantum-resistant Double Ratchet variant.

### 1.10 Delivery & Read Receipts

- **Delivery receipts:** Implemented since v5.2. Optional, disabled by default for existing profiles, enabled by default for new ones. Can be toggled per contact/profile.
- **Read receipts:** Deliberately NOT implemented. The team believes read receipts create social pressure and compromise privacy. Users are encouraged to use reactions instead.

### 1.11 Message Reactions

- 6 fixed emoji reactions: thumbs up, thumbs down, smile, tear, heart, rocket
- Maximum 3 reactions per message per user
- Can be disabled per conversation
- Deliberately limited to avoid UI clutter

---

## 2. Element / Matrix Protocol — Architecture Deep Dive

### 2.1 Federation (Decentralized Servers)

Matrix is a **federated** protocol — multiple independent homeservers communicate with each other:

- Each organization/user can run their own **homeserver** (Synapse, Dendrite, Conduit)
- Internal conversations stay on the local server
- Federated conversations are replicated only to the specific external servers involved
- Server-to-server traffic is encrypted with HTTPS and signed with each server's Ed25519 private key
- Current spec version: **v1.17** (December 2025)
- Each room is replicated across all participating homeservers (no single point of failure)

### 2.2 Megolm Encryption (Group Chats)

Megolm is Matrix's group encryption protocol, extending Olm (Double Ratchet) for scalability:

- Each device maintains a **Megolm session** for each room it participates in
- The session generates an AES-256 key and HMAC-SHA-256 key
- After each message, the Megolm ratchet advances via a hash calculation (forward-only)
- **Key distribution:** Session keys are shared via 1:1 Olm channels (Signal-style Double Ratchet)
- Sharing the current ratchet state allows decryption of **future** messages but NOT past ones (forward secrecy)
- Scales to thousands of devices per room (unlike Signal's per-message DH, which doesn't scale)
- One-time cost: joining a room requires syncing ~1000-2000 Olm key exchanges, then no latency

### 2.3 Media Encryption and Upload

- In E2E-encrypted rooms, files are encrypted **client-side** before upload
- Encryption: **AES-256-CTR** with a single-use 256-bit key
- Upload: encrypted blob is uploaded as `application/octet-stream` (server cannot identify file type)
- The encryption key, IV, and hash are embedded in the message event (shared via Megolm)
- Library: `matrix-encrypt-attachment` (JS/TS implementation)
- Server stores opaque encrypted blobs; cannot decrypt content

### 2.4 Voice/Video Calls

**Historical (Jitsi):** Multi-party calls embedded Jitsi Meet instances — required separate infrastructure.

**Current (Element Call — Native Matrix VoIP):**
- Built entirely on Matrix protocol (MSC3401)
- No additional servers needed
- End-to-end encrypted voice and video
- Full mesh topology: each participant places a 1:1 call to every other participant
- Supports both 1:1 and group calls
- Being actively developed to replace Jitsi integration
- Element X (new client) uses Element Call by default

### 2.5 Typing Indicators, Read Receipts, Presence

**Typing indicators:**
- Ephemeral Data Units (EDUs) — not stored, not sent via push
- `m.typing` events broadcast to room participants
- Automatically cleared after timeout

**Read receipts:**
- `m.receipt` events with `m.read` type
- Per-room, per-user tracking of the last read event
- Used for unread badge calculations
- Can generate push notification updates (unread count changes)
- Private read receipts added in recent spec versions

**Presence:**
- `m.presence` events: online, offline, unavailable
- Optional — can be disabled server-side for performance
- Includes `last_active_ago` timestamp
- Significant performance impact at scale

### 2.6 Message Editing and Deletion

**Editing:**
- `m.replace` relation type (MSC2676, added in v1.4)
- `m.relates_to` with `rel_type: "m.replace"` + `m.new_content`
- Edit history is preserved (federated servers keep original)
- Clients display the latest version with an "edited" indicator

**Deletion (Redaction):**
- `m.room.redaction` events
- Removes content but preserves the event shell (metadata)
- Moderators can redact any message; users can redact their own
- Federated servers may retain original content depending on configuration

### 2.7 Reactions and Threads

**Reactions:**
- `m.annotation` relation type
- Any emoji or text can be used as a reaction
- Aggregated by the server and presented to clients
- Added in v1.4

**Threads:**
- `m.thread` relation type (MSC3440, added in v1.4)
- Per-thread notifications and read receipts (MSC3771, MSC3773)
- Allows nested conversations within a room
- Thread root message and threaded replies are distinct

### 2.8 Push Notifications (Sygnal)

- **Sygnal** is the reference Matrix Push Gateway
- Homeserver forwards event information to the push gateway via HTTP
- Gateway translates Matrix events into APNs (iOS) / FCM (Android) push notifications
- Supports custom push gateways for self-hosted deployments
- Notification payload includes room ID, event ID, sender, unread counts
- Ephemeral events (typing, presence) are NOT pushed
- Read receipts may trigger unread count updates via push

### 2.9 Key Verification

**Emoji Verification (SAS — Short Authentication String):**
- Both devices generate ephemeral ECDH keypairs
- Exchange public keys and derive shared secret
- Display 7 emojis (or 6-digit numbers) for visual comparison
- Both users confirm match to complete verification

**QR Code Verification:**
- One device displays a QR code containing its cross-signing key
- The other device scans it and automatically verifies
- Faster than emoji comparison

**Cross-Signing:**
- Three-key trust chain: Master Signing Key (MSK), Self Signing Key (SSK), User Signing Key (USK)
- Verify once, trust all devices of that user
- MSK signs SSK (trusts own devices) and USK (trusts other users)
- Stored encrypted in server-side secret storage (SSSS)

### 2.10 Message Retention / Disappearing Messages

- Server-side retention policies (MSC1763) — experimental, not yet formally in spec
- `m.room.retention` state event with `max_lifetime` parameter
- Server purges expired events on schedule
- **No client-side disappearing messages built into Element** — relies on server-side purge
- Administrators configure retention; users have limited control
- Limitation: no UI warning about disappearing messages in many clients

---

## 3. Feature-by-Feature Comparison Table

| Feature | SimpleX Chat | Element (Matrix) | QRChat (v4.0.0) |
|---------|-------------|-------------------|------------------|
| **IDENTITY & CONTACT DISCOVERY** | | | |
| User identifiers | None at all | Username (@user:server.tld) | UUID (internal) |
| Contact discovery | QR code / invitation link only | Username search, phone/email via Identity Service | QR code only |
| Phone/email required | No | Optional (for discovery) | No |
| **ARCHITECTURE** | | | |
| Server model | Relay servers (no federation, no user data) | Federated homeservers | Single central WebSocket server |
| Decentralization | Fully decentralized (any relay) | Federated (multiple homeservers) | Centralized (Railway server) |
| Self-hostable servers | Yes (SMP + XFTP relays) | Yes (Synapse/Dendrite/Conduit) | Partially (server is open) |
| P2P capability | Optional for calls | No (server-mediated) | Yes (WebRTC data channels) |
| Offline message delivery | SMP relay queues (temporary) | Homeserver stores until sync | Server pending queue (48h expiry) |
| **ENCRYPTION** | | | |
| E2E encryption algorithm | Double Ratchet (Signal-style) | Olm (1:1) + Megolm (group) | Double Ratchet (Signal-style) |
| Crypto library | NaCl (custom Haskell impl) | libolm / vodozemac (Rust) | TweetNaCl (JS) |
| Key exchange | X25519 | X25519 (Olm) | X25519 |
| Symmetric cipher | XSalsa20-Poly1305 | AES-256-CTR (media), AES-256 (Megolm) | XSalsa20-Poly1305 |
| Signatures | Ed25519 | Ed25519 | Ed25519 |
| KDF | HKDF-SHA512 | HKDF-SHA256 | HKDF-SHA512 |
| Forward secrecy | Yes (DH ratchet) | Yes (Olm ratchet) | Yes (DH ratchet) |
| Post-quantum encryption | Yes (NTRU Prime, opt-in) | No (not yet) | No |
| Post-compromise security | Yes | Yes (Olm) | Yes |
| **MESSAGING FEATURES** | | | |
| Text messages | Yes | Yes | Yes |
| Image/video/file transfer | Yes (XFTP protocol) | Yes (media upload + Megolm encryption) | Yes (WebRTC chunks + relay fallback) |
| Voice messages | Yes | Yes | Yes |
| Message editing | No | Yes (m.replace) | Yes |
| Message deletion (for all) | Yes (soft-delete) | Yes (redaction) | Yes |
| Disappearing messages | Yes (per-contact/group timer) | Server-side only (experimental) | Yes (self-destruct timer) |
| Reactions | Yes (6 fixed emoji, max 3) | Yes (any emoji) | Yes (emoji reactions) |
| Reply/quote | Yes | Yes | Yes (swipe-to-reply) |
| Threads | No | Yes (m.thread) | No |
| Message forwarding | Yes | No (not natively) | Yes |
| Typing indicators | No (privacy choice) | Yes (ephemeral EDU) | Yes (configurable per contact) |
| Read receipts | No (deliberate omission) | Yes (m.receipt) | Yes (configurable per contact) |
| Delivery receipts | Yes (opt-in since v5.2) | Yes (built into sync) | Yes |
| Online/presence status | No (privacy choice) | Yes (m.presence, optional) | Yes (via WebSocket connection) |
| **CALLS** | | | |
| Voice calls | Yes (WebRTC, 1:1 only) | Yes (Element Call / Jitsi) | Yes (WebRTC) |
| Video calls | Yes (WebRTC, 1:1 only) | Yes (Element Call / Jitsi) | Yes (WebRTC) |
| Group calls | No | Yes (Element Call, full mesh) | No |
| Call relay (IP hiding) | Yes (TURN by default) | Yes (TURN) | Yes (TURN/STUN) |
| **GROUPS** | | | |
| Group chat | Yes (decentralized) | Yes (rooms, federated) | Yes (basic) |
| Group encryption | Per-member E2E (pairwise) | Megolm (efficient group ratchet) | Per-member (like SimpleX) |
| Group size limit | ~100 practical (no hard limit) | Thousands (Megolm scales) | Basic (no Megolm) |
| Group moderation | Yes (owner tools) | Yes (power levels, roles) | Basic |
| Group admin roles | Owner, admin, member | Granular power levels (0-100) | Basic (creator is admin) |
| **VERIFICATION** | | | |
| Contact verification | QR code scan (mandatory) | Emoji / QR / Cross-signing | QR code scan (mandatory) |
| Key fingerprint | N/A (no persistent identity) | Cross-signing trust chain | Yes (XXXX-XXXX format) |
| Device cross-signing | N/A | Yes (MSK/SSK/USK chain) | No |
| **PUSH NOTIFICATIONS** | | | |
| iOS push | Yes (APNs via relay) | Yes (Sygnal gateway) | Partial (APNs not configured) |
| Android push | Yes (FCM optional) | Yes (Sygnal + FCM) | Partial (FCM not configured) |
| Push without Google Services | Yes (unified push / polling) | Yes (UnifiedPush) | No |
| **PRIVACY** | | | |
| Metadata protection | Excellent (double-hop, no IDs) | Moderate (server sees room membership) | Basic (server sees connections) |
| IP protection | TURN default + optional Tor | TURN for calls; server sees IP | TURN for calls; server sees IP |
| Spam prevention | By design (opt-in contacts) | Moderate (room invites) | By design (QR-only contacts) |
| **PLATFORM** | | | |
| iOS | Yes (native Swift) | Yes (Element X, Rust SDK) | Yes (React Native) |
| Android | Yes (native Kotlin) | Yes (Element X, Rust SDK) | Yes (React Native) |
| Desktop | Yes (Haskell CLI + Electron) | Yes (Element Web) | No |
| Web client | No | Yes (Element Web) | No |
| Multi-device | Yes (linked devices) | Yes (cross-signing) | No |

---

## 4. QRChat Gap Analysis & Recommendations

### 4.1 CRITICAL — Security & Privacy Gaps

| # | Feature Gap | SimpleX Has It | Matrix Has It | Priority | Recommendation |
|---|------------|----------------|---------------|----------|----------------|
| 1 | **Post-quantum encryption** | Yes (NTRU Prime) | No | CRITICAL | Implement PQ KEM in Double Ratchet. Use NTRU Prime (like SimpleX) or ML-KEM. QRChat already uses TweetNaCl + Double Ratchet, so the integration path is similar to SimpleX's approach. This is the #1 security differentiator for 2026+. |
| 2 | **Private message routing (double-hop)** | Yes (default since v6.0) | No | CRITICAL | QRChat's server currently sees both sender and recipient. Implement relay-based routing where messages pass through an intermediary, so no single server sees both endpoints. This is essential for metadata protection. |
| 3 | **No user identifiers at protocol level** | Yes (core design) | No | IMPORTANT | QRChat already uses QR-code-only contact addition (like SimpleX). However, the server still maps userId to WebSocket connections. Consider: make userId ephemeral per-session, use per-queue addresses like SimpleX. Major architectural change but aligns with QRChat's privacy positioning. |
| 4 | **Encrypted file transfer protocol** | Yes (XFTP) | Yes (AES-256-CTR upload) | IMPORTANT | QRChat sends files via WebRTC chunks (good for P2P) but relay fallback sends through the signaling server unoptimized. Implement a dedicated encrypted file upload/download service (like XFTP) for the relay path. Files should be encrypted client-side with a random symmetric key before upload. |
| 5 | **Device cross-signing** | N/A | Yes (MSK/SSK/USK) | NICE-TO-HAVE | Only needed when QRChat supports multi-device. Not urgent for v4.x. |

### 4.2 IMPORTANT — Feature Gaps

| # | Feature Gap | SimpleX Has It | Matrix Has It | Priority | Recommendation |
|---|------------|----------------|---------------|----------|----------------|
| 6 | **Threads** | No | Yes | NICE-TO-HAVE | Not a core messenger feature. QRChat has reply/quote which covers 90% of the use case. Low priority. |
| 7 | **Group calls** | No | Yes | IMPORTANT | Neither SimpleX nor QRChat has group calls. Matrix's full-mesh approach (Element Call) works but doesn't scale well beyond ~8 participants. Implement basic 3-way calling first using existing WebRTC infrastructure. |
| 8 | **Scalable group encryption (Megolm)** | No (pairwise) | Yes (Megolm) | IMPORTANT | QRChat's groups currently work like SimpleX (send to each member individually). For groups >20 members, this is expensive. Consider implementing a Megolm-like group ratchet where one session key is shared via pairwise Olm/DR channels. |
| 9 | **Push notifications (fully working)** | Yes | Yes | CRITICAL | QRChat has push token registration code but APNs/FCM are not configured on Railway. This is blocking for App Store launch. Configure APNs credentials + FCM on Railway immediately. |
| 10 | **Multi-device support** | Yes (linked devices) | Yes (cross-signing) | IMPORTANT | QRChat is single-device only. Users increasingly expect to use messenger on phone + desktop. Implement linked devices (SimpleX model: share ratchet state to linked device via secure channel). |
| 11 | **Desktop/Web client** | Yes (both) | Yes (both) | IMPORTANT | Related to multi-device. A web client or Electron desktop app would significantly expand QRChat's usability. Medium-term goal. |
| 12 | **UnifiedPush / push without Google** | Yes | Yes | NICE-TO-HAVE | Privacy-focused users on degoogled Android need push without FCM. Consider adding UnifiedPush support or WebSocket-based background polling. |

### 4.3 QRChat Strengths (Already Competitive)

| Feature | QRChat Status | Comparison |
|---------|--------------|------------|
| **QR-code-only contact addition** | Full (mandatory QR scan with Ed25519 signature verification, 5-min expiry) | Better than Matrix (which allows username search), equal to SimpleX |
| **Double Ratchet E2E encryption** | Full (X25519, HKDF-SHA512, XSalsa20-Poly1305) | Equal to SimpleX, comparable to Matrix's Olm |
| **No phone/email required** | Yes | Equal to SimpleX, better than Matrix (which optionally uses Identity Service) |
| **WebRTC P2P data channels** | Full (with TURN fallback, Perfect Negotiation, glare fix) | Better than Matrix (no P2P); comparable to SimpleX (which uses relay-only for messages) |
| **Self-destruct messages** | Full (configurable timer, auto-delete on read) | Better than Matrix (server-side only); comparable to SimpleX |
| **Message editing** | Full (E2E encrypted edits) | Better than SimpleX (which has no editing); equal to Matrix |
| **Reactions** | Full (emoji reactions) | Comparable to SimpleX (which limits to 6); equal to Matrix |
| **Typing indicators** | Full (per-contact toggle) | Better than SimpleX (which has none); equal to Matrix |
| **Read receipts** | Full (per-contact toggle) | Better than SimpleX (which has none); equal to Matrix |
| **Delivery receipts** | Yes | Equal to both |
| **Voice/video calls** | Full (WebRTC with TURN) | Equal to SimpleX; comparable to Matrix |
| **Swipe-to-reply** | Full (gesture handler) | Standard feature across all three |
| **Message forwarding** | Full | Better than Matrix (no native forwarding); equal to SimpleX |
| **i18n (4 languages)** | EN, RO, RU, FR | Comparable |
| **SQLCipher encrypted database** | Full (Keychain-stored key) | Equal to SimpleX; better than standard Matrix clients |
| **Spam prevention by design** | Yes (QR-only contacts) | Equal to SimpleX; better than Matrix |

---

## 5. Priority Roadmap for QRChat

### Phase 1 — Launch Blockers (Immediate)

| Priority | Task | Effort | Impact |
|----------|------|--------|--------|
| P0 | Configure APNs + FCM on Railway server | 1 day | Unblocks push notifications for App Store |
| P0 | Apple Developer Account + TestFlight upload | 1-2 days | Unblocks App Store submission |
| P0 | Privacy Policy hosting (GitHub Pages) | 1 hour | Unblocks App Store submission |

### Phase 2 — Security Parity with SimpleX (1-3 months)

| Priority | Task | Effort | Impact |
|----------|------|--------|--------|
| P1 | **Post-quantum key exchange** (add NTRU Prime or ML-KEM to Double Ratchet) | 2-3 weeks | Major security differentiator; future-proofs encryption |
| P1 | **Private message routing** (double-hop relay) | 3-4 weeks | Critical metadata protection; prevents server from seeing both endpoints |
| P2 | **Encrypted file relay protocol** (client-side encryption + dedicated upload) | 2 weeks | Protects files in transit through relay; currently files via relay lack dedicated encryption layer |
| P2 | **Ephemeral session identifiers** (per-connection queue addresses) | 2-3 weeks | Reduces server-side metadata; moves toward SimpleX-style privacy |

### Phase 3 — Feature Expansion (3-6 months)

| Priority | Task | Effort | Impact |
|----------|------|--------|--------|
| P2 | **Multi-device support** (linked devices with ratchet sync) | 4-6 weeks | High user demand; major usability improvement |
| P2 | **Group call support** (3-way WebRTC mesh) | 2-3 weeks | Competitive feature |
| P3 | **Megolm-style group encryption** (for large groups) | 4 weeks | Only needed if groups grow beyond ~20 members |
| P3 | **Desktop/web client** | 6-8 weeks | Expands platform reach |
| P3 | **UnifiedPush support** (degoogled Android) | 1 week | Niche but privacy-aligned |

### Phase 4 — Advanced Features (6+ months)

| Priority | Task | Effort | Impact |
|----------|------|--------|--------|
| P3 | **Self-hostable relay servers** (let users run their own QRChat relay) | 3-4 weeks | Decentralization; enterprise use case |
| P3 | **Onion routing** (multi-hop, Tor-like) | 6-8 weeks | Maximum metadata protection |
| P4 | **Threads** | 2 weeks | Nice-to-have, not essential |
| P4 | **Federation** (Matrix-style server-to-server) | 8-12 weeks | Major architecture change; questionable ROI vs SimpleX model |

---

## Summary

**QRChat's current position:**
QRChat is already architecturally closer to SimpleX Chat than to Matrix/Element. Both QRChat and SimpleX share the same foundational philosophy: no phone numbers, no emails, QR-code-based contact exchange, NaCl cryptography, Double Ratchet, and WebRTC calls. QRChat actually has features that SimpleX deliberately omits (message editing, typing indicators, read receipts).

**Biggest gaps vs SimpleX:**
1. Post-quantum encryption (NTRU Prime in Double Ratchet)
2. Private message routing (double-hop relay)
3. No user identifiers at the protocol level (ephemeral queue addresses)
4. Dedicated encrypted file transfer protocol (XFTP equivalent)

**Biggest gaps vs Matrix:**
1. Multi-device support
2. Group calls
3. Scalable group encryption (Megolm)
4. Desktop/web client
5. Federation

**Strategic recommendation:**
Focus on SimpleX-style privacy enhancements (post-quantum, double-hop routing) rather than Matrix-style federation. QRChat's strength is its simplicity and privacy-first design. Adding federation would add enormous complexity with questionable user benefit. Instead, pursue the SimpleX model: allow users to choose/host relay servers while keeping the protocol simple.

---

## Sources

### SimpleX Chat
- [SimpleX Chat GitHub](https://github.com/simplex-chat/simplex-chat)
- [SimpleX Platform Overview](https://simplex.chat/docs/simplex.html)
- [SimpleX Chat Protocol](https://simplex.chat/docs/protocol/simplex-chat.html)
- [SimpleX XFTP Protocol Blog](https://simplex.chat/blog/20230301-simplex-file-transfer-protocol.html)
- [SimpleX Private Message Routing](https://simplex.chat/blog/20240604-simplex-chat-v5.8-private-message-routing-chat-themes.html)
- [SimpleX Post-Quantum Encryption](https://simplex.chat/blog/20240314-simplex-chat-v5-6-quantum-resistance-signal-double-ratchet-algorithm.html)
- [SimpleX Security Review by Trail of Bits](https://simplex.chat/blog/20241014-simplex-network-v6-1-security-review-better-calls-user-experience.html)
- [SimpleX Delivery Receipts](https://simplex.chat/blog/20230722-simplex-chat-v5-2-message-delivery-receipts.html)
- [SimpleX Reactions](https://simplex.chat/blog/20230523-simplex-chat-v5-1-message-reactions-self-destruct-passcode.html)
- [SimpleX Secret Groups](https://simplex.chat/docs/guide/secret-groups.html)
- [SimpleX Large Groups](https://simplex.chat/blog/20250114-simplex-network-large-groups-privacy-preserving-content-moderation.html)
- [SimpleX Audio/Video Calls](https://simplex.chat/docs/guide/audio-video-calls.html)
- [SimpleX WebRTC Configuration](https://simplex.chat/docs/webrtc.html)
- [SimpleX FAQ](https://simplex.chat/faq/)
- [SimpleX Redefining Privacy](https://simplex.chat/blog/20240516-simplex-redefining-privacy-hard-choices.html)
- [SimpleX PQ Double Ratchet RFC](https://github.com/simplex-chat/simplexmq/blob/stable/protocol/pqdr.md)

### Matrix / Element
- [Matrix Specification v1.17](https://spec.matrix.org/latest/)
- [Matrix E2E Encryption Guide](https://matrix.org/docs/matrix-concepts/end-to-end-encryption/)
- [Matrix Wikipedia](https://en.wikipedia.org/wiki/Matrix_(protocol))
- [Element Native VoIP (Element Call)](https://element.io/blog/introducing-native-matrix-voip-with-element-call/)
- [Sygnal Push Gateway](https://github.com/matrix-org/sygnal)
- [Matrix Push Gateway API Spec](https://spec.matrix.org/unstable/push-gateway-api/)
- [Matrix Message Editing MSC2676](https://github.com/matrix-org/matrix-spec-proposals/blob/main/proposals/2676-message-editing.md)
- [Matrix QR Key Verification MSC1544](https://github.com/matrix-org/matrix-spec-proposals/pull/1544)
- [Matrix Cross-Signing Guide](https://matrix.org/docs/guides/implementing-more-advanced-e-2-ee-features-such-as-cross-signing/)
- [Matrix Encrypt Attachment Library](https://github.com/matrix-org/matrix-encrypt-attachment)
- [Matrix Read Receipts & Notifications](https://patrick.cloke.us/posts/2023/01/05/matrix-read-receipts-and-notifications/)
- [Matrix Message Retention Policies (Synapse)](https://matrix-org.github.io/synapse/latest/message_retention_policies.html)
- [Element E2EE Features](https://element.io/en/features/end-to-end-encryption)
- [Matrix in Government IT](https://www.theregister.com/2026/02/09/matrix_element_secure_chat/)
- [Matrix v1.16 Spec](https://github.com/easypro-tech/matrix-specification-v1.16)

### Comparisons
- [Encrypted Messaging Comparison (dasroot.net)](https://dasroot.net/posts/2025/12/encrypted-messaging-signal-matrix-session-simplex/)
- [Instant Messenger Comparison Table](https://eylenburg.github.io/im_comparison.htm)
- [SimpleX vs Signal (GrapheneOS Forum)](https://discuss.grapheneos.org/d/13043-how-does-simplex-compare-to-signal)
- [Privacy Guides — Real-Time Communication](https://www.privacyguides.org/en/real-time-communication/)
- [SimpleX Chat BrightCoding Review](https://www.blog.brightcoding.dev/2025/09/18/simplex-chat-the-first-messaging-app-with-no-user-identifiers-privacy-by-design/)
