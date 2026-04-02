# Signal Messenger Architecture: Comprehensive Technical Analysis

**Date:** 2026-03-24
**Purpose:** Deep research of Signal's open-source implementation for QRChat feature parity and security improvements

---

## Table of Contents

1. [Signal Protocol Core](#1-signal-protocol-core)
2. [Server Architecture](#2-server-architecture)
3. [iOS Client Architecture](#3-ios-client-architecture)
4. [Message Pipeline (Send/Receive)](#4-message-pipeline)
5. [Group Messaging (Sender Key)](#5-group-messaging)
6. [Media/Attachment Handling](#6-media-attachment-handling)
7. [Voice/Video Calls](#7-voice-video-calls)
8. [Push Notifications](#8-push-notifications)
9. [Sealed Sender (Metadata Protection)](#9-sealed-sender)
10. [Contact Discovery](#10-contact-discovery)
11. [Multi-Device Sync](#11-multi-device-sync)
12. [Key Verification & Key Transparency](#12-key-verification)
13. [Disappearing Messages](#13-disappearing-messages)
14. [Reactions, Replies, Editing](#14-reactions-replies-editing)
15. [Message Retry & Error Recovery](#15-message-retry)
16. [Spam Prevention & Rate Limiting](#16-spam-prevention)
17. [Backup/Restore](#17-backup-restore)
18. [Post-Quantum Upgrades](#18-post-quantum)
19. [Recommendations for QRChat](#19-recommendations-for-qrchat)

---

## 1. Signal Protocol Core

### 1.1 X3DH Key Agreement (Extended Triple Diffie-Hellman)

X3DH establishes a shared secret between two parties who have never communicated, even when one party is offline. It provides **mutual authentication**, **forward secrecy**, and **cryptographic deniability**.

#### Key Types

| Key | Owner | Lifetime | Purpose |
|-----|-------|----------|---------|
| Identity Key (IK) | Both | Permanent | Long-term authentication |
| Signed Prekey (SPK) | Recipient | Rotated periodically | Forward secrecy anchor |
| One-Time Prekey (OPK) | Recipient | Single use, deleted after consumption | Additional forward secrecy |
| Ephemeral Key (EK) | Sender | Single use, per session | Fresh randomness |

#### Protocol Flow

**Phase 1 -- Key Publication (Bob, offline):**
Bob uploads to the server:
- Identity key IK_B (once)
- Signed prekey SPK_B + Sig(IK_B, Encode(SPK_B)) (rotated periodically)
- Set of one-time prekeys OPK_B1, OPK_B2, ... (replenished as consumed)

**Phase 2 -- Initial Message (Alice, initiating):**
1. Alice fetches Bob's "prekey bundle" from server: {IK_B, SPK_B, Sig, OPK_B}
2. Alice verifies SPK_B signature using IK_B
3. Alice generates ephemeral keypair EK_A
4. Alice computes four DH shared secrets:

```
DH1 = DH(IK_A, SPK_B)    -- mutual authentication
DH2 = DH(EK_A, IK_B)     -- mutual authentication
DH3 = DH(EK_A, SPK_B)    -- forward secrecy
DH4 = DH(EK_A, OPK_B)    -- additional forward secrecy (optional)
```

5. Derive session key: `SK = HKDF(DH1 || DH2 || DH3 || DH4)`
6. Alice sends initial message: {IK_A, EK_A, OPK_B_id, encrypted_message}

**Phase 3 -- Reception (Bob):**
Bob performs the same DH calculations to derive SK, then decrypts.

**When One-Time Prekeys Are Exhausted:**
The protocol falls back to 3-DH (without DH4). Forward secrecy then depends solely on SPK rotation frequency -- an important reason to rotate SPKs regularly.

#### QRChat Relevance
QRChat currently uses TweetNaCl for key exchange. Signal's X3DH model with prekeys is specifically designed for asynchronous messaging where one party is offline -- a critical feature QRChat should adopt to avoid the "both parties must be online" limitation.

---

### 1.2 Double Ratchet Algorithm

The Double Ratchet provides **per-message forward secrecy** and **break-in recovery** (post-compromise security). It combines two ratcheting mechanisms:

#### Symmetric-Key Ratchet (KDF Chain)
- Each message gets a unique **message key** derived from a **chain key**
- Chain key advances: `CK_new = HMAC-SHA256(CK, 0x02)`
- Message key derived: `MK = HMAC-SHA256(CK, 0x01)`
- Message keys are used exactly once for AEAD encryption (AES-256-CTR/CBC + HMAC-SHA256)
- Old chain keys are deleted; message keys may be stored for out-of-order delivery

#### Diffie-Hellman Ratchet (Asymmetric)
- Parties attach new ephemeral DH public keys to messages ("ratchet keys")
- Each new DH output feeds into the root chain via HKDF, producing new sending/receiving chain keys
- Creates a "ping-pong" pattern: Alice sends with her ratchet key, Bob responds with a new ratchet key
- Ensures that even if an attacker compromises current state, they cannot derive future keys (break-in recovery)

#### Key Hierarchy

```
Root Key (RK) --[DH output + HKDF]--> New RK + Chain Key (CK)
Chain Key (CK) --[HMAC]--> Message Key (MK) + New CK
```

#### Out-of-Order Message Handling
- Each message header contains: ratchet public key, message number N, previous chain length PN
- Recipients store skipped message keys indexed by (ratchet_key, message_number)
- MAX_SKIP constant limits stored keys to prevent DoS attacks
- Skipped keys are stored until used or expired

#### Header Encryption (Optional)
- Headers can be encrypted using symmetric header keys derived alongside chain keys
- Prevents eavesdroppers from observing message ordering and session membership
- Uses "current header key" and "next header key" for ratchet step signaling

#### QRChat Relevance
QRChat uses TweetNaCl's box/secretbox for encryption. The Double Ratchet provides dramatically better security properties: per-message forward secrecy (compromise of one key doesn't reveal other messages) and post-compromise security (the system self-heals after a breach). This is the single most impactful security upgrade QRChat could implement.

---

## 2. Server Architecture

### 2.1 Technology Stack

Signal Server is a Java application built on **Dropwizard** framework, exposing three client interfaces:
- **REST API** (Jersey controllers) -- synchronous operations
- **WebSocket** -- persistent connections for real-time message delivery
- **gRPC** -- modern RPC interface for selected services

### 2.2 Two-Tier Message Storage

Signal uses a cache-first architecture:

**Tier 1 -- Redis (MessagesCache):**
- All incoming messages write to Redis first
- 5-10 minute TTL for active delivery scenarios
- Lua scripts manage queue operations (insert, expire, metadata tracking)
- Pub/Sub coordinates message availability across distributed server instances
- Rate limiting state stored across 45+ limit types

**Tier 2 -- DynamoDB (MessagesDynamoDb):**
- `MessagePersister` background worker asynchronously migrates messages from Redis to DynamoDB
- 30-day TTL on stored messages (previously 7-day)
- Old PostgreSQL implementation enforced 1,000 message limit per device

**Message Retrieval Flow:**
When fetching pending messages, the system queries BOTH Redis cache AND DynamoDB to include messages that haven't been persisted yet.

### 2.3 WebSocket Architecture

```
Client --> WebSocket Connection --> AuthenticatedConnectListener (validates credentials)
                                --> WebSocketConnection (persistent bidirectional)
                                --> Redis Pub/Sub (cross-instance notification)
```

- Device connections stored in memory maps indexed by device identifier
- `RedisMessageAvailabilityManager` notifies across distributed instances
- Supports authenticated messaging (`/v1/websocket/`) and device provisioning (`/v1/websocket/provisioning/`)

### 2.4 Message Delivery Flow

```
Sender --> Server API (REST or WebSocket)
           |
           v
       Is recipient online?
       /              \
    YES                NO
     |                  |
  WebSocket          Redis Queue --> MessagePersister --> DynamoDB
  direct delivery       |
                    PushNotificationScheduler
                        |
                    APNSender / FcmSender
                    (empty notification -- wake only)
```

### 2.5 Key Management Server-Side

`KeysManager` orchestrates cryptographic material:
- Single-use EC prekeys (DynamoDB)
- Paged post-quantum KEM bundles (DynamoDB metadata + S3 storage)
- "Last resort" signed prekeys (repeated-use fallback)

### 2.6 External Integrations

- **Storage:** AWS S3, Google Cloud Storage, DynamoDB
- **Push:** APNs, Firebase Cloud Messaging
- **Verification:** Registration Service, Key Transparency Service
- **Recovery:** Secure Value Recovery (SVR2/SVRB)
- **Calling:** Cloudflare TURN for WebRTC relaying
- **Payments:** Stripe, Braintree, Google Play Billing, Apple App Store
- **SMS:** Twilio for verification

### QRChat Relevance
QRChat uses a single Node.js server. The key takeaways:
- **Adopt a two-tier storage model**: Use Redis for hot message queue + persistent DB for durability
- **WebSocket-first delivery**: QRChat already uses WebSocket, but should add Redis Pub/Sub for horizontal scaling
- **Push-to-sync notifications**: Send EMPTY push notifications, then let the app fetch encrypted content over the secure channel
- **Message TTL**: Implement automatic message expiration (30 days) to limit exposure

---

## 3. iOS Client Architecture

### 3.1 High-Level Structure

Signal iOS uses a layered architecture with three application targets:
- **Main app** -- primary messaging interface
- **Share Extension** -- share content from other apps (30-second execution window)
- **Notification Service Extension (NSE)** -- decrypt push notification content in background (~30 seconds)

All three share core frameworks (`SignalServiceKit`, `SignalUI`) through `AppSetup` initialization.

### 3.2 Core Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| LibSignalClient | 0.86.8 | Signal Protocol (Rust-based) |
| SignalRingRTC | 2.61.0 | WebRTC voice/video (Rust-based) |
| GRDB.swift | 5.26.0 | SQLite wrapper |
| SQLCipher | 4.6.1 | AES-256 database encryption |

### 3.3 Database Architecture

- `SDSDatabaseStorage` -- primary read/write transaction interface
- SQLCipher encrypts all data at rest using AES-256
- Encryption key stored in iOS Keychain
- `GRDBSchemaMigrator` runs 100+ incremental migrations
- `DatabaseChangeObserver` tracks changes for UI reactivity

**Major Tables:**
- `model_TSThread` -- conversations (1-1 and groups)
- `model_TSInteraction` -- messages, calls, info events
- `model_TSAttachment` / `Attachment` -- media metadata
- `model_SignalRecipient` -- recipient identity information
- `indexable_text_fts` -- full-text search index (FTS5)

### 3.4 Networking

- `NetworkManager` -- HTTP REST API requests
- `ChatConnectionManager` -- persistent WebSocket via `libsignal-net`
- Push notification fallback if WebSocket delivery fails
- `OWSRequestFactory` constructs API calls

### 3.5 Service Singletons

**Legacy (SSKEnvironment):** databaseStorage, messageSenderJobQueue, blockingManager, profileManager, contactsManager

**Modern (DependenciesBridge):** tsAccountManager, attachmentStore, threadStore, recipientDatabaseTable, backupExportJob

### QRChat Relevance
- QRChat should adopt **SQLCipher** for database encryption at rest (currently using plain SQLite)
- The **Notification Service Extension** pattern is critical: decrypt message content in the NSE before displaying, so push payloads remain empty/opaque
- The **DatabaseChangeObserver** pattern (reactive UI updates from DB changes) is more robust than QRChat's current state management

---

## 4. Message Pipeline (Send/Receive)

### 4.1 Sending Flow

```
1. User composes message in ConversationViewController
2. MessageSender prepares and encrypts via LibSignalClient
3. SignalProtocolStore manages encryption keys (Double Ratchet state)
4. For each recipient device:
   a. Encrypt message content with per-device session
   b. Optionally wrap in sealed sender envelope
5. SignalServiceClient transmits via REST to server
6. Server routes to recipient (WebSocket if online, push + queue if offline)
```

### 4.2 Receiving Flow

```
1. Push notification triggers NotificationService Extension (NSE)
2. NSE fetches encrypted message from server via WebSocket/REST
3. MessageProcessor decrypts using LibSignalClient
4. InteractionStore persists decrypted message to encrypted SQLite
5. DatabaseChangeObserver notifies UI components
6. ConversationViewController displays via reactive updates
```

### 4.3 Message Encryption Details

- **Encryption:** AES-256-CTR or ChaCha20
- **Authentication:** HMAC-SHA256
- **Key derivation:** HKDF with SHA-256 produces 80 bytes (32-byte encryption key, 32-byte auth key, 16-byte IV)
- **Each message includes:** version, ephemeral ratchet key, counter, ciphertext, MAC

### QRChat Relevance
QRChat should implement the NSE-based decryption pattern. Currently, if the app receives a push notification, the notification content either leaks plaintext or shows a generic "New message" -- the NSE approach decrypts in the extension process and shows the actual content securely.

---

## 5. Group Messaging (Sender Key Protocol)

### 5.1 How Sender Key Works

Instead of encrypting a message individually for each group member (O(n) encryptions), Sender Key uses a single symmetric key per sender per group:

```
Sender generates:
  - Random 32-byte Chain Key
  - Ed25519 Signature Key pair

For each message:
  1. MK = HMAC-SHA256(Chain Key, 0x01)    -- derive message key
  2. CK = HMAC-SHA256(Chain Key, 0x02)    -- advance chain key
  3. Encrypt message with AES-256-CBC using MK
  4. Sign ciphertext with Signature Key
```

### 5.2 Key Distribution

- When first sending to a group, sender generates a Sender Key and distributes it to each member individually (encrypted 1-to-1 via Signal Protocol sessions)
- New members receive Sender Keys from existing members -- cannot decrypt past messages
- When ANY member leaves (or a device is removed), ALL group participants clear their Sender Key and generate new ones

### 5.3 Group V2 Features

- Server-enforced membership consistency via Group Master Key
- Prevents stealthy additions/removals
- Access control (who can add members, edit info)
- Group link invitations with approval workflow

### 5.4 Security Properties

- **Forward secrecy:** Hash ratchet of chain key (messages can't be decrypted backward)
- **No future secrecy per-message:** Keys only rotate when group membership changes (not per-message like Double Ratchet)
- **Authentication:** Each sender signs their messages

### QRChat Relevance
QRChat currently has no group messaging. Implementing Sender Key would be the scalable approach -- O(1) encryption per message instead of O(n). The key rotation on member departure is critical for security.

---

## 6. Media/Attachment Handling

### 6.1 Encryption

Each attachment is encrypted independently with a **per-attachment random key**:
- Random AES-256 key generated for each attachment
- Encrypted with AES-256-CBC + HMAC-SHA256
- The encryption key and HMAC are sent inside the Signal Protocol message (encrypted end-to-end)
- The encrypted blob is uploaded to Signal's CDN separately

### 6.2 Upload/Download Flow

```
Sending:
1. Generate random AES-256 key + HMAC key for attachment
2. Encrypt attachment locally with AES-256-CBC
3. Compute HMAC over encrypted data
4. Upload encrypted blob to CDN (server never sees plaintext)
5. Send message containing: CDN URL, AES key, HMAC key, file metadata
   (all encrypted within the Signal Protocol message)

Receiving:
1. Decrypt message to get CDN URL + keys
2. Download encrypted blob from CDN
3. Verify HMAC
4. Decrypt with AES key
5. Store decrypted file locally (in encrypted database/filesystem)
```

### 6.3 CDN Architecture

- **Transit CDN:** Attachments available for 45 days for re-download
- **Backup CDN:** For paid tier, server copies encrypted attachments from transit CDN to backup CDN with additional encryption layer
- Media stored at paths like `https://cdn.signal.org/attachments/`
- Encrypted profiles stored at `https://cdn.signal.org/profiles/`

### 6.4 Limits

- iOS enforces media sizing limits
- Files up to ~100 MB supported
- Progressive download for large files
- Background task scheduling via `BGTaskScheduler`

### QRChat Relevance
QRChat should adopt the pattern of **per-attachment random keys** sent inside the encrypted message. This decouples attachment storage from the encryption protocol -- the CDN/server stores only opaque encrypted blobs. QRChat could use any object storage (S3, Cloudflare R2) for encrypted attachment hosting.

---

## 7. Voice/Video Calls

### 7.1 Architecture Overview

Signal uses **RingRTC**, an open-source Rust library wrapping WebRTC, for all calling functionality.

**1-to-1 Calls:**
- Signaling (offer/answer SDPs, ICE candidates) sent through Signal Protocol messaging channel
- This binds call security to the existing encrypted messaging infrastructure
- No separate SRTP key exchange needed -- keys derived from the secure channel
- Audio codec: Opus in **CBR mode** (constant bitrate to prevent speech pattern leakage via packet sizes)

**Group Calls (SFU):**
- Custom **Selective Forwarding Unit (SFU)** written in Rust
- SFU receives encrypted media and forwards without decrypting
- Scales to 40+ participants
- Frame-level encryption: contents encrypted BEFORE being divided into RTP packets

### 7.2 Group Call Key Management

```
When participant joins:
1. Generate new media encryption key
2. Send key to all other participants via Signal Protocol messages
3. Wait 3 seconds for propagation before using key

When any participant joins or leaves:
1. Every remaining participant generates a new key
2. Distribute via Signal Protocol messages
3. Switch to new key after 3 seconds
```

This ensures:
- Participants cannot decrypt media from before they joined
- Participants cannot decrypt media after they leave
- Forward and backward secrecy for call media

### 7.3 Simulcast & Rate Adaptation

- Each participant sends multiple video resolutions simultaneously (simulcast)
- SFU rewrites RTP headers (SSRC, sequence numbers, timestamps, VP8 Picture IDs) to merge layers into one timeline
- Congestion control: googcc algorithm with transport-cc feedback
- Rate allocation: prioritize smaller layers, prefer higher-requested resolutions

### 7.4 iOS CallKit Integration

- Incoming calls answered from lock screen via CallKit
- Native iOS call UI experience
- Optional: users can disable CallKit while keeping new calling system
- ICE forking: caller sends offer to ALL recipient devices, first to answer wins

### QRChat Relevance
QRChat already uses WebRTC for calls. Key improvements to adopt:
- **CBR codec mode** to prevent traffic analysis
- **Signal channel for call signaling** instead of separate signaling server
- **Frame-level encryption for group calls** when implementing group calling
- **ICE forking** for multi-device ringing

---

## 8. Push Notifications

### 8.1 Push-to-Sync Architecture

Signal's approach is fundamentally different from most messengers:

```
Server --> APNs/FCM: EMPTY notification (no content, no metadata)
                     |
                     v
Client receives empty push --> wakes app/NSE
                     |
                     v
NSE opens WebSocket --> fetches encrypted message from Signal server
                     |
                     v
NSE decrypts message locally --> displays notification with content
```

**Why this matters:**
- Apple/Google see ZERO message content in push payloads
- No sender information, no preview, no metadata in the push
- The push serves purely as a "wake up" signal
- Actual content fetched over Signal's own encrypted channel

### 8.2 iOS Implementation

- `PushRegistrationManager` coordinates with APNs
- **Notification Service Extension (NSE)** decrypts content before display
- ~30 second execution window for NSE
- Falls back to WebSocket if push delivery fails

### 8.3 Android Implementation

- FCM push with completely empty payload
- App wakes and fetches data from Signal server
- Local notification constructed with decrypted content

### QRChat Relevance
This is a CRITICAL privacy feature QRChat should implement immediately. If QRChat sends any message content (even encrypted) through APNs/FCM, Apple/Google can potentially access it. The correct pattern:
1. Register for silent/background push notifications
2. Send empty pushes from server
3. Implement NSE that fetches + decrypts + displays
4. Never put message content in push payload

---

## 9. Sealed Sender (Metadata Protection)

### 9.1 The Problem

Even with end-to-end encryption, the server traditionally sees WHO is messaging WHOM (the "from" field on the envelope). Sealed sender removes this metadata.

### 9.2 How It Works

**Layer 1 -- Normal Signal Protocol encryption:**
Message content encrypted as usual with Double Ratchet session keys.

**Layer 2 -- Sealed sender envelope:**
```
1. Sender obtains short-lived "sender certificate" from Signal
   (contains: phone number, public identity key, expiration)
2. Sender generates ephemeral Curve25519 keypair
3. Sender performs DH with recipient's identity key
4. Sender encrypts {sender_certificate + Signal_Protocol_ciphertext}
   using the DH-derived key
5. Sends envelope to server WITHOUT any "from" field
```

**Recipient decryption:**
```
1. Recipient decrypts outer envelope using their identity key
2. Extracts and validates sender certificate (checks expiration, identity)
3. Decrypts inner Signal Protocol message as normal
```

### 9.3 Abuse Prevention (Delivery Tokens)

- Each user derives a **96-bit delivery token** from their profile key
- Registers token with Signal server
- To send sealed-sender messages, sender must prove knowledge of recipient's delivery token
- Since profile keys are only shared with contacts, this restricts anonymous messaging to known contacts
- Optional setting: accept sealed sender from non-contacts (trades security for flexibility)

### 9.4 Limitations

- Protects sender's phone number but NOT IP address (use VPN/Tor for that)
- Server can still observe timing patterns and IP addresses
- "Incremental step" toward full metadata resistance

### QRChat Relevance
QRChat's server currently sees sender and recipient for every message. Implementing sealed sender would significantly improve privacy:
- Server would only know the RECIPIENT, not the sender
- Combined with QR-based contact exchange, QRChat could achieve even stronger metadata protection than Signal since it doesn't rely on phone numbers

---

## 10. Contact Discovery

### 10.1 The Problem

To find which contacts use Signal, the app needs to check phone numbers against Signal's database -- but uploading your entire contact list to Signal would be a massive privacy violation.

### 10.2 SGX Secure Enclave Solution

```
1. Client performs remote attestation with SGX enclave on Signal server
   (verifies the enclave runs the expected open-source code)
2. Client establishes encrypted connection directly to enclave
   (bypasses host OS entirely)
3. Client sends encrypted phone number hashes to enclave
4. Enclave builds oblivious hash table from submitted contacts
5. Enclave iterates through ALL registered users (constant-time)
   (uses oblivious RAM to prevent memory access pattern leakage)
6. Returns encrypted intersection to client
7. Server/OS learns NOTHING about which contacts matched
```

### 10.3 Oblivious Operations

The enclave iterates through every cache line and checks all contacts against each line regardless of relevance, creating uniform memory access patterns. This prevents the host OS from inferring anything from memory access patterns.

### QRChat Relevance
QRChat uses QR codes for contact exchange, which is actually MORE private than Signal's approach -- no server-side contact discovery needed at all. This is a genuine advantage QRChat should emphasize. However, for users who want to find contacts by phone number or username, consider implementing a privacy-preserving lookup using techniques like private set intersection.

---

## 11. Multi-Device Sync

### 11.1 Architecture

- Each linked device maintains **independent encryption state** (own identity keys, own ratchet sessions)
- Per-device encryption preserves forward secrecy
- Limit of 5 linked devices
- Primary device (phone) is the authority

### 11.2 Linking Flow

```
1. New device generates provisioning address + Curve25519 keypair
2. Embeds public key in QR code
3. Primary device scans QR code
4. Primary creates "provisioning message" encrypted with new device's public key:
   - Shared account keys
   - One-time linking token (proves permission to join account)
5. Transfer compressed, encrypted archive:
   - All text messages
   - Last 45 days of media (pointers to CDN, not re-uploaded)
   - Uses random one-time-use 256-bit AES key
6. New device decrypts locally -- Signal servers cannot access content
7. New device registers its own identity keys with server
```

### 11.3 Message Sync

- Messages encrypted separately for EACH device's session
- Server maintains per-device message queues
- Delivery receipts sent per-device

### 11.4 Call Handling (ICE Forking)

- Caller sends offer to ALL recipient devices simultaneously
- First device to answer wins
- Other devices stop ringing

### QRChat Relevance
QRChat is currently single-device only. To add multi-device:
- Each device needs its own encryption keypair
- Server must maintain per-device message queues
- Messages must be encrypted for each device separately
- The QR-code-based linking flow Signal uses would fit QRChat's existing QR paradigm perfectly

---

## 12. Key Verification & Key Transparency

### 12.1 Safety Numbers

Each 1-to-1 conversation has a unique "safety number" derived from both parties' identity keys:
- Displayed as a long numeric string and QR code
- Both parties see the same number
- If numbers match, no MITM attack is occurring
- Changes when either party's identity key changes (new device, reinstall)

### 12.2 Key Transparency (2024-2025 Development)

Signal is building an **auditable transparency log** for identity keys:

**Architecture:**
- `KeyTransparencyQueryService` -- read-only, clients query the log
- `KeyTransparencyService` -- read/write, handles auditing + log updates
- `key-transparency-auditor` -- third-party auditor reference implementation

**How it works:**
- Log tree (append-only) + prefix trees (efficient lookups)
- Auditor streams updates from key transparency service
- Maintains condensed view of prefix and log trees
- Periodically signs tree heads, confirming consistency
- Clients can verify their identity key hasn't been secretly changed by the server

**Goal:** Automatic verification that end-to-end encryption hasn't been tampered with, without requiring manual QR code scanning.

### QRChat Relevance
QRChat should implement safety numbers (or equivalent fingerprint verification) as a minimum. The key transparency log is more advanced but provides the gold standard: automatic detection if the server tries to serve fake keys for MITM attacks.

---

## 13. Disappearing Messages

### 13.1 Implementation

- **Client-side enforcement only** -- server never stores, interprets, or enforces expiration
- Timer value embedded in the encrypted message envelope at send time
- Cannot retroactively add timer to already-sent messages
- Available durations: 30 seconds to 4 weeks

### 13.2 Timer Behavior

- **Sent messages:** Timer starts after message is sent
- **Received messages:** Timer starts after message is read (opened)
- Timer configuration is per-conversation, agreed upon by both parties
- Default timer can be set for all new conversations

### 13.3 Deletion Process

- When timer expires, app calls `deleteFromDatabase()`
- Android: JobScheduler (probabilistic intervals)
- iOS: Background App Refresh (not real-time)
- NOT guaranteed if device is offline, asleep, or killed by OS

### 13.4 Exclusions

- View-once messages and messages with timers under 24 hours excluded from backups
- Deletion is best-effort, not cryptographic guarantee

### QRChat Relevance
QRChat should implement disappearing messages with client-side timers. The key insight: embed the timer in the encrypted payload so the server never knows about expiration policies. Important to communicate to users that this is best-effort deletion, not a cryptographic guarantee.

---

## 14. Reactions, Replies, Editing

### 14.1 Reactions

- Emoji reactions sent as separate encrypted messages
- Reference original message by timestamp
- All group members see reactions below the message
- Notification sent only to original message author

### 14.2 Quote Replies

- Reference original message by `quoteTimestamp`
- Include snippet of quoted message in the reply payload
- Displayed as inline quote above the reply

### 14.3 Message Editing

- Uses `editTimestamp` to reference the original message
- Edit history may be visible to recipient
- Edits are separate encrypted messages that replace the original display

### QRChat Relevance
All three features use the pattern of referencing messages by timestamp. QRChat should implement a message ID system (timestamp + sender is sufficient) for reactions, replies, and future editing support.

---

## 15. Message Retry & Error Recovery (Sesame Algorithm)

### 15.1 Session Management

The Sesame algorithm manages multiple concurrent sessions per device:

**State hierarchy:**
```
UserRecord (indexed by UserID)
  --> DeviceRecord (indexed by DeviceID)
      --> Active Session (one per device)
      --> Inactive Sessions (ordered list)
```

### 15.2 Retry Protocol

```
1. Recipient receives undecryptable message
2. Recipient sends unencrypted retry request containing MessageID
3. Sender looks up MessageRecord (stores plaintext + metadata)
4. Sender re-encrypts with current active session
5. Sender creates new session if original session is orphaned
6. Delivery receipt confirms successful delivery --> sender deletes MessageRecord
```

**Limits:** Devices impose a maximum retry count to prevent abuse.

### 15.3 Conflict Resolution

When both parties simultaneously create new sessions:
- Receiving device activates the incoming session
- Previous active session becomes head of inactive list
- Message exchange naturally converges both parties to matching sessions

### 15.4 Failure Handling

- Failed decryptions trigger complete state rollback (no partial state)
- Stale records (deleted users/devices) retained for MAXLATENCY period
- Authentication requires manual public key verification

### QRChat Relevance
QRChat currently has no retry mechanism for failed decryption. Implementing MessageRecord storage + retry requests would eliminate the current "message lost" failure mode. The Sesame algorithm's automatic session convergence is particularly important for multi-device support.

---

## 16. Spam Prevention & Rate Limiting

### 16.1 Privacy-First Approach

Signal cannot inspect message content or analyze social graphs. Instead:

**Behavioral Signals:**
- Repeated spam reports against specific accounts
- Detection of automated network traffic patterns

**Proof of Humanity:**
- Accounts exceeding server-side request thresholds must complete CAPTCHA
- Challenges issued within the Signal app
- No messages sent until challenge completed

### 16.2 Rate Limiting

- 45+ rate limit types stored in dedicated Redis cluster
- Runtime-adjustable configuration (no redeployment needed)
- HTTP 413 response when limits exceeded
- Per-endpoint, per-account, and global limits

### 16.3 Reporting Mechanism

When user clicks "Report Spam and Block":
- Device sends ONLY: sender's phone number + one-time anonymous message ID
- No message content, no metadata, no additional identifying information

### 16.4 Client-Side Protections

- Profile pictures from unknown senders are blurred
- URL linkification disabled on message request screens
- Reduces social engineering without server-side content inspection

### 16.5 Private Server Component

Signal's spam detection logic is the ONLY private code in their infrastructure. Unlike encryption protocols (provably secure even when public), spam detection requires secrecy to be effective.

### QRChat Relevance
QRChat should implement:
- Redis-backed rate limiting on the Node.js server (per-user, per-endpoint)
- CAPTCHA challenges for suspicious accounts
- Client-side protections (blur unknown profiles, disable link previews from unknown senders)
- Spam reporting that sends minimal metadata

---

## 17. Backup/Restore

### 17.1 Signal Secure Backups (2025)

**Encryption:**
- 64-character cryptographically secure recovery key generated on device
- Recovery key NEVER shared with Signal servers
- Backup archive is end-to-end encrypted with this key

**Storage Tiers:**
- **Free:** All text messages + last 45 days of media
- **Paid ($1.99/month):** Full media history beyond 45 days

**Exclusions:**
- Disappearing messages with timer < 24 hours
- View-once messages

**Privacy:**
- Backups disabled by default
- Cannot be linked to any user account
- Even payments designed to be unlinkable to user accounts

### 17.2 Linked Device Transfer

- Compressed, encrypted archive sent device-to-device
- One-time-use 256-bit AES key
- Media transferred as CDN pointers (not re-uploaded)
- Server sees encrypted blob, cannot access content

### QRChat Relevance
QRChat should implement encrypted backup with a user-generated recovery key. The key insight: NEVER store the recovery key server-side. Use HKDF to derive encryption keys from a user-chosen passphrase or generated recovery key, encrypt the entire database, and upload to the user's own cloud storage (iCloud/Google Drive).

---

## 18. Post-Quantum Upgrades

### 18.1 PQXDH (Post-Quantum Extended Diffie-Hellman)

Signal upgraded X3DH to PQXDH in 2023-2024 to defend against "Harvest Now, Decrypt Later" attacks.

**Hybrid Approach:**
PQXDH combines both classical and post-quantum cryptography:
- **X25519** (elliptic curve) -- proven classical security
- **CRYSTALS-Kyber** (lattice-based KEM) -- post-quantum security (NIST standardized)

Both shared secrets are combined via HKDF, requiring an attacker to break BOTH.

**Additional Key Types:**
- Signed last-resort PQ prekey (PQSPK_B) -- fallback KEM key
- Signed one-time PQ prekeys (PQOPK_B1, ...) -- per-session KEM keys

**Key Agreement:**
```
DH1 = DH(IK_A, SPK_B)
DH2 = DH(EK_A, IK_B)
DH3 = DH(EK_A, SPK_B)
DH4 = DH(EK_A, OPK_B)     [optional, EC]
(CT, SS) = KEM-Encaps(PQPK_B)  [Kyber encapsulation]

SK = HKDF(DH1 || DH2 || DH3 || DH4 || SS)
```

### 18.2 SPQR (Sparse Post-Quantum Ratchet, 2025)

Signal introduced SPQR to extend post-quantum security beyond the initial handshake into the ongoing Double Ratchet:
- Periodically injects post-quantum KEM operations into the DH ratchet
- Maintains bandwidth efficiency (KEM operations are "sparse," not every message)
- Combined with Double Ratchet, provides strong post-quantum security for the entire session

### 18.3 Timeline

- 2023: PQXDH deployed for new chats
- 2024: X3DH disabled for new chats, PQXDH required
- 2025: SPQR deployed, existing chats upgraded; Triple Ratchet protocol released (October 2025)

### QRChat Relevance
Post-quantum is not an immediate priority for QRChat, but the hybrid approach is worth noting: when upgrading, ADD post-quantum on top of existing classical crypto rather than replacing it. This provides defense-in-depth without risking regression if the PQ algorithm has unforeseen weaknesses.

---

## 19. Recommendations for QRChat

### Priority 1: CRITICAL Security Improvements

| # | Feature | Signal Reference | QRChat Impact | Effort |
|---|---------|-----------------|---------------|--------|
| 1 | **Empty push notifications** | Push-to-sync via NSE | Stops Apple/Google from seeing any message data | Medium |
| 2 | **Per-message encryption keys** (Double Ratchet or equivalent) | Double Ratchet Algorithm | Forward secrecy + post-compromise security | High |
| 3 | **Database encryption at rest** | SQLCipher (AES-256) | Protects data on stolen/seized devices | Low |
| 4 | **Message retry on decryption failure** | Sesame Algorithm | Eliminates "lost message" failures | Medium |
| 5 | **Server rate limiting** | Redis-backed 45+ limit types | Prevents abuse, spam, DoS | Low |

### Priority 2: Important Privacy Features

| # | Feature | Signal Reference | QRChat Impact | Effort |
|---|---------|-----------------|---------------|--------|
| 6 | **Sealed sender** | Sealed sender envelopes | Server can't see who messages whom | High |
| 7 | **Safety numbers / key verification** | Safety Numbers | Users can verify no MITM | Medium |
| 8 | **Disappearing messages** | Client-side timers in payload | Ephemeral messaging option | Medium |
| 9 | **Per-attachment encryption keys** | Random AES-256 per attachment | Decouple media storage from message encryption | Medium |
| 10 | **Message TTL on server** | 30-day DynamoDB TTL | Limit exposure of queued messages | Low |

### Priority 3: Feature Parity

| # | Feature | Signal Reference | QRChat Impact | Effort |
|---|---------|-----------------|---------------|--------|
| 11 | **Group messaging** | Sender Key protocol | Core feature for adoption | High |
| 12 | **Reactions and replies** | Timestamp-based references | Modern messaging UX | Low |
| 13 | **Typing indicators** | Encrypted via Signal Protocol | Real-time presence | Low |
| 14 | **Read/delivery receipts** | Mandatory delivery, optional read | Message status feedback | Low |
| 15 | **CBR codec for calls** | Opus CBR mode | Prevent traffic analysis on calls | Low |

### Priority 4: Advanced Features

| # | Feature | Signal Reference | QRChat Impact | Effort |
|---|---------|-----------------|---------------|--------|
| 16 | **Multi-device support** | Per-device sessions + sync | Use on phone + desktop | Very High |
| 17 | **Encrypted backup/restore** | 64-char recovery key | Data portability | High |
| 18 | **Key transparency** | Auditable transparency log | Auto-detect MITM by server | Very High |
| 19 | **Group video calls (SFU)** | RingRTC + custom SFU | Group calling support | Very High |
| 20 | **Post-quantum crypto** | PQXDH + SPQR | Future-proof against quantum | High |

### QRChat's Existing Advantages Over Signal

1. **QR-based contact exchange** -- more private than phone-number-based discovery; no server-side contact matching needed
2. **No phone number requirement** -- Signal requires phone numbers; QRChat could offer truly anonymous accounts
3. **Simpler architecture** -- easier to audit, fewer attack surfaces
4. **React Native** -- single codebase for iOS + Android (Signal maintains separate native apps)

### Architectural Recommendations

1. **Adopt libsignal**: Consider integrating Signal's open-source `libsignal` library (available as Swift/Java/TypeScript bindings over Rust core) rather than reimplementing the protocol. This gives you the Double Ratchet, X3DH/PQXDH, Sealed Sender, and Sender Key for free, with formal verification.

2. **Two-tier message storage**: Replace single-DB approach with Redis (hot) + persistent DB (cold). All incoming messages hit Redis first, background worker persists to permanent storage.

3. **WebSocket-first, push-second**: Use WebSocket as primary delivery channel, push notifications only as wake-up signals with empty payloads.

4. **Notification Service Extension**: Implement iOS NSE to decrypt messages in the extension process. This is the only way to show notification content without leaking it to Apple.

5. **CDN for attachments**: Upload encrypted attachment blobs to object storage (S3/R2), send decryption keys inside the encrypted message. Server never sees plaintext media.

---

## Sources

### Official Signal Documentation
- [X3DH Key Agreement Protocol](https://signal.org/docs/specifications/x3dh/)
- [Double Ratchet Algorithm](https://signal.org/docs/specifications/doubleratchet/)
- [PQXDH Key Agreement Protocol](https://signal.org/docs/specifications/pqxdh/)
- [Sesame Algorithm (Session Management)](https://signal.org/docs/specifications/sesame/)
- [Signal Documentation Hub](https://signal.org/docs/)

### Signal Blog Posts
- [Sealed Sender](https://signal.org/blog/sealed-sender/)
- [Private Contact Discovery](https://signal.org/blog/private-contact-discovery/)
- [Keeping Spam Off Signal](https://signal.org/blog/keeping-spam-off-signal/)
- [A Synchronized Start for Linked Devices](https://signal.org/blog/a-synchronized-start-for-linked-devices/)
- [How to Build Encrypted Group Calls](https://signal.org/blog/how-to-build-encrypted-group-calls/)
- [Video Calls Beta](https://signal.org/blog/signal-video-calls-beta/)
- [Quantum Resistance (PQXDH)](https://signal.org/blog/pqxdh/)
- [Post-Quantum Ratchets (SPQR)](https://signal.org/blog/spqr/)
- [Disappearing Messages](https://signal.org/blog/disappearing-messages/)
- [Disappearing by Default](https://signal.org/blog/disappearing-by-default/)
- [Reactions](https://signal.org/blog/reactions/)
- [Private Groups](https://signal.org/blog/private-groups/)
- [Safety Number Updates](https://signal.org/blog/safety-number-updates/)
- [Introducing Secure Backups](https://signal.org/blog/introducing-secure-backups/)
- [ICE Forking for Multi-Device Calls](https://signal.org/blog/ice-forking/)

### GitHub Repositories
- [Signal-iOS](https://github.com/signalapp/Signal-iOS)
- [Signal-Server](https://github.com/signalapp/Signal-Server)
- [libsignal](https://github.com/signalapp/libsignal)
- [ContactDiscoveryService](https://github.com/signalapp/ContactDiscoveryService)
- [key-transparency-server](https://github.com/signalapp/key-transparency-server)
- [key-transparency-auditor](https://github.com/signalapp/key-transparency-auditor)

### Technical Analysis
- [DeepWiki: Signal-Server Architecture](https://deepwiki.com/signalapp/Signal-Server)
- [DeepWiki: Signal-iOS Architecture](https://deepwiki.com/signalapp/Signal-iOS)
- [SoftwareMill: What I Learned from Signal Server Source Code](https://softwaremill.com/what-ive-learned-from-signal-server-source-code/)
- [Signal Security Architecture Deep Dive](https://profincognito.me/blog/security/signal-security-architecture/)
- [PQShield: Diving into Signal's PQ Protocol](https://pqshield.com/diving-into-signals-new-pq-protocol/)
- [Signal Protocol - Wikipedia](https://en.wikipedia.org/wiki/Signal_Protocol)

### Academic Papers
- [Security Analysis of Signal's PQXDH (ePrint 2024/702)](https://eprint.iacr.org/2024/702)
- [Formal Verification of PQXDH (USENIX Security 2024)](https://www.usenix.org/conference/usenixsecurity24/presentation/bhargavan)
- [Improving Signal's Sealed Sender (NDSS 2021)](https://www.cs.umd.edu/~kaptchuk/publications/ndss21.pdf)
- [Analysis of Sender Keys Protocol](https://arxiv.org/pdf/2301.07045)
- [Multi-Device for Signal](https://eprint.iacr.org/2019/1363.pdf)
- [Signal Private Group System](https://eprint.iacr.org/2019/1416.pdf)

### Signal Support Pages
- [Key Transparency](https://support.signal.org/hc/en-us/articles/10223569377562-Key-Transparency-Auto-verify-encryption)
- [Secure Backups](https://support.signal.org/hc/en-us/articles/9708267671322-Signal-Secure-Backups)
- [Read Receipts](https://support.signal.org/hc/en-us/articles/360007059812-Read-Receipts)
- [Typing Indicators](https://support.signal.org/hc/en-us/articles/360020798451-Typing-Indicators)
- [Linked Devices](https://support.signal.org/hc/en-us/articles/360007320551-Linked-Devices)
