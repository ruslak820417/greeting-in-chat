# QRChat Network Audit Report
**Date:** 2026-03-23
**Auditor:** Network Auditor Agent
**Scope:** Server (Railway) + iOS Client + Android Client networking interaction

---

## Executive Summary

The QRChat networking stack is well-architected with a shared React Native codebase serving both iOS and Android. The server-side WebSocket signaling, pending message queue, and push notification routing are robust. However, **one critical bug** and several medium-priority issues were identified.

| Severity | Count |
|----------|-------|
| CRITICAL | 1 |
| HIGH     | 1 |
| MEDIUM   | 3 |
| LOW      | 3 |
| INFO     | 2 |

---

## 1. Server Health

**Status: PASS**

```
GET /health -> {"status":"ok","clients":1}
Response time: 389ms
GET /        -> {"service":"QRChat Signaling Server","status":"running"}
```

- Server is running on Railway, responding normally.
- Health endpoint exposes client count (minor info leak — see LOW-1).

---

## 2. WebSocket Connection

**Status: PASS**

- Server uses `ws` (WebSocket) library over HTTP.
- Auth flow: server sends `auth-challenge` (Ed25519 nonce) -> client signs -> `auth-response` -> `auth-success` -> `register`.
- Client has 3s auth fallback timer (if server doesn't send challenge, falls back to direct register).
- `GRACE_PERIOD` env var controls whether unauthenticated clients can register (backward compat).
- Relay URL pinning: production only allows `wss://` to pinned domains — good security.

---

## 3. Server Ping Interval (10s)

**Status: PASS**

- **Server-side:** `setInterval` at 10s uses native WebSocket `ws.ping()` / `ws.pong()`.
  - Dead connections (`ws.isAlive === false`) are terminated immediately.
  - This is appropriate for Railway's infrastructure which may timeout idle connections.

**File:** `server/index.js:900-906`

---

## 4. Client Heartbeat (30s)

**Status: PASS (with note)**

- **Client-side:** Sends `{ type: 'ping' }` JSON message every 30s.
- Server responds with `{ type: 'pong' }`.
- Client expects pong within 10s; on timeout, closes WS and triggers reconnect.
- **Timing analysis:**
  - Server native ping: every 10s (detects dead client in 10-20s)
  - Client app-level ping: every 30s (detects dead server in 30-40s)
  - These are well-synchronized. Server detects dead clients faster; client detects dead server within ~40s.

**File:** `src/network/SignalingClient.ts:43-44, 457-475`

**Note:** The two ping mechanisms operate at different layers — server uses WebSocket protocol-level ping, client uses application-level JSON ping. This is correct and complementary.

---

## 5. Reconnection Logic

**Status: PASS**

- **Backoff:** Exponential `Math.min(1000 * 2^attempts, 30000)` — caps at 30s.
- **Max attempts:** `Infinity` (will always retry).
- **On reconnect:**
  1. Re-authenticates (auth-challenge/response)
  2. Re-registers (sends userId)
  3. Receives pending messages from server
  4. Requests TURN credentials
  5. Flushes local send queue (messages queued during disconnect)
  6. Starts heartbeat
- **Send queue:** Max 500 messages, 30s max age. Oldest dropped when full.
- **forceReconnect():** Called on app foreground — resets attempts, reconnects immediately.
- **hardReconnect():** Force-closes and reconnects — used to trigger pending message delivery.

**File:** `src/network/SignalingClient.ts:477-485`

---

## 6. Message Delivery (iOS <-> Android)

**Status: PASS**

- **Dual-path delivery:** Messages sent on BOTH P2P (WebRTC DataChannel) and Relay (signaling server) simultaneously. Receiver deduplicates by `messageId`.
- **Online recipient:** Server forwards directly, sends `message-delivered` confirmation.
- **Offline recipient:** Server queues in `pendingMessages` (JSON file on disk), sends push notification.
- **Deduplication:** `processingIds` Set in MessagingService prevents double-processing.
- iOS and Android share identical `src/services/MessagingService.ts` — cross-platform delivery confirmed.

**File:** `src/services/MessagingService.ts:412-414` (dual-send), `server/index.js:654-706` (relay)

---

## 7. File Transfer / Chunking

**Status: PASS**

### P2P (WebRTC DataChannel):
- Chunk size: 16KB (safe for WebRTC DataChannel MTU)
- Reassembly via `chunkBuffers` Map with TTL 5 minutes
- Stale buffer cleanup every 60s

### Relay (Signaling Server):
- Chunk size: up to server max payload (1.5MB per WS message)
- `fileChunkBuffers` in MessagingService with 300s timeout
- Download cancellation supported via EventBus

### Cross-platform:
- Both iOS and Android use identical chunking code
- Server is transparent relay — doesn't parse chunk content

**File:** `src/network/WebRTCManager.ts:29, 178-215` (P2P), `src/services/MessagingService.ts:44-46` (relay)

---

## 8. Call Signaling

**Status: PASS**

- **Flow:** `offer` (with `isCall: true`, `isVideo`, `callTimestamp`) -> `answer` -> `ice-candidate` exchange.
- **Perfect Negotiation (Glare handling):** Implemented correctly.
  - Polite/impolite role based on userId comparison (`localUserId < remoteId`)
  - Polite peer rolls back on collision, impolite ignores
  - Fallback to close+recreate if rollback fails (older react-native-webrtc)
- **ICE candidate queuing:** Candidates queued for pending calls (before user answers), drained after `answerCall()`.
- **Outgoing call timeout:** 45s auto-hangup if no answer.
- **Missed call detection:** 600ms grace period after receiving offer — if `call-ended` arrives within, marked as missed.
- **Stale offer filter:** Offers older than 30s auto-rejected as missed.
- **CallKit (iOS):** Properly integrated with stale call cleanup (60s).

**File:** `src/network/WebRTCManager.ts:327-438` (calls), `src/services/MessagingService.ts:148-198` (missed call logic)

---

## 9. Push Notifications

### APNs (iOS): PASS
- Token-based authentication (.p8 key)
- Silent push with `content-available` + `mutable-content` (triggers NSE)
- `pushType: 'alert'` with empty alert body (avoids Apple silent push throttling)
- Priority 10 (high)
- Payload: `{ e: 1, s: senderUserId }` — ZERO message content
- Throttle: max 1 push per 30s per mailbox
- Invalid token cleanup on `BadDeviceToken` / `Unregistered`

### FCM (Android): PASS (server-side)
- Firebase Admin SDK with service account or env vars
- High-priority data message
- TTL: 60s for calls
- Call push: `{ type: 'incoming-call', from, callerName, isVideo, offer }`
- Message push: `{ type: 'new-message', from }`
- Invalid token cleanup on `registration-token-not-registered`

### CRITICAL BUG: Android PushTokenService sends `platform: 'ios'`

See CRITICAL-1 below.

**File:** `server/push.js:1-322`, `src/services/PushTokenService.ts:57-65`

---

## 10. Pending Messages

**Status: PASS**

- Storage: JSON file on Railway volume (`RAILWAY_VOLUME_MOUNT_PATH`)
- Expiry: 48 hours
- Max per user: 1000 messages OR 50MB
- Delivery: Staggered batch (10 messages per batch, 50ms between batches) — prevents client flood
- Cleanup: Hourly interval removes expired messages
- Persistence: Saved every 60s (dirty flag), also on SIGTERM/SIGINT
- Loaded on server startup

**File:** `server/index.js:44-91, 153-177, 367-388, 518-536`

---

## 11. Server push.js — sendPush() Routing

**Status: PASS**

```
sendPush(userId, senderUserId, callData) routes:
  - Android + call data -> sendAndroidPush() (FCM high-priority)
  - Android + no call data -> sendAndroidPush() (FCM lightweight)
  - iOS (any) -> sendSilentPush() (APNs)
```

Two-map design (userId -> mailboxId, mailboxId -> token) prevents linking identity to push token. Correct architecture.

**File:** `server/push.js:284-310`

---

## 12. Rate Limiting

**Status: PASS**

### WebSocket messages:
- Token bucket: 200 burst, 20 tokens/sec refill
- Max payload: 1.5MB per message
- `payload-too-large` and `rate-limited` error types sent to client
- Client handles both (`SignalingClient.ts:429-434`)

### Admin endpoints:
- 5 attempts per 60s per IP
- Stale entry cleanup every 5 minutes

### Push notifications:
- 1 push per 30s per mailbox (messages)
- 1 push per 5s per mailbox (calls — shorter for time-sensitivity)

**File:** `server/index.js:93-117, 156-160, 393-407`

---

## 13. TURN Credentials

**Status: PASS (with notes)**

- Provider: Metered.ca
- 4 TURN server entries:
  - `turn:a.relay.metered.ca:80` (UDP)
  - `turn:a.relay.metered.ca:80?transport=tcp` (TCP)
  - `turn:a.relay.metered.ca:443` (UDP)
  - `turns:a.relay.metered.ca:443?transport=tcp` (TLS)
- **Primary delivery:** Via WebSocket after auth (`get-turn-credentials` -> `turn-credentials`)
- **HTTP fallback:** `/turn-credentials` endpoint — currently returns `503 "TURN access token not configured"` (TURN_ACCESS_TOKEN env var not set)
- **Client fallback chain:** WebSocket cache -> HTTP fetch -> STUN only (last resort)
- **Env vars needed on Railway:** `TURN_USERNAME`, `TURN_CREDENTIAL`, (optional) `TURN_ACCESS_TOKEN`

**Note:** TURN_ACCESS_TOKEN not set means HTTP fallback is disabled. This is acceptable since WebSocket delivery works, but it means TURN credentials are unavailable before WebSocket auth completes.

**File:** `server/index.js:192-212, 773-794`, `src/utils/constants.ts:43-75`

---

## Issues Found

### CRITICAL-1: Android PushTokenService sends `platform: 'ios'`

**File:** `QRChat-Android/src/services/PushTokenService.ts:63`

```typescript
SignalingClient.send({
  type: 'register-push-token',
  mailboxId,
  platform: 'ios',  // BUG: should be 'android'
  token: apnsToken,
});
```

**Impact:** When an Android user registers their FCM push token, the server stores it with `platform: 'ios'`. When `sendPush()` is called for this user, it checks `tokenEntry.platform === 'android'` and finds `'ios'` instead, so it falls through to `sendSilentPush()` (APNs). APNs will fail because the token is actually an FCM registration token, not an APNs device token. **Result: Android users will NEVER receive push notifications.**

**Fix:** Change `platform: 'ios'` to `platform: 'android'` in the Android version, and also rename the parameter from `apnsToken` to `pushToken` for clarity.

---

### HIGH-1: No server-side auth timeout

**File:** `server/index.js:409-418`

Server sends `auth-challenge` but never enforces a timeout for the client to respond. A client can connect, receive the challenge, and stay connected indefinitely without authenticating (if GRACE_PERIOD is false, it can't send messages, but still consumes a connection slot).

**Recommendation:** Add a timeout (e.g., 10s) after sending auth-challenge. If no valid `auth-response` is received, terminate the connection.

---

### MEDIUM-1: TURN HTTP fallback disabled in production

The `/turn-credentials` HTTP endpoint requires `TURN_ACCESS_TOKEN` env var, which is not set on Railway (returns 503). This means TURN credentials are only available via WebSocket. If WebSocket auth fails or the client needs TURN servers before connecting (unlikely but possible for pre-flight ICE), they won't be available.

**Recommendation:** Set `TURN_ACCESS_TOKEN` on Railway and embed it in the client app, or accept that WebSocket-only delivery is sufficient.

---

### MEDIUM-2: Server health exposes client count

**File:** `server/index.js:187-189`

```javascript
app.get('/health', (req, res) => {
  res.json({ status: 'ok', clients: clients.size });
});
```

Exposes the number of connected clients to anyone. This could be used for traffic analysis.

**Recommendation:** Remove `clients` from public health endpoint, or add an admin auth check.

---

### MEDIUM-3: Pending message queue JSON serialization overhead

**File:** `server/index.js:377-383`

Size check recalculates `JSON.stringify()` for every message in the queue on each insertion. For a queue near 1000 messages, this is O(n) string allocations per enqueue.

**Recommendation:** Cache cumulative size as a running counter instead of recalculating.

---

### LOW-1: No connection cleanup for unauthenticated idle clients

Connected clients that never register sit in memory. The 10s ping keeps them alive but they consume memory.

---

### LOW-2: Push token persistence race condition

**File:** `server/push.js:120-128`

`savePushToDisk()` writes two separate files (`PUSH_TOKENS_FILE` and `USER_MAILBOXES_FILE`). If the process crashes between the two writes, the maps become inconsistent.

**Recommendation:** Write to a single atomic file, or use a temporary file + rename pattern.

---

### LOW-3: SignalingClient send queue has no priority

All messages (file chunks, typing indicators, delivery receipts) share the same 500-item queue. Under pressure, important messages could be dropped in favor of typing indicators.

**Recommendation:** Priority queue or at least skip ephemeral messages (typing) when queue is > 80% full.

---

### INFO-1: iOS and Android share identical networking code

All files in `src/network/` and `src/services/` are byte-identical between QRChat (iOS) and QRChat-Android. This is good for consistency but means platform-specific bugs (like CRITICAL-1) get copied.

---

### INFO-2: Dual-path message delivery

Messages are sent on both P2P and relay simultaneously. This maximizes delivery reliability but doubles bandwidth. The receiver deduplicates correctly.

---

## Summary Table

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | Server health | PASS | 200 OK, 389ms |
| 2 | WebSocket connection | PASS | Auth challenge + relay pinning |
| 3 | Server ping (10s) | PASS | Native WS ping, terminates dead |
| 4 | Client heartbeat (30s) | PASS | App-level, 10s pong timeout |
| 5 | Reconnection logic | PASS | Exp backoff, 30s cap, queue flush |
| 6 | Message delivery iOS<->Android | PASS | Dual-path, dedup by messageId |
| 7 | File transfer chunking | PASS | 16KB P2P, 1.5MB relay, 5min TTL |
| 8 | Call signaling | PASS | Perfect negotiation, glare fix |
| 9 | Push notifications | **FAIL** | CRITICAL: Android sends `platform: 'ios'` |
| 10 | Pending messages | PASS | 48h, 1000/user, batch delivery |
| 11 | Push routing (sendPush) | PASS | Correct APNs/FCM routing logic |
| 12 | Rate limiting | PASS | Token bucket 200/20s + admin 5/60s |
| 13 | TURN credentials | PASS | Metered.ca, WS delivery works |

---

## Priority Fix List

1. **CRITICAL-1:** Fix `platform: 'ios'` -> `platform: 'android'` in `QRChat-Android/src/services/PushTokenService.ts:63`
2. **HIGH-1:** Add auth timeout on server (10s after challenge)
3. **MEDIUM-2:** Remove client count from `/health`
4. **MEDIUM-3:** Cache pending queue size calculation
5. **LOW-2:** Atomic push token persistence
