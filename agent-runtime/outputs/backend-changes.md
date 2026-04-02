# Backend Engineer — Changes Log

## server/index.js

### 1. Pending Message Queue — Size-Based Limit (50MB per user)
- Added `MAX_PENDING_SIZE_PER_USER = 50 * 1024 * 1024` constant
- `enqueuePending()` now calculates total queue size via `JSON.stringify` before accepting new entries
- Rejects with warning log if adding the entry would exceed 50MB per user
- Works alongside existing count-based limit (1000 messages)

### 2. Comprehensive Input Validation on All WS Message Types
- Added helper functions: `isNonEmptyString(val, maxLen)`, `isBase64String(val, maxLen)`
- Added `VALID_MESSAGE_TYPES` whitelist Set — rejects unknown types early
- Added `validateMessage()` — validates message is object, type is string, type is in whitelist
- Per-type validation:
  - `auth-response`: validates `publicKey` and `signature` are valid base64 strings
  - `register`: validates `userId` is a non-empty string (max 256 chars)
  - `register-push-token`: validates `mailboxId` (max 256), `token` (max 512), sanitizes `platform` to ios/android
  - `ping-user`: validates `targetUserId` is non-empty string
  - `encrypted-message`: validates `payload` exists, `messageId` is valid if present
  - `delivery-receipt`: validates `messageId` format, `deliveredAt` is number if present
  - `read-receipt`: validates `messageIds` is non-empty array (max 100 items), `readAt` is number if present
  - `typing`: validates `isTyping` is boolean

### 3. Health Endpoint Sanitized
- `GET /` no longer exposes `connectedClients`, `pendingQueues`, or `uptime`
- Returns only `service` name and `status: 'running'`
- `GET /health` still returns client count (internal use)

### 4. Application-Level Ping/Pong Handler
- Added `'ping'` to `VALID_MESSAGE_TYPES` whitelist
- Added `case 'ping'` in WebSocket message handler — responds with `{ type: 'pong' }`
- Required by network-engineer for client-side heartbeat (RN can't send native WS pings)

### 5. POST /report Endpoint (Apple App Store Compliance)
- New endpoint: `POST /report`
- Accepts: `{ reporterId, reportedUserId, messageId, reason, timestamp }`
- Validates required fields: `reporterId`, `reportedUserId`, `reason`
- Persists reports to `qrchat_reports.json` in `DATA_DIR` (Railway volume)
- Logs each report to stdout for monitoring

### 6. TLS 1.3 Compliance
- Verified: Railway handles TLS termination at the edge (TLS 1.2 + 1.3)
- Server runs plain HTTP internally — no changes needed
- Client enforces `wss://` and domain pinning
- Full report: `agent-runtime/outputs/tls-compliance.md`

## Status
- All backend tasks DONE
