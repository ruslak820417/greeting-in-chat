# Deep Research: SimpleX Chat Messenger — Complete Technical Analysis

**Date:** 2026-03-30
**Purpose:** Competitive analysis for QRChat (React Native, TweetNaCl, WebRTC, SQLite, Double Ratchet)
**Sources:** SimpleX GitHub repos (simplex-chat, simplexmq), protocol specifications, RFCs, blog posts, security audits, source code

---

## Table of Contents

1. [Architecture & Protocol](#1-architecture--protocol)
2. [Cryptography](#2-cryptography)
3. [WebRTC Calls](#3-webrtc-calls)
4. [Unique Features](#4-unique-features)
5. [Client Architecture](#5-client-architecture)
6. [Server Infrastructure](#6-server-infrastructure)
7. [Security Audits](#7-security-audits)
8. [Lessons for QRChat](#8-lessons-for-qrchat)

---

## 1. Architecture & Protocol

### 1.1 Core Design Philosophy

SimpleX is the **first messenger with zero user identifiers** — no phone numbers, no usernames, no public keys, no random IDs. Instead of identifying users, it uses **per-contact unidirectional message queues** on relay servers. Each contact relationship uses a completely separate set of queue addresses.

The architecture is a layered stack:

```
+------------------+
|    Chat App UI    |  (Swift/Kotlin/Compose Multiplatform)
+------------------+
|  SimpleX Agent   |  (Haskell — duplex connections, E2E encryption, queue rotation)
+------------------+
|  SimpleX Client  |  (Haskell — SMP protocol, queue management)
+------------------+
|  SMP over TLS    |  (transport to relay servers)
+------------------+
```

### 1.2 SimpleX Messaging Protocol (SMP) — How It Works

SMP is a **client-server protocol for asynchronous unidirectional message transmission via simplex queues**. Key mechanics:

**Queue Creation:**
1. Recipient (Alice) creates a queue on an SMP server she chooses
2. She provides: her Ed25519/X25519 auth public key + Curve25519 DH public key for server encryption
3. Server returns: separate `recipientId` and `senderId` (16-24 random bytes each) + server's DH key
4. Server and recipient perform DH exchange — the shared secret re-encrypts all delivered messages, preventing ciphertext correlation between incoming/outgoing server traffic

**Message Sending:**
1. Sender (Bob) receives queue info out-of-band (via QR code, link, or existing secure channel)
2. Bob sends `SEND` command with the `senderId` — message is E2E encrypted + encrypted again with server-recipient shared secret
3. Server holds the message until recipient subscribes and ACKs
4. All transmissions are **fixed 16384-byte padded blocks** — uniform traffic makes correlation harder

**Queue Lifecycle:**
- Queues are unidirectional (simplex) — for bidirectional chat, each side creates a queue
- Queues can be rotated to different servers without losing the contact (QADD/QKEY/QUSE/QTEST protocol)
- Suspended queues stop accepting messages; deleted queues purge all undelivered messages

### 1.3 SMP Relay Servers — What They Store

**In memory only (by default):**
- Queue metadata: recipientId, senderId, auth keys, DH shared secrets
- Undelivered messages (with server-enforced TTL, typically days)
- Active subscriptions (which transport connections are listening on which queues)

**What servers explicitly DO NOT store:**
- User accounts, profiles, or contacts
- Message history after delivery + ACK
- Logs of client commands (production requirement)
- Snapshots or backups of queue state

**Critical anti-correlation property:** The server re-encrypts each message with the recipient-server DH secret before delivery. This means the ciphertext a sender puts in is **different from the ciphertext the recipient gets out** — even if TLS is compromised, you cannot correlate input/output traffic by matching encrypted payloads.

### 1.4 Double-Hop Onion Routing (Private Message Routing)

Added in SMP v8 (released v5.8, mid-2024). Problem: since recipients choose the SMP server, senders connecting directly to recipient's server expose their IP address.

**How 2-hop routing works:**

```
Sender → [TLS] → SMP Proxy (sender's server) → [TLS] → SMP Destination (recipient's server) → [TLS] → Recipient
```

1. **PRXY:** Sender asks their trusted SMP server to act as proxy, connecting to the destination server
2. **PKEY:** Proxy returns session info including destination server's certificate + session key (signed)
3. **PFWD:** Sender encrypts the command to the destination server using a per-command random key + server's session key, sends to proxy
4. **RFWD:** Proxy adds another encryption layer and forwards to destination
5. **RRES/PRES:** Response travels back through same path, double-encrypted

**Four encryption layers on the wire:**
- TLS (transport between each hop)
- s2r: sender-to-relay encryption (destination server can't be MITM'd by proxy)
- p2r: proxy-to-relay encryption (prevents ciphertext correlation inside TLS)
- e2e: end-to-end Double Ratchet encryption

**Key security properties:**
- Proxy cannot see which queues sender sends to (encrypted with destination server key)
- Destination server cannot see sender's IP or session
- Random correlation IDs and keys per message prevent session correlation
- Proxy MUST reuse the same session with the destination server for all clients (preventing per-client correlation)
- Client validates destination server certificate fingerprint against address to prevent MITM by proxy

### 1.5 Message Queues (Simplex Queues)

Each queue has:
- **Separate IDs for sender and recipient** (16-24 random bytes each)
- **Separate auth keys** — recipient uses Ed25519/X25519 for commands, sender uses their own key for SEND
- **Server DH key pair** — unique per queue, for re-encrypting delivered messages
- **FIFO delivery** with sequential ACK requirement
- **Quota enforcement** — configurable max messages; when exceeded, sender gets `ERR QUOTA` until ALL messages are consumed

**When both users are offline:**
- Messages sit in server memory until TTL expires (configurable, default ~days)
- Servers use in-memory persistence with optional append-only log for crash recovery
- Messages are NOT replicated — if server crashes before log restore, messages are lost
- The agent layer can use **redundant queues** (multiple queues per contact on different servers) to mitigate this
- Push notifications (see below) wake up iOS devices to receive pending messages

---

## 2. Cryptography

### 2.1 Full Crypto Stack

**Transport Layer (Client ↔ Server):**
- TLS 1.3 restricted to: `TLS_CHACHA20_POLY1305_SHA256`
- Ed25519 for signatures, X25519 for ECDHE
- Self-signed server certificates (offline CA → online cert → session cert chain)
- Server identity = SHA256 fingerprint of offline certificate, embedded in server address
- No session resumption allowed (prevents tracking)

**SMP Layer (Per-Queue Encryption):**
- NaCl `crypto_box` (Curve25519 + XSalsa20 + Poly1305) between server and recipient
- Purpose: different ciphertext in/out of server, preventing traffic correlation
- Separate Curve25519 DH exchange per queue for this encryption
- Message nonce = server-generated unique msgId (24 bytes random)

**E2E Layer (Agent Protocol — Double Ratchet):**
- **Key Exchange:** Modified X3DH with 2 ephemeral keys per side (Curve448)
- **Ratchet:** Double Ratchet with encrypted headers (Signal spec compliant base)
- **Symmetric Cipher:** AES-256-GCM (AEAD)
- **KDF:** HKDF-SHA512
- **Message Integrity:** Each agent message includes agentMsgId (sequential Int64) + hash of previous message
- **Deniability:** Preserved — recipients cannot prove message origin to third parties

### 2.2 How SimpleX's Double Ratchet Differs from Signal's

| Aspect | Signal | SimpleX |
|--------|--------|---------|
| **Key Exchange** | X3DH with server-stored prekeys | X3DH variant with 2 ephemeral keys, no server-stored keys |
| **DH Curve** | Curve25519 | Curve448 (stronger, 224-bit security) |
| **Header Encryption** | Not standard | Yes — encrypted headers hide ratchet state |
| **Post-Quantum** | PQXDH (augments initial X3DH only) | PQDR — augments EVERY ratchet step (see 2.3) |
| **PQ Break-in Recovery** | No (only initial exchange is PQ-protected) | Yes — each DH ratchet step includes PQ KEM |
| **Message Padding** | No fixed padding | All messages padded to 16KB blocks |
| **KDF** | HKDF-SHA256 | HKDF-SHA512 |
| **Queue-level E2E** | N/A | Additional NaCl crypto_box per SMP queue |

### 2.3 Post-Quantum Encryption — NTRU Prime Integration

SimpleX uses **PQDR (Post-Quantum resistant augmented Double Ratchet)** — their own design that is fundamentally different from Signal's PQXDH.

**Algorithm: Streamlined NTRU-Prime 761 (sntrup761)**

Chosen over ML-KEM/Kyber because:
- Used in OpenSSH for years (battle-tested)
- ML-KEM standardization raised expert concerns (removed hash of random numbers, disputed security levels)
- ML-KEM may conflict with existing patents; sntrup761 does not

**How PQDR works:**

The core innovation is running **two parallel KEM agreements** alongside the DH exchange on every ratchet step:

```
Standard Double Ratchet:
  RK, CK = KDF(RK, DH(myKey, theirKey))

SimpleX PQDR:
  RK, CK = KDF(RK, DH(myKey, theirKey) || PQ_shared_secret)
```

Each message header carries:
- DH public key (as usual)
- **PQ KEM encapsulation key** (new public key for next KEM)
- **PQ KEM ciphertext** (encapsulated shared secret from previous KEM)

On each DH ratchet step:
1. Decapsulate shared secret from received header's ciphertext (KEM #2)
2. Generate new PQ key pair
3. Generate new random shared secret
4. Encapsulate new secret with received encapsulation key (KEM #1)
5. Augment both DH agreements with KEM shared secrets

**Result:** Unlike Signal's PQXDH where PQ protection is only at initial key exchange, SimpleX's PQDR provides **PQ-resistant break-in recovery** — even if an attacker with a quantum computer compromises current keys, security recovers on the next ratchet step.

**Overhead:** ~2-4KB per message (KEM key + ciphertext). Since SimpleX pads all messages to 16KB blocks, this overhead is absorbed without additional traffic in most cases.

**Dynamic PQ:** The protocol supports adding/removing PQ KEM from existing connections. Groups larger than ~20 members disable PQ due to slow key generation on mobile devices (~10-20 keys/second for sntrup761).

### 2.4 XFTP — File Encryption and Transfer

Files use a separate protocol (XFTP) running over HTTP/2 + TLS:

**File Preparation:**
1. Compute SHA512 digest of original file
2. Prepend filename header, pad to whole number of chunks
3. Encrypt entire padded file with random NaCl `secret_box` key (XSalsa20-Poly1305)
4. Split into fixed-size chunks: 64KB, 256KB, 1MB, or 4MB
5. Upload chunks to multiple XFTP servers (sender's choice)

**File Transfer:**
- Each chunk gets separate random Ed25519 auth keys for sender and each recipient
- Sender generates more recipient keys than actual recipients (rounded up to power of 2) to hide recipient count
- Each download gets additionally encrypted with ephemeral DH (NaCl crypto_box) — no shared ciphertext between upload/download
- File description (YAML document with keys, hashes, chunk locations) is sent via SMP messaging channel

**Anti-Correlation:**
- XFTP servers only see individual chunks, not complete files
- Chunks of the same file on the same server look like unrelated uploads
- No identifiers shared between sender and recipient traffic

### 2.5 Key Verification

- Connection requests are passed **out-of-band** (QR code, link shared via other channel)
- This makes MITM on initial key exchange "very difficult" — attacker must intercept the out-of-band channel
- The invitation link contains: server address + queue ID + recipient's public keys + server certificate fingerprint
- Users can verify key fingerprints to confirm no MITM occurred
- Connection queue rotation is transparent — agent handles it automatically, re-establishing crypto on new queues

---

## 3. WebRTC Calls

### 3.1 Call Setup / Signaling Flow

SimpleX uses the existing SMP messaging channel for WebRTC signaling — **no separate signaling server:**

```
Alice                          SMP Relay                         Bob
  |-- x_call_inv (offer SDP) ------>|------>|                      |
  |                                 |       |-- MSG(x_call_inv) -->|
  |                                 |       |<-- ACK --------------|
  |                                 |       |                      |
  |                          <------|<------|-- x_call_offer -------|  (answer SDP)
  |<-- MSG(x_call_offer) ----------|       |                      |
  |-- ACK ---->|                   |       |                      |
  |                                 |       |                      |
  |-- x_call_extra (ICE) --------->|------>|-- MSG(ICE) --------->|
  |<-- x_call_extra (ICE) ---------|<------|-- MSG(ICE) ----------|
  |                                 |       |                      |
  |<================== WebRTC P2P / TURN ==================>|
```

Call messages are compressed (LZ-String base64) to fit within the 16KB SMP block size.

### 3.2 End-to-End Encryption (Beyond SRTP/DTLS)

SimpleX implements **custom frame-level encryption on top of WebRTC's DTLS-SRTP:**

- Uses **Insertable Streams API** (WebRTC Encoded Transform)
- AES-256-GCM encryption per frame
- Key exchange: A random AES key is generated by the caller and shared via the E2E encrypted SMP channel
- Each frame: first N bytes left as plaintext (codec header), rest encrypted with AES-GCM + random 12-byte IV
- Both native (iOS Swift `RTCFrameEncryptor`/`RTCFrameDecryptor`) and Web Worker implementations

```typescript
// Frame structure after encryption:
// [initial plaintext (codec header)] [AES-GCM ciphertext] [12-byte IV] [16-byte auth tag]
```

Initial plaintext sizes vary by frame type:
- Key frames: 10 bytes
- Delta frames: 3 bytes
- Empty frames: 1 byte

### 3.3 ICE/TURN Configuration

From the iOS source code:

```swift
defaultIceServers = [
    RTCIceServer(urlStrings: ["stuns:stun.simplex.im:443"]),
    RTCIceServer(urlStrings: ["turns:turn.simplex.im:443?transport=tcp"],
                 username: "private2", credential: "Hxuq2QxUjnhj96Zq2r4HjqHRj"),
]
```

- STUN over TLS (port 443) — `stuns:` protocol
- TURN over TLS/TCP (port 443) — `turns:` protocol with TCP transport
- SimpleX runs their own TURN servers
- Users can configure relay-only mode (`iceTransportPolicy = .relay`) to force all media through TURN
- Users can self-host WebRTC relay servers
- Uses their own fork of the WebRTC library with custom encryption/decryption support

### 3.4 Codec and Configuration

- **Video codec:** VP8 preferred (`RTCVideoCodecInfo(name: kRTCVp8CodecName)`)
- **SDP semantics:** Unified Plan
- **ICE gathering:** Continuous (`gatherContinually`)
- **ICE inactive timeout:** 30 seconds (allows time for answer before failing)
- **Screen sharing:** Supported (separate audio/video tracks for screen)
- **Camera switching:** Front/back toggle supported
- **Audio:** Uses RTCAudioSession with manual audio control for CallKit integration

---

## 4. Unique Features

### 4.1 No User Identifiers — How It Works Technically

**The fundamental insight:** Instead of routing messages to a person (identified by phone, username, or key), SimpleX routes messages to a **queue address on a server**. Each queue is single-use for one relationship.

For contact Alice ↔ Bob:
- Alice creates Queue_A on Server_1 (her choice) — gives Bob the address
- Bob creates Queue_B on Server_2 (his choice) — gives Alice the address
- Messages from Alice to Bob go to Queue_B on Server_2
- Messages from Bob to Alice go to Queue_A on Server_1
- Neither server knows the queues are related
- Neither server knows Alice or Bob's identity

**What makes this different from just "anonymous accounts":**
- There is no shared identifier across contacts — Server_1 doesn't know Alice is Alice
- Queue IDs are random bytes, not derived from any identity
- A new set of queues is created for every contact
- Queues can be rotated to different servers without the contact knowing
- Even the transport connections can be isolated per contact (separate TCP connections, separate Tor circuits)

### 4.2 Contact Connections Without User IDs

**One-Time Invitation:**
1. Alice generates an invitation link containing: SMP server address, queue ID, her public keys
2. Alice shares this link out-of-band (QR code, paste, etc.)
3. Bob uses the link to send a confirmation to Alice's queue
4. Alice's agent automatically creates a return queue and sends Bob the address
5. Both sides now have a duplex connection with no shared identity

**Contact Addresses (Reusable):**
- Alice creates a "contact queue" — a special queue only for receiving connection requests
- She publishes this address (like a public profile link)
- Each person who connects creates a new independent duplex connection
- The contact address can be deleted without affecting existing connections

### 4.3 Disappearing Messages

Implementation details from the RFC:

- A `delete_at` field on `chat_items` table with database index
- Background cleanup manager periodically scans for items past expiry
- Items expiring within 30 minutes get a dedicated timer thread
- Items past current time are bulk-deleted
- Timer starts when message is **sent or marked read** (not when received)
- Per-conversation setting, negotiated between contacts:
  - Direct chats: both parties must agree (offer/agree protocol)
  - Groups: set by owner
- Killing the timer thread when message is manually deleted
- UI shows countdown timer based on `createdAt` and `deleteAt`

### 4.4 Group Protocol

Current groups use **pairwise connections with broadcast** — every member has a separate duplex connection with every other member:

- Group creator makes introductions between new and existing members
- Each member sends messages to all other members individually
- This creates O(N) traffic per sender per message

**Problems with current design:**
- Linear traffic scaling makes it impractical for large groups
- Fully connected graph is expensive to establish
- Group state (profile, membership, messages) can become inconsistent

**Future design (from RFC):**
- **Epidemic dissemination algorithm** inspired by distributed database replication
- Each member broadcasts to `k` randomly chosen peers (where k = ~7 for 100 members, ~14 for 100K members)
- Messages form a **Merkle DAG** — hash-linked directed acyclic graph for integrity
- Missing messages detected and requested from peers
- No need for full connectivity
- Membership changes require consensus among admins (proposed/accepted/committed states)
- "Super peers" (group owners/admins) handle heavier traffic loads

### 4.5 Message Delivery Receipts

- Agent-level A_RCVD message sent back through the connection
- Contains: received message's agentMsgId + message hash
- Confirmable by sender through RCVD event
- Can be enabled/disabled per conversation
- Receipts are themselves E2E encrypted and sent through the same SMP queues

### 4.6 Link Previews

- Link previews are generated **client-side** — the client fetches the URL and extracts Open Graph metadata
- Preview data (title, description, image thumbnail) is sent as part of the message content
- The recipient's device does NOT fetch the URL — no privacy leak from the recipient
- Image previews are encoded as base64 within the JSON message body
- Preview images are compressed to fit within the 16KB message block

---

## 5. Client Architecture

### 5.1 Haskell Core Library Structure

The core is written in Haskell and compiled to native libraries for each platform:

```
simplex-chat/src/Simplex/
├── Chat.hs              — Main chat logic, command processing
├── Chat/
│   ├── Controller.hs    — State management, event dispatch
│   ├── Messages.hs      — Message types, encoding
│   ├── Store.hs         — Database operations (SQLCipher)
│   ├── Protocol.hs      — Chat protocol messages
│   └── ...

simplexmq/src/Simplex/
├── Messaging/
│   ├── Protocol.hs      — SMP protocol implementation
│   ├── Client.hs        — SMP client (queue operations)
│   ├── Agent.hs         — SMP agent (duplex connections, E2E crypto)
│   ├── Server.hs        — SMP server implementation
│   ├── Crypto.hs        — All cryptographic operations
│   └── Transport.hs     — TLS transport
├── FileTransfer/         — XFTP protocol
└── RemoteControl/        — Remote UI protocol (XRCP)
```

The Haskell core handles:
- All cryptographic operations (Double Ratchet, NaCl, PQ KEM)
- SMP protocol communication
- Database operations via SQLCipher
- Connection management and queue rotation
- File transfer (XFTP)
- Push notification coordination
- WebRTC signaling message routing

### 5.2 Native UI ↔ Haskell Core Communication

**FFI Bridge:**
- The Haskell core is compiled to a C-compatible shared library
- iOS (Swift) and Android (Kotlin) use FFI to call into the Haskell library
- Commands are sent as serialized strings (JSON-like encoding)
- Responses/events are dispatched asynchronously via callbacks

**Communication Pattern:**
```
UI → FFI → chat_send_cmd(command_string) → Haskell Core
Haskell Core → chat_recv_msg() → FFI → UI Event Handler
```

**Key APIs exposed:**
- `createConnection` / `joinConnection` — establish contacts
- `sendMessage` — send message (returns immediately, SENT event later)
- `ackMessage` — acknowledge received message
- `switchConnection` — rotate queues to new server
- `synchronizeRatchet` — re-negotiate E2E encryption

**Desktop:**
- Uses Compose Multiplatform (Kotlin/JVM)
- Same Haskell core compiled for desktop platforms
- WebRTC calls on desktop use a local WebSocket signaling server + browser WebView
- JVM runtime bundled with the app

### 5.3 SQLCipher Database

**Encryption:**
- SQLCipher — drop-in replacement for SQLite with transparent AES-256 encryption
- User provides a passphrase (can be empty for no encryption)
- Migration from plaintext: uses `sqlcipher_export()` with automatic rollback on failure
- Key change: `PRAGMA rekey`
- Custom Haskell bindings via `direct-sqlcipher` and `sqlcipher-simple` (forked from `direct-sqlite`)

**Database Schema Approach:**
- Chat items table with: message content, metadata, `delete_at` for disappearing messages
- Connections table: tracks all SMP queues per contact, with ratchet state
- Groups, members, profiles — all stored locally
- Agent state: queue subscriptions, pending messages, delivery status
- Migration system for schema updates between versions
- Index on `delete_at` for efficient disappearing message cleanup

### 5.4 iOS Push Notifications — The Hard Problem

SimpleX's solution to iOS push notifications is architecturally complex because the core principle is that **the notification itself must not reveal message content or metadata to any server:**

**Architecture:**

```
SMP Server ←→ SimpleX Notification Server (subscriber) ←→ Apple APN ←→ iOS Device
```

**How it works:**

1. Client registers device token with SimpleX Notification Server
2. For each SMP queue, client creates a notification subscription:
   - Sends `NKEY` to SMP server (creates notifier credentials with separate queue ID)
   - Sends `SNEW` to notification server (links SMP notifier ID to device token)
3. When a message arrives at SMP server:
   - SMP server sends `NMSG` to notification subscriber
   - NMSG contains only: E2E encrypted metadata (msgId + timestamp), encrypted with a key the notification server CANNOT decrypt
   - Notification server forwards this encrypted blob as a silent/mutable push notification
4. iOS device receives push, wakes NSE (Notification Service Extension):
   - NSE starts the Haskell core in minimal mode
   - Connects to SMP server, fetches actual message using `GET` command
   - Decrypts message, creates local notification with content
   - Suspends core, closes database

**Critical challenge: NSE ↔ App database contention**
- iOS can run NSE and main app concurrently
- Both access the same SQLCipher database
- Solution: NSE checks shared preferences to detect if app is foregrounded
- NSE creates connections without subscribing (avoids disrupting app's subscriptions)
- New connections are flagged "requiring subscription" for the main app to pick up

**Privacy properties:**
- Apple APN learns only: user has SimpleX app + notification count
- Notification server learns: device token + number of subscribed queues
- Notification server CANNOT learn: message content, sender, queue addresses for messages
- Optional: periodic-only notifications (notification server learns nothing beyond device token)

### 5.5 Multi-Device Support

**Current status (as of 2026):** No true multi-device sync. Instead:

**Remote Control Protocol (XRCP):**
- Mobile acts as "host" — holds the database and all connections
- Desktop acts as "controller" — renders UI and sends commands to mobile
- Connected over local network with E2E encryption
- When desktop is connected, mobile UI shows "connected" status and stops processing
- File transfers are forwarded between devices
- Effectively "remote desktop" for the chat app, not true multi-device

**Design constraints preventing true multi-device:**
- Double Ratchet state is inherently single-device (ratchet advances break other devices)
- No server-side message storage for synchronization
- No user identity to link devices

---

## 6. Server Infrastructure

### 6.1 SMP Server Self-Hosting

SMP servers are fully open-source, designed for self-hosting:

**What you deploy:**
- Single Haskell binary (`smp-server`)
- Generates self-signed certificate chain (offline CA → online cert)
- Listens on port 5223 (default) or 443
- Optional basic auth (password) to restrict who can create queues

**Configuration:**
- In-memory message storage with optional append-only log
- Configurable message TTL
- Configurable queue capacity
- Optional Tor onion service
- No user database, no registration

**Server address format:**
```
smp://<certificate-fingerprint>@<host>:<port>
```

### 6.2 XFTP File Transfer Servers

Separate servers for file transfer:
- HTTP/2 + TLS transport
- Store fixed-size encrypted chunks (64KB, 256KB, 1MB, 4MB)
- In-memory chunk records with optional append-only log
- Auto-expiry of chunks after configurable time
- Basic auth for upload authorization
- Can be self-hosted alongside SMP servers

### 6.3 Federation-Like Relay Discovery

SimpleX is NOT federated in the traditional sense — servers don't talk to each other or discover each other. Instead:

- Each user independently chooses which servers to create queues on
- Users can use any combination of servers (default SimpleX servers, self-hosted, third-party)
- When Alice creates a queue on Server_A and gives Bob the address, Bob's client connects directly to Server_A
- With private routing (2-hop), Bob's client connects to his own server, which proxies to Server_A
- **No server directory, no DNS-based discovery, no federation protocol**
- New servers can be added to client configuration at any time
- Changing servers is transparent — queue rotation moves conversations to new servers

### 6.4 Server Authentication

- Servers use self-signed certificate chains (2-4 certificates deep)
- Offline CA certificate fingerprint is embedded in server address
- Client validates: TLS certificate chain → online cert signed by offline cert → fingerprint matches address
- Session certificates can be rotated on restart without changing server identity
- Optional operator identity certificate for multi-server operators
- No third-party CA trust — entirely self-sovereign PKI

---

## 7. Security Audits

### 7.1 Trail of Bits — First Audit (2022)

- **Scope:** simplexmq library (all crypto + networking)
- **Duration:** 2 engineers, 1 calendar week
- **Key finding:** Vulnerability in key exchange that could allow MITM under specific conditions
  - Fixed in v4.2 — both clients must update
  - New connections created after fix are secure
  - Existing connections secure if both sides sent messages
  - Recommended creating new connections for security-critical contacts

### 7.2 Trail of Bits — Second Audit (2024)

- **Scope:** Cryptographic design review of all protocols (SMP, XFTP, XRCP, PQDR)
- **Focus:** Protocol-level security analysis, not just code review
- Covered the new additions: XFTP file transfer, XRCP remote control, post-quantum Double Ratchet
- Additional security audit planned for early 2025

---

## 8. Lessons for QRChat

### 8.1 What QRChat Can Adopt

**From the Crypto Layer:**
1. **Encrypted headers in Double Ratchet** — hides ratchet state from observers. QRChat could add header encryption to its DR implementation.
2. **Per-queue server encryption** — QRChat's server could re-encrypt messages with a recipient-server shared secret to prevent ciphertext correlation.
3. **Fixed-size message padding** — QRChat should pad all messages to a fixed size to prevent traffic analysis.
4. **Post-quantum KEM augmentation** — The PQDR approach is implementable: on each DH ratchet step, also run a KEM exchange. NTRU-Prime has C/JS implementations available. Consider this for a future version.
5. **Curve448 instead of Curve25519** for DH — higher security margin (224-bit vs 128-bit). TweetNaCl uses Curve25519; upgrading would require switching to a different library.

**From the Protocol Layer:**
6. **Queue rotation** — QRChat should implement server/relay rotation without breaking contacts. This is essential for server migration and privacy.
7. **Out-of-band key exchange** — QRChat already uses QR codes, which is the same approach SimpleX takes. This is a strong foundation.
8. **Message integrity chain** — Each message should reference the hash of the previous message, enabling tamper detection.

**From the Call System:**
9. **Frame-level E2E encryption for WebRTC** — SimpleX uses AES-256-GCM on each video/audio frame via Insertable Streams. QRChat could implement this to add E2E encryption independent of SRTP/DTLS.
10. **SMP-based signaling** — Using the existing E2E encrypted messaging channel for WebRTC signaling eliminates the need for a separate signaling server. QRChat could do the same.
11. **TURN over TLS on port 443** — Better firewall traversal.

**From the Infrastructure:**
12. **Push notification architecture** — SimpleX's approach of sending encrypted metadata (not message content) to the notification server, then having the NSE fetch and decrypt the actual message, is worth studying for QRChat's VoIP push issues.
13. **Self-signed certificate chain** — Eliminates dependency on third-party CAs.

### 8.2 What QRChat Should NOT Copy

1. **Haskell core** — The FFI bridge between Haskell and native platforms is architecturally elegant but adds enormous complexity. QRChat's TypeScript/React Native stack is far more maintainable.
2. **No user identifiers at all** — While privacy-maximizing, it makes group management, multi-device sync, and user experience significantly harder. QRChat's QR-code-based identity is a good balance.
3. **In-memory-only server storage** — SimpleX loses messages on server crash. QRChat's SQLite-based server persistence is more practical.
4. **Current group protocol** — SimpleX's O(N) pairwise broadcast is their acknowledged weakness. QRChat should design a more scalable group protocol from the start.
5. **SQLCipher** — Requires forked Haskell bindings and custom compilation. QRChat's SQLite with application-level encryption (or react-native-sqlcipher) is simpler.

### 8.3 Competitive Analysis Summary

| Feature | SimpleX | QRChat | Advantage |
|---------|---------|--------|-----------|
| User Identity | None at all | QR code based | SimpleX (max privacy) but QRChat (usability) |
| E2E Encryption | DR + PQ KEM (sntrup761) | Double Ratchet (TweetNaCl) | SimpleX (post-quantum) |
| Message Padding | 16KB fixed blocks | Variable | SimpleX |
| Server Trust | Minimal (no accounts, no logs) | More trust required | SimpleX |
| Private Routing | 2-hop onion routing | Direct | SimpleX |
| File Transfer | XFTP (chunked, multi-server) | Direct via messaging | SimpleX |
| Groups | O(N) broadcast (scaling problem) | TBD | Neither (both have issues) |
| Multi-Device | Remote control only | TBD | Neither (both limited) |
| Call E2E | AES-GCM frame encryption | SRTP/DTLS only | SimpleX |
| Tech Stack | Haskell + Swift/Kotlin | React Native + TypeScript | QRChat (dev velocity) |
| Push Notifications | Custom notification server | Firebase + VoIP push | Trade-off (privacy vs reliability) |
| Self-Hosting | Full (SMP + XFTP servers) | Partial (Node.js server) | SimpleX |
| Security Audits | 2x Trail of Bits | None yet | SimpleX |

### 8.4 Priority Recommendations for QRChat

**Immediate (low effort, high impact):**
1. Add message padding to fixed block size
2. Add message integrity chain (prev_msg_hash)
3. Use existing SMP channel for WebRTC signaling instead of separate signaling

**Medium-term (moderate effort):**
4. Implement frame-level E2E encryption for WebRTC calls (Insertable Streams API)
5. Add server-side message re-encryption to prevent ciphertext correlation
6. Implement queue/server rotation protocol

**Long-term (high effort, strategic):**
7. Post-quantum KEM augmentation of Double Ratchet
8. Investigate XFTP-style chunked file transfer for large files
9. Privacy-preserving push notification architecture
10. Commission independent security audit

---

*Research compiled from: SimpleX Chat GitHub (simplex-chat/simplex-chat, simplex-chat/simplexmq), SMP Protocol Specification v9 (2024-06-22), XFTP Protocol Specification v2, SMP Agent Protocol v5, PQDR Specification v1, SimpleX Whitepaper rev.2, 15+ RFCs from docs/rfcs/, iOS/Android source code, Trail of Bits audit reports, SimpleX blog posts (2022-2024).*
