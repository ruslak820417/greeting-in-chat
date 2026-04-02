# Deep Research: Reliable Message Delivery in Production Messaging Apps

**Date:** 2026-03-24
**Scope:** WhatsApp, Signal, Telegram — protocols, algorithms, best practices
**Target:** QRChat (React Native, WebSocket, TweetNaCl, Double Ratchet, SQLite)

---

## Table of Contents

1. [Message Delivery Pipeline](#1-message-delivery-pipeline)
2. [Delivery Receipts / Read Receipts](#2-delivery-receipts--read-receipts)
3. [Offline Message Queue](#3-offline-message-queue)
4. [Message Retry and Error Handling](#4-message-retry-and-error-handling)
5. [Typing Indicators](#5-typing-indicators)
6. [Online/Offline Presence](#6-onlineoffline-presence)
7. [Message Sync and History](#7-message-sync-and-history)
8. [Group Messaging](#8-group-messaging)
9. [QRChat Gap Analysis](#9-qrchat-gap-analysis)
10. [Specific Recommendations for QRChat](#10-specific-recommendations-for-qrchat)

---

## 1. Message Delivery Pipeline

### 1.1 WhatsApp — Step by Step

WhatsApp processes 140 billion messages per day using custom Erlang/OTP servers running on the BEAM VM. Each server handles 2-3 million concurrent connections via lightweight Erlang processes (~300 bytes each).

**Full message flow:**

```
Sender Phone                    Server Cluster                   Recipient Phone
     |                               |                                |
     |  1. Encrypt (Double Ratchet)  |                                |
     |  2. Encode (FunXMPP binary)   |                                |
     |      ~180B XML -> ~20B binary |                                |
     |                               |                                |
     |  3. Send over TCP/TLS ------->|                                |
     |                               |  4. Decode FunXMPP             |
     |                               |  5. Query Mnesia: where is     |
     |                               |     recipient? (microseconds,  |
     |                               |     all in RAM)                |
     |                               |                                |
     |                               |  [IF ONLINE]                   |
     |                               |  6. Forward to recipient's     |
     |                               |     server process ----------->|
     |                               |                                |  7. Decode + decrypt
     |  8. Single checkmark <--------|                                |
     |     (server received)         |                                |
     |                               |  9. Recipient ACK <------------|
     |  10. Double checkmark <--------|     (FunXMPP ACK)             |
     |     (delivered to device)     |                                |
     |                               |                                |
     |                               |  [IF OFFLINE]                  |
     |                               |  6. Store in Mnesia offline    |
     |                               |     queue (replicated)         |
     |                               |  7. Send push notification     |
     |  8. Single checkmark <--------|     (APNs/FCM)                 |
     |     (server received)         |                                |
     |                               |                                |
     |                               |  [WHEN RECIPIENT RECONNECTS]   |
     |                               |  9. Deliver queued messages -->|
     |                               | 10. Delete from queue          |
     |  11. Double checkmark <--------|                               |
```

**Key design decisions:**
- FunXMPP binary protocol reduces XML overhead by 50-70%
- Mnesia (Erlang's built-in distributed DB) stores routing tables, offline queues, and user data — all in RAM, replicated across nodes
- Server NEVER persists decrypted content — only encrypted blobs transit the server
- Messages are deleted from the offline queue immediately upon successful delivery
- A single server handling 2-3M connections means every message path is: receive -> lookup -> forward -> deliver

### 1.2 Signal — Step by Step

Signal uses a store-and-forward model with sealed sender envelopes:

```
Sender                          Signal Server                    Recipient
  |                                  |                               |
  |  1. Encrypt with Double Ratchet |                               |
  |  2. Create sender certificate   |                               |
  |  3. Encrypt envelope with       |                               |
  |     recipient's identity key    |                               |
  |     (sealed sender)             |                               |
  |                                  |                               |
  |  4. Send envelope + delivery --->|                               |
  |     token (NO sender auth)      |                               |
  |                                  |  5. Validate delivery token   |
  |                                  |  6. Queue encrypted envelope  |
  |                                  |                               |
  |                                  |  [DELIVER when online] ------>|
  |                                  |  7. Delete from queue         |
  |                                  |                               |  8. Decrypt outer layer
  |                                  |                               |  9. Validate sender cert
  |                                  |                               | 10. Decrypt inner layer
  |                                  |                               |     (Double Ratchet)
```

**Sealed Sender key innovation:**
- The server cannot see WHO sent the message — only WHO it is addressed to
- Sender authenticates via a delivery token derived from the recipient's profile key
- Abuse prevention: blocking a user rotates the profile key, invalidating their delivery token
- Sender certificate inside the envelope lets the RECIPIENT verify the sender

**Multi-device delivery:**
- Messages are encrypted separately for EACH device on the recipient's account
- Each device has independent prekeys and ratchet state
- Maximum 5 linked devices
- Linked device message history: compressed encrypted archive with 256-bit AES key, transferred via provisioning message, limited to 45 days of media

### 1.3 Telegram — MTProto

Telegram uses a custom protocol (MTProto 2.0) with explicit acknowledgment:

- Every content-related message has a `msg_seqno` (32-bit sequence number)
- `msg_seqno = 2 * content_messages_sent_before + (is_content ? 1 : 0)`
- Acknowledgments via `msgs_ack` constructor containing message IDs
- Quick ACKs: lightweight receipt confirmation (received + decrypted + accepted for processing)
- Full ACK: RPC response serves as implicit acknowledgment
- If no response within 60-120 seconds, standalone ACK must be sent
- Standalone ACK if 16+ unacknowledged messages accumulate

---

## 2. Delivery Receipts / Read Receipts

### 2.1 The Checkmark System (WhatsApp Model)

| State | Visual | Meaning | Trigger |
|-------|--------|---------|---------|
| Sending | Clock icon | Message in local outbox | User taps send |
| Sent | Single gray check | Server received + persisted | Server ACK |
| Delivered | Double gray check | Reached recipient's device | Device ACK |
| Read | Double blue check | Recipient opened the chat | App event: chat opened |

**Critical rule:** "Never acknowledge a message to the sender until it is persisted to durable storage." This prevents data loss on server crash.

**State transitions are unidirectional:** sending -> sent -> delivered -> read. You can skip states (e.g., go directly from sent to read), but never go backward.

### 2.2 Protocol for ACKs

```
DELIVERY RECEIPT:
  Recipient device receives message
  -> Recipient sends: { type: "delivery-receipt", messageId, deliveredAt }
  -> Server forwards to sender (or queues if sender offline)
  -> Sender updates local DB: isDelivered = true

READ RECEIPT:
  Recipient opens the conversation containing unread messages
  -> Recipient sends: { type: "read-receipt", messageIds: [...], readAt }
  -> Server forwards to sender
  -> Sender updates local DB: isRead = true
  -> Sender UI updates checkmarks to blue
```

### 2.3 Lost ACK Problem

What if the delivery receipt is lost (network drop between recipient and server)?

**Solution: Idempotent receipts + retry**
- Recipient re-sends delivery receipts on next connection
- Server deduplicates based on messageId
- Receipts are queued for offline senders (same as regular messages)
- On reconnection, all pending receipts are flushed

### 2.4 Privacy Controls

- WhatsApp: users can disable read receipts (blue checks) but NOT delivery receipts (gray checks). Group read receipts cannot be disabled.
- Signal: read receipts are optional per-user setting
- Telegram: read receipts always on in private chats, no opt-out

### 2.5 Group Receipt Behavior

- WhatsApp: double blue checks appear ONLY when ALL group members have read the message
- Practical: long-press a message to see per-member delivery/read status
- Implementation: the server (or sender) tracks receipt count vs. member count

---

## 3. Offline Message Queue

### 3.1 Server-Side Queue Architecture

**WhatsApp approach (Mnesia):**
- Offline messages stored in Mnesia RAM database, replicated to backup server
- Messages are queued as encrypted blobs with timestamps
- On reconnection: batch delivery with staggered pacing to avoid client flood
- Messages deleted from queue upon delivery confirmation

**Signal approach:**
- Encrypted envelopes queued on server
- Purged after "a period of inactivity" (reportedly up to 30 days, though exact TTL is not publicly documented)
- Server cannot read envelope contents
- No message persistence after delivery — envelope deleted immediately

### 3.2 Queue Overflow Protection

| Parameter | Recommended Value | Rationale |
|-----------|-------------------|-----------|
| Max messages per user | 1,000 | Prevents DoS from mass-sending to offline user |
| Max queue size per user | 50 MB | Prevents storage exhaustion |
| Message TTL | 30-48 hours for chat, 30 days for encrypted envelopes | Balance between delivery guarantee and storage cost |
| Cleanup interval | Every 1 hour | Purge expired messages periodically |

### 3.3 Message Ordering

**The clock problem:** Client clocks are unreliable. Server A's clock may differ from Server B's.

**Solutions used in production:**

1. **Server-assigned timestamps** (WhatsApp, most systems): The server stamps every message with its own clock at reception time. This is the authoritative ordering.

2. **Lamport logical clocks** (used internally): Each process maintains a counter that increments on every event. Messages carry the counter. Receiver updates its counter to `max(local, received) + 1`. This ensures causal ordering without relying on wall clocks.

3. **Per-conversation sequence numbers** (recommended): Each conversation has a monotonically increasing sequence number. The server assigns the next number when a message arrives. Client orders by sequence number, not timestamp.

```
Server receives message for conversation C:
  seq = conversations[C].nextSeq++
  message.seq = seq
  persist(message)
  deliver(message)

Client displays messages:
  ORDER BY seq ASC  (not ORDER BY timestamp ASC)
```

### 3.4 Duplicate Detection After Reconnection

When a client reconnects and the server replays queued messages, duplicates can occur if the original delivery was partially successful. Solutions:

1. **Idempotency keys (messageId):** Every message has a unique ID (UUID). Client checks: "Have I already processed this messageId?" If yes, skip.

2. **Deduplication window:** Store processed messageIds for a retention period (e.g., 24 hours). After that, accept the risk of occasional duplicates.

3. **UUIDv7 optimization:** Use time-sorted UUIDs so old IDs can be efficiently pruned.

4. **Database-level:** `INSERT OR IGNORE` with messageId as PRIMARY KEY — the database itself rejects duplicates.

### 3.5 Batch Delivery on Reconnection

When a user comes online after being offline:

```
1. Server identifies N queued messages for this user
2. Sort by timestamp (oldest first)
3. Deliver in batches of 10-20 messages
4. Wait 50ms between batches (prevents client flood)
5. Client processes each batch, sends ACKs
6. Server removes delivered messages from queue
7. If connection drops mid-delivery, remaining messages stay queued
```

---

## 4. Message Retry and Error Handling

### 4.1 Client-Side Retry Strategy

**Signal's approach (from their Android codebase):**
- Failed messages retry for up to **24 hours** with exponential backoff
- Uses a persistent **JobManager** system — retry jobs survive app restarts
- Jobs are serialized to SQLite and deserialized on app launch
- Group-level locking prevents out-of-order delivery within a conversation

**Exponential backoff formula:**

```javascript
// Base: 500ms, cap: 30s, jitter: 50-100% of calculated delay
function getRetryDelay(attempt) {
  const base = 500;
  const max = 30000;
  const exponential = Math.min(base * Math.pow(2, attempt), max);
  const jitter = exponential * (0.5 + Math.random() * 0.5);
  return jitter;
}

// Attempt 0: 250-500ms
// Attempt 1: 500-1000ms
// Attempt 2: 1000-2000ms
// Attempt 3: 2000-4000ms
// ...
// Attempt 6+: 15000-30000ms (capped)
```

### 4.2 Message State Machine (Client UI)

```
                          +----> FAILED (show retry button)
                          |        |
  [User taps send] --> SENDING --> SENT --> DELIVERED --> READ
                          |                    |
                          |                    +----> READ (can skip DELIVERED)
                          |
                          +----> QUEUED (offline, will retry)
```

**UI states:**
| State | UI Indicator | User Action Available |
|-------|-------------|----------------------|
| SENDING | Spinner/clock | Cancel (if quick enough) |
| SENT | Single check (gray) | None |
| DELIVERED | Double check (gray) | None |
| READ | Double check (blue) | None |
| FAILED | Red exclamation | Tap to retry |
| QUEUED | Clock + "waiting" | Cancel send |

### 4.3 Client-Side Outbox Queue

For offline-first operation, the client needs a persistent outbox:

```
SQLite table: outbox
  id TEXT PRIMARY KEY,          -- message UUID
  conversationId TEXT,
  encryptedPayload BLOB,       -- pre-encrypted message
  status TEXT DEFAULT 'pending', -- pending | sending | sent | failed
  retryCount INTEGER DEFAULT 0,
  nextRetryAt INTEGER,          -- timestamp for next attempt
  createdAt INTEGER,
  maxRetryUntil INTEGER         -- createdAt + 24 hours
```

**Algorithm:**
1. User sends message -> save to `messages` table (with isSent=false) AND `outbox` table
2. Attempt to send via WebSocket
3. If WebSocket is down, message stays in outbox with status='pending'
4. Background timer checks outbox every 5 seconds
5. For each pending message where `nextRetryAt <= now`:
   - If `now > maxRetryUntil`: mark as FAILED, notify user
   - Else: attempt send, increment retryCount, set nextRetryAt using backoff
6. On successful send (server ACK): remove from outbox, update messages.isSent=true
7. On app restart: reload outbox, resume retries

### 4.4 Double Ratchet Error Recovery

When a message cannot be decrypted (ratchet out of sync):

**Common causes:**
- Reinstalled app (lost ratchet state)
- Database corruption
- Race condition with concurrent messages from multiple devices
- Skipped too many messages (exceeds MAX_SKIP limit)

**Recovery protocol:**
1. Recipient detects decryption failure (ProtocolInvalidMessageException)
2. Recipient sends a "session reset" message to sender
3. Sender initiates a new X3DH key exchange
4. Both parties establish a fresh Double Ratchet session
5. Previously undeliverable messages are lost (by design — forward secrecy)

**Signal's MAX_SKIP protection:**
- The Double Ratchet stores skipped message keys for out-of-order delivery
- A malicious sender could claim `messageNumber = 999999` to force storage of 999,999 keys
- MAX_SKIP (typically 1000) limits how many keys can be skipped in one ratchet step
- Messages beyond MAX_SKIP are dropped with an error

### 4.5 Idempotency for Server Operations

```
Server receives encrypted-message:
  1. Check: have we seen this messageId before?
     - Maintain a Set/Map of recent messageIds (last 24h)
     - If duplicate: respond with "message-delivered" (idempotent success)
     - If new: process normally
  2. Persist message to queue/deliver
  3. Respond with ACK including messageId
```

---

## 5. Typing Indicators

### 5.1 Protocol Design

Typing indicators are **ephemeral** — they are NEVER persisted or queued. If the recipient is offline, typing events are silently dropped.

```
SENDER (client-side):
  onKeyPress:
    if not currently_sending_typing:
      send({ type: 'typing', to: recipientId, isTyping: true })
      set currently_sending_typing = true
      reset inactivity_timer to 3 seconds

  inactivity_timer expires:
    send({ type: 'typing', to: recipientId, isTyping: false })
    set currently_sending_typing = false

  onMessageSend:
    send({ type: 'typing', to: recipientId, isTyping: false })
    set currently_sending_typing = false

RECIPIENT (client-side):
  on typing event received:
    show typing indicator
    reset display_timer to 5 seconds  // auto-hide if no new event

  display_timer expires:
    hide typing indicator  // safety net if stop event was lost
```

### 5.2 Throttle + Debounce Strategy

The optimal approach combines BOTH throttle and debounce:

```javascript
// Throttle: send "typing" at most once per 2 seconds (even if user is continuously typing)
// Debounce: send "stopped" after 3 seconds of inactivity

let typingThrottle = null;
let stoppedDebounce = null;
let isTypingSent = false;

function onTextChange(text) {
  // Clear the "stopped" debounce timer
  clearTimeout(stoppedDebounce);

  // Throttle: send "typing: true" at most once per 2s
  if (!isTypingSent) {
    sendTyping(true);
    isTypingSent = true;
    typingThrottle = setTimeout(() => {
      isTypingSent = false;
    }, 2000);
  }

  // Debounce: if no typing for 3s, send "typing: false"
  stoppedDebounce = setTimeout(() => {
    sendTyping(false);
    isTypingSent = false;
    clearTimeout(typingThrottle);
  }, 3000);
}
```

### 5.3 Timeout Values (Industry Standard)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Throttle interval | 2000ms | Prevents flooding; one event per 2s max |
| Debounce (stop) | 3000ms | User paused typing |
| Receiver auto-hide | 5000ms | Safety net if stop event lost |
| Typing default timeout | 5000ms (PubNub standard) with 1000ms buffer | Widely adopted standard |

### 5.4 Privacy

- Signal: typing indicators are optional (Settings -> Privacy)
- WhatsApp: typing indicators always on, no opt-out
- Recommendation: make it a per-contact privacy setting (as QRChat already has in the Contact type)

---

## 6. Online/Offline Presence

### 6.1 Heartbeat-Based Presence

```
Client                          Server
  |                                |
  |  [Every 25-30 seconds]        |
  |  ping ----------------------->|
  |                                |  Reset presence TTL to 60s
  |  pong <-----------------------|
  |                                |
  |  [If no pong within 10s]      |
  |  Connection is dead ->        |
  |  Close + reconnect            |
  |                                |
  |  [Server side: if no ping     |
  |   within 35s]                 |
  |                                |  Mark user offline
  |                                |  Clean up connection
```

### 6.2 Presence Architecture at Scale

**Small scale (< 10K users, like QRChat):**
- Simple `clients` Map on server: `userId -> WebSocket`
- `clients.has(userId)` = online
- No separate presence service needed

**Medium scale (10K-1M users):**
- Redis with TTL-based presence: `SET presence:{userId} online EX 60`
- Heartbeat refreshes TTL
- Query: `EXISTS presence:{userId}`

**Large scale (1M+ users, WhatsApp/LinkedIn):**
- Dedicated presence service with actor model
- Each user has a presence actor that tracks heartbeats
- Lazy queries: presence is only fetched when viewing a conversation
- Fan-out avoidance: don't broadcast presence changes to all contacts

### 6.3 Battery Optimization

| Approach | Battery Impact | Accuracy |
|----------|---------------|----------|
| 10s heartbeat | High | Near real-time |
| 30s heartbeat | Medium | ~30s delay |
| 60s heartbeat | Low | ~60s delay (acceptable for most apps) |
| Lazy query only | Minimal | On-demand only |

**Best practice:** 25-30 second heartbeat interval. This clears common proxy timeouts (many proxies kill idle WebSocket connections after 30s) while being battery-friendly.

### 6.4 Privacy Considerations

- **Signal deliberately does NOT show online/last-seen status** — this is a privacy-first design decision
- **WhatsApp:** "Last seen" with privacy settings (Everyone / My Contacts / Nobody)
- **Telegram:** "Last seen" with privacy settings, plus approximate values ("recently", "within a week")

**Recommendation for QRChat:** Implement per-contact privacy controls (already partially in the Contact type with `privacyLastSeenVisible`). Default to "contacts only."

---

## 7. Message Sync and History

### 7.1 Signal's Linked Device Sync

When linking a new device (desktop/iPad):

```
1. New device generates temporary provisioning address + Curve25519 keypair
2. Displays QR code containing: provisioning address + public key
3. Primary device scans QR code
4. Primary device sends encrypted provisioning message containing:
   - Shared keys
   - Account information
   - One-time-use linking token
5. Primary device creates compressed archive of:
   - All text messages, stickers, call logs, reactions, receipts
   - Pointers to media attachments (not the actual files)
   - Limited to 45 days of media
6. Archive encrypted with 256-bit AES key (one-time-use)
7. Transferred via Signal servers (E2E encrypted)
8. New device decrypts and imports to local database
9. New device independently fetches media from server using pointers
```

**Post-sync operation:**
- Each device maintains independent Double Ratchet sessions
- Senders encrypt and send a SEPARATE copy to each device
- Each device has its own prekeys uploaded to the server
- Maximum 5 linked devices per account

### 7.2 WhatsApp Encrypted Backups

- Backup encrypted with a random 256-bit key
- User secures the key with either:
  - A user-chosen password (key stored in HSM-backed Backup Key Vault)
  - A 64-digit encryption key (user manages manually)
- Stored on iCloud or Google Drive
- Neither WhatsApp nor the cloud provider can decrypt the backup
- Password-based key retrieval has rate limiting + max attempt lockout

### 7.3 Cross-Device Message Deletion

When user deletes a message:
1. Delete locally
2. Send "delete-for-me" or "delete-for-everyone" signal to other devices/contacts
3. Other devices process the delete
4. Timeout: WhatsApp allows "delete for everyone" within ~2 days

---

## 8. Group Messaging

### 8.1 Signal's Sender Keys Protocol

For groups, Signal uses **Sender Keys** instead of individual Double Ratchet sessions:

```
GROUP SETUP:
  1. Creator generates group parameters
  2. For each member, establish pairwise Double Ratchet session (if not exists)
  3. Each member generates their own Sender Key:
     - Random symmetric key
     - Chain key for forward ratcheting

SENDING A GROUP MESSAGE:
  1. Sender encrypts message with their Sender Key (single encryption)
  2. Sends encrypted blob to server with group ID
  3. Server fans out to each member
  4. Each member decrypts with sender's Sender Key

SENDER KEY DISTRIBUTION:
  - When joining a group, distribute your Sender Key to all members
  - Distribution happens via pairwise Double Ratchet sessions (E2E)
  - When a member is REMOVED: all remaining members rotate their Sender Keys
```

**Advantages over pairwise encryption:**
- Sender encrypts ONCE (not N times for N members)
- Much more efficient for large groups
- Still E2E encrypted

**Security trade-off:**
- Learning a Sender Key enables computing all FUTURE message keys from that sender
- Mitigation: rotate Sender Keys when members leave

### 8.2 Server-Side Fan-Out

**Small groups (< 100 members, WhatsApp model):**
```
1. Sender sends message to server (single copy)
2. Server looks up group member list
3. Server spawns parallel delivery workers (10-20 recipients per worker)
4. Each worker delivers to online members OR queues for offline members
5. All deliveries happen simultaneously across the cluster
```

**Large groups/channels (Telegram model):**
```
1. Message persisted once in database
2. Fan-out workers iterate through member list
3. For online members: push via WebSocket
4. For offline members: add message reference to their queue
5. Lazy delivery: members fetch when they open the group
```

### 8.3 Group Size Limits

| App | Max Group Size | Rationale |
|-----|---------------|-----------|
| WhatsApp | 1,024 | Performance + spam prevention |
| Telegram | 200,000 | Channel-like groups with admin controls |
| Signal | 1,000 | Privacy + E2E encryption overhead |

### 8.4 Group Admin Controls

Essential admin capabilities:
- Add/remove members (with re-encryption on removal)
- Promote/demote admins
- Change group name/photo
- Control who can post (admin-only mode)
- Group invite links with approval
- View/manage pending join requests

---

## 9. QRChat Gap Analysis

After examining the QRChat codebase (`/Users/ruslanconstantinovici/QRChat`), here is a detailed analysis of what exists vs. what production apps do.

### 9.1 What QRChat Does RIGHT

| Feature | Status | Notes |
|---------|--------|-------|
| E2E encryption (Double Ratchet) | GOOD | Proper Double Ratchet with TweetNaCl |
| Delivery receipts | GOOD | `delivery-receipt` type implemented on server and client |
| Read receipts | GOOD | `read-receipt` with batch messageIds (up to 100) |
| Typing indicators | GOOD | `typing` event with `isTyping` boolean, not queued for offline |
| Offline message queue | GOOD | Server queues with 48h TTL, JSON persistence to disk |
| Queue DoS protection | GOOD | 1000 msgs / 50MB per user limits |
| Heartbeat | GOOD | 30s ping/pong with 10s timeout |
| Reconnection backoff | GOOD | Capped at 30 seconds |
| Client send queue | GOOD | 500 messages, 30s max age |
| Push notifications | GOOD | APNs + FCM integration for offline users |
| Auth challenge | GOOD | Ed25519 signature verification |
| Rate limiting | GOOD | Token bucket: 200 burst, 20/s refill |
| Per-contact privacy | GOOD | `privacyReadReceipts`, `privacyTypingIndicators`, `privacyLastSeenVisible` in Contact type |
| Message deduplication | PARTIAL | `processingIds` Set on client, `INSERT OR IGNORE` on DB |
| Staggered batch delivery | GOOD | 10 messages per batch, 50ms between batches |

### 9.2 What QRChat is MISSING or DOING WRONG

#### CRITICAL ISSUES

**1. No server-side message persistence guarantee (data loss risk)**
- QRChat server writes pending messages to a JSON file (`qrchat_pending_messages.json`) every 60 seconds
- If the server crashes between writes, up to 60 seconds of queued messages are LOST
- WhatsApp rule: "Never acknowledge a message until it is persisted to durable storage"
- QRChat sends `message-queued` ACK BEFORE the next periodic flush

**2. No per-conversation sequence numbers**
- Messages are ordered by `timestamp` only (`ORDER BY timestamp ASC`)
- Client timestamps are unreliable (wrong timezone, clock skew, manual adjustment)
- Production apps use server-assigned sequence numbers per conversation
- Risk: messages appear out of order, especially after offline delivery

**3. No persistent client-side outbox**
- `SignalingClient.sendQueue` is in-memory only (max 500 messages, 30s max age)
- If the app is killed while messages are queued, they are LOST
- Signal retries for 24 hours using persistent SQLite-backed JobManager
- QRChat should persist unsent messages to SQLite and retry with exponential backoff

**4. No idempotency on server-side message processing**
- Server does not track processed messageIds
- If a client retries sending the same message (e.g., after timeout without ACK), the server queues/delivers it AGAIN
- This results in duplicate messages on the recipient's device
- Solution: server-side deduplication with a messageId cache (TTL: 24 hours)

**5. No server-assigned timestamp/sequence for message ordering**
- The `encrypted-message` handler forwards `message.payload` as-is without adding any server metadata
- No server timestamp is stamped on the message
- The client generates its own timestamp, which is unreliable for ordering

#### HIGH PRIORITY ISSUES

**6. No message status state machine on client**
- Messages have `isSent`, `isDelivered`, `isRead` booleans but no explicit state machine
- No SENDING state (spinner while WebSocket send is in progress)
- No FAILED state with retry button
- No QUEUED state (waiting for reconnection)
- The `flushUndeliveredMessages` method exists but has no UI feedback

**7. Delivery receipts not sent on reconnection**
- When the client receives queued messages from the server after reconnection, it does not batch-send delivery receipts for all received messages
- This means the sender never gets the double checkmark for offline-delivered messages unless the recipient manually triggers it

**8. No receipt for queued messages when they are actually delivered**
- When server delivers queued messages to a reconnecting user, it sends `pendingDelivered: N` count
- But it does NOT send `message-delivered` ACKs back to the original senders
- The original senders' messages stay at "sent" (single check) forever for offline-delivered messages

**9. Typing indicator has no throttle/debounce on client**
- Server relays typing events directly without any server-side throttle
- If the client sends typing on every keystroke, this floods the WebSocket
- Need: throttle to max 1 event per 2s, debounce stop after 3s inactivity

**10. Presence is query-only, no push updates**
- `ping-user` returns online/offline status but only on explicit request
- No mechanism to push "contact came online" events to interested users
- When you're in a chat, you want live presence updates without polling

#### MEDIUM PRIORITY ISSUES

**11. No message gap detection on reconnection**
- When client reconnects, it receives queued messages but has no way to detect if messages were lost (server crash, queue overflow)
- No sequence number to detect gaps
- Should track "last received sequence" and request replay

**12. Send queue max age too short (30s)**
- `QUEUE_MAX_AGE = 30000` means messages older than 30s in the outbox are DROPPED
- If the user is in a tunnel/elevator for 2 minutes, all their queued messages are lost
- Signal keeps retrying for 24 hours
- Should be at minimum 24 hours with persistent storage

**13. No encrypted backup/restore**
- No mechanism to backup message history to iCloud/Google Drive
- If user reinstalls app or switches phone, all messages are lost
- WhatsApp and Signal both offer encrypted cloud backups

**14. Group message encryption is unclear**
- `Group` type exists with `memberIds` but no Sender Key protocol visible
- Likely using pairwise encryption (N copies for N members) which doesn't scale
- Should implement Sender Keys for groups > 3 members

**15. No session reset / ratchet recovery mechanism**
- No visible handling of Double Ratchet decryption failures
- No "reset secure session" option for users
- If ratchet gets out of sync, messages become permanently undecryptable

**16. File chunk retry is not persistent**
- `sendChunkedRelay` has retry logic (3 attempts, 2s delay) but only within the current session
- If app is killed during file transfer, the transfer is lost
- Should persist chunk progress and resume on app restart

---

## 10. Specific Recommendations for QRChat

### Priority 1: Prevent Message Loss (implement immediately)

#### R1. Persistent Server-Side Write-Ahead
```javascript
// BEFORE sending ACK, flush to disk:
case 'encrypted-message': {
  const entry = { timestamp: Date.now(), data: { ... } };
  const queued = enqueuePending(message.to, entry);

  // NEW: Force flush before ACK
  if (queued) {
    savePendingToDisk();  // Synchronous write
  }

  ws.send(JSON.stringify({
    type: 'message-queued',
    messageId: message.messageId,
    to: message.to,
  }));
}
```

Better yet, use SQLite on the server instead of a JSON file for atomic writes.

#### R2. Server-Assigned Sequence Numbers
```javascript
// Server maintains per-conversation sequence counter
const conversationSeqs = new Map(); // conversationId -> nextSeq

function getNextSeq(conversationId) {
  const seq = (conversationSeqs.get(conversationId) || 0) + 1;
  conversationSeqs.set(conversationId, seq);
  return seq;
}

// When relaying a message:
target.send(JSON.stringify({
  type: 'encrypted-message',
  from: userId,
  payload: message.payload,
  messageId: message.messageId,
  seq: getNextSeq(conversationKey),      // NEW
  serverTimestamp: Date.now(),            // NEW
}));
```

#### R3. Persistent Client-Side Outbox
```sql
-- New table in SQLite
CREATE TABLE IF NOT EXISTS outbox (
  messageId TEXT PRIMARY KEY,
  conversationId TEXT NOT NULL,
  encryptedPayload TEXT NOT NULL,
  status TEXT DEFAULT 'pending',  -- pending, sending, sent, failed
  retryCount INTEGER DEFAULT 0,
  nextRetryAt INTEGER,
  createdAt INTEGER NOT NULL,
  maxRetryUntil INTEGER NOT NULL  -- createdAt + 86400000 (24h)
);
```

```typescript
// OutboxService.ts
class OutboxService {
  async enqueue(messageId: string, conversationId: string, payload: string) {
    const now = Date.now();
    await Database.execute(
      'INSERT INTO outbox VALUES (?, ?, ?, "pending", 0, ?, ?, ?)',
      [messageId, conversationId, payload, now, now, now + 86400000]
    );
    this.processQueue();
  }

  async processQueue() {
    const pending = await Database.execute(
      'SELECT * FROM outbox WHERE status = "pending" AND nextRetryAt <= ? AND maxRetryUntil > ?',
      [Date.now(), Date.now()]
    );
    for (const msg of pending) {
      const sent = SignalingClient.send({
        type: 'encrypted-message',
        to: msg.conversationId,
        payload: msg.encryptedPayload,
        messageId: msg.messageId,
      });
      if (sent) {
        await Database.execute('DELETE FROM outbox WHERE messageId = ?', [msg.messageId]);
      } else {
        const delay = getRetryDelay(msg.retryCount);
        await Database.execute(
          'UPDATE outbox SET retryCount = retryCount + 1, nextRetryAt = ? WHERE messageId = ?',
          [Date.now() + delay, msg.messageId]
        );
      }
    }
  }
}
```

#### R4. Server-Side Message Deduplication
```javascript
// Simple dedup cache with TTL
const processedMessages = new Map(); // messageId -> timestamp
const DEDUP_TTL = 24 * 60 * 60 * 1000; // 24 hours

// Cleanup every hour
setInterval(() => {
  const cutoff = Date.now() - DEDUP_TTL;
  for (const [id, ts] of processedMessages) {
    if (ts < cutoff) processedMessages.delete(id);
  }
}, 60 * 60 * 1000);

// In encrypted-message handler:
case 'encrypted-message': {
  if (message.messageId && processedMessages.has(message.messageId)) {
    // Idempotent: ACK success without re-delivering
    ws.send(JSON.stringify({
      type: 'message-delivered',
      messageId: message.messageId,
      to: message.to,
      deduplicated: true,
    }));
    break;
  }
  processedMessages.set(message.messageId, Date.now());
  // ... normal processing
}
```

### Priority 2: Fix Receipt Flow

#### R5. Delivery Receipt on Offline Message Delivery
```javascript
// When delivering queued messages to a reconnecting user:
const pending = pendingMessages.get(userId) || [];
if (pending.length > 0) {
  pendingMessages.delete(userId);

  // Track which senders need delivery notifications
  const senderNotifications = new Map(); // senderId -> [messageIds]

  for (const p of pending) {
    if (p.data.type === 'encrypted-message' && p.data.from) {
      const list = senderNotifications.get(p.data.from) || [];
      list.push(p.data.messageId);
      senderNotifications.set(p.data.from, list);
    }
  }

  // Notify each sender that their messages were delivered
  for (const [senderId, messageIds] of senderNotifications) {
    const senderWs = clients.get(senderId);
    if (senderWs && senderWs.readyState === WebSocket.OPEN) {
      for (const msgId of messageIds) {
        senderWs.send(JSON.stringify({
          type: 'message-delivered',
          messageId: msgId,
          to: userId,
          deliveredAt: Date.now(),
        }));
      }
    }
    // If sender is also offline, queue the delivery receipts for them
    // (they'll get notified when they reconnect)
  }

  // ... then deliver messages to recipient as before
}
```

#### R6. Client Sends Batch Delivery Receipts on Reconnection
```typescript
// In MessagingService, after receiving queued messages:
SignalingClient.on('registered', async (message) => {
  if (message.pendingDelivered > 0) {
    // Wait for messages to arrive, then ACK them all
    setTimeout(async () => {
      // Get all recently received messages that lack delivery receipt
      const unacked = await Database.getUnackedReceivedMessages();
      for (const msg of unacked) {
        SignalingClient.sendDeliveryReceipt(msg.senderId, msg.id);
      }
    }, 2000); // Wait 2s for all batches to arrive
  }
});
```

### Priority 3: Improve Typing & Presence

#### R7. Typing Indicator Throttle/Debounce
```typescript
// In ChatScreen.tsx
let typingThrottleTimer: NodeJS.Timeout | null = null;
let stoppedDebounceTimer: NodeJS.Timeout | null = null;
let isTypingSent = false;

function onTextInputChange(text: string) {
  if (stoppedDebounceTimer) clearTimeout(stoppedDebounceTimer);

  if (!isTypingSent) {
    SignalingClient.sendTyping(contactId, true);
    isTypingSent = true;
    typingThrottleTimer = setTimeout(() => {
      isTypingSent = false;
    }, 2000);
  }

  stoppedDebounceTimer = setTimeout(() => {
    SignalingClient.sendTyping(contactId, false);
    isTypingSent = false;
    if (typingThrottleTimer) clearTimeout(typingThrottleTimer);
  }, 3000);
}

// Auto-hide on receiver after 5s timeout (safety net)
function onTypingReceived(isTyping: boolean) {
  if (isTyping) {
    showTypingIndicator();
    resetAutoHideTimer(5000);
  } else {
    hideTypingIndicator();
  }
}
```

#### R8. Live Presence Push (While in Chat)
```javascript
// Server: when user connects, notify all their chat partners
case 'register': {
  // ... existing code ...

  // NEW: Notify recent chat partners that this user is now online
  const contacts = getRecentChatPartners(userId); // from pending messages or a contacts list
  for (const contactId of contacts) {
    const contactWs = clients.get(contactId);
    if (contactWs && contactWs.readyState === WebSocket.OPEN) {
      contactWs.send(JSON.stringify({
        type: 'user-status',
        userId: userId,
        isOnline: true,
      }));
    }
  }
}

// On disconnect:
ws.on('close', () => {
  // Notify contacts that user went offline
  // (Same pattern as above with isOnline: false)
});
```

### Priority 4: Future Enhancements

#### R9. Session Reset for Double Ratchet Recovery
```typescript
// Add to MessagingService:
async resetSession(contactId: string) {
  // Clear ratchet state
  await RatchetStore.deleteSession(contactId);

  // Re-initiate key exchange
  const contact = await Database.getContact(contactId);
  const newRatchet = new DoubleRatchet();
  await newRatchet.initSender(myKeyPair, contact.publicKey);
  await RatchetStore.saveSession(contactId, newRatchet.serialize());

  // Send session-reset signal so other side also resets
  SignalingClient.send({
    type: 'encrypted-message',
    to: contactId,
    payload: { _type: 'session-reset', newPublicKey: myKeyPair.publicKey },
    messageId: generateId(),
  });
}
```

#### R10. Encrypted Cloud Backup
```typescript
// Key derivation from user password:
const backupKey = await deriveKey(userPassword, salt, 100000); // PBKDF2, 100K iterations

// Encrypt database:
const dbData = await readSQLiteFile();
const encrypted = nacl.secretbox(dbData, nonce, backupKey);

// Upload to iCloud/Google Drive via react-native-cloud-storage
await CloudStorage.upload('qrchat-backup.enc', encrypted);
```

---

## Summary: Priority Implementation Order

| # | Fix | Effort | Impact | Risk if Skipped |
|---|-----|--------|--------|-----------------|
| 1 | Server-side flush before ACK | Low | Critical | Message loss on server crash |
| 2 | Server-side messageId dedup | Low | High | Duplicate messages after retry |
| 3 | Persistent client outbox (SQLite) | Medium | Critical | Message loss on app kill |
| 4 | Server-assigned sequence numbers | Medium | High | Wrong message order |
| 5 | Delivery receipt for offline messages | Low | High | Stuck single checkmarks |
| 6 | Message state machine + FAILED UI | Medium | High | User thinks message sent but it wasn't |
| 7 | Typing throttle/debounce | Low | Medium | WebSocket flooding |
| 8 | Presence push on connect/disconnect | Low | Medium | Stale online/offline status |
| 9 | Session reset for ratchet recovery | Medium | Medium | Permanently broken conversations |
| 10 | Encrypted cloud backup | High | Medium | Data loss on phone loss/reinstall |

---

## Sources

- [How WhatsApp Works - Architecture Deep Dive (GetStream)](https://getstream.io/blog/whatsapp-works/)
- [How WhatsApp Handles 40 Billion Messages Per Day (ByteByteGo)](https://blog.bytebytego.com/p/how-whatsapp-handles-40-billion-messages)
- [Design WhatsApp System Design Interview (AlgoMaster)](https://algomaster.io/learn/system-design-interviews/design-whatsapp)
- [Signal Sealed Sender](https://signal.org/blog/sealed-sender/)
- [Signal Double Ratchet Specification](https://signal.org/docs/specifications/doubleratchet/)
- [Signal Linked Device Sync](https://signal.org/blog/a-synchronized-start-for-linked-devices/)
- [Signal Forward Secrecy for Async Messages](https://signal.org/blog/asynchronous-security/)
- [Signal Android PR #7914 - 24h Retry](https://github.com/signalapp/Signal-Android/pull/7914)
- [Telegram MTProto Detailed Description](https://core.telegram.org/mtproto/description)
- [Telegram Service Messages About Messages](https://core.telegram.org/mtproto/service_messages_about_messages)
- [WebSocket Reconnection Guide (WebSocket.org)](https://websocket.org/guides/reconnection/)
- [WhatsApp E2E Encrypted Backups (Meta Engineering)](https://engineering.fb.com/2021/09/10/security/whatsapp-e2ee-backups/)
- [EFF: How Signal, WhatsApp, Apple Handle Encrypted Backups](https://www.eff.org/deeplinks/2025/05/back-it-back-it-let-us-begin-explain-encrypted-chat-backups)
- [Exactly-Once Delivery (Google Cloud Pub/Sub)](https://cloud.google.com/pubsub/docs/exactly-once-delivery)
- [Idempotency Keys (Gunnar Morling)](https://www.morling.dev/blog/on-idempotency-keys/)
- [Deduplication in Distributed Systems (Architecture Weekly)](https://www.architecture-weekly.com/p/deduplication-in-distributed-systems)
- [Adding Typing Indicators (DEV Community)](https://dev.to/hexshift/adding-typing-indicators-to-real-time-chat-applications-76p)
- [LinkedIn Real-Time Presence Platform](https://www.linkedin.com/blog/engineering/product-design/now-you-see-me-now-you-dont-linkedins-real-time-presence-platf)
- [AWS Timeouts, Retries, Backoff with Jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)
- [Signal Sender Keys / Group Protocol (Wikipedia)](https://en.wikipedia.org/wiki/Signal_Protocol)
- [Signal Protocol Group Chat Implementation (Medium)](https://medium.com/@ahmedcs1995/signal-protocol-end-to-end-group-chat-implementation-in-android-e4e77c79e698)
- [Push Notification Delivery: APNs and FCM Deep Dive](https://blog.clix.so/how-push-notification-delivery-works-internally/)
- [Lamport Clocks (Martin Fowler)](https://martinfowler.com/articles/patterns-of-distributed-systems/lamport-clock.html)
