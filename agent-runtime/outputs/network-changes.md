# Network Engineer — Change Log

## 2026-03-21 — Faza 2 Fixes

### 1. Event handler cleanup (WebRTCManager.ts)
**Problem:** `initialize()` registered SignalingClient handlers (`offer`, `answer`, `ice-candidate`) without storing references. Re-calling `initialize()` created duplicate handlers causing race conditions and double call processing.

**Fix:**
- Added `signalingHandlers` array to store handler references
- `initialize()` now calls `removeSignalingHandlers()` before registering new handlers
- Added `destroy()` public method for full teardown (peers + handlers + chunk buffers)
- Added `removeSignalingHandlers()` private method that calls `SignalingClient.off()` for each stored handler

### 2. DHT XOR distance overflow (DHTManager.ts)
**Problem:** `xorDistance()` used `distance << 4` (bitwise left shift) which operates on signed 32-bit integers. When MSB was set after processing 8 hex chars, the distance became negative. `Math.log2(negative)` returned `NaN`, causing `getBucketIndex()` to return `NaN` → peers placed in wrong/undefined buckets.

**Fix:** Replaced `(distance << 4) | xor` with `distance * 16 + xor`. JavaScript multiplication uses 64-bit float (safe up to 2^53), avoiding the signed 32-bit overflow entirely.

### 3. Outgoing call timeout — 45 seconds (WebRTCManager.ts)
**Problem:** Outgoing calls ring indefinitely if nobody answers.

**Fix:**
- Added `callTimeouts` Map and `OUTGOING_CALL_TIMEOUT = 45000`
- `startCall()` sets a 45s timer; if peer not connected by then, auto-calls `endCall()`
- Timer cleared in `markConnected()` (call answered) and `endCall()` (manual hangup)

### 4. Chunk buffer cleanup — 5min TTL (WebRTCManager.ts)
**Problem:** Chunk buffers from failed file transfers stay in memory forever.

**Fix:**
- Added `createdAt` timestamp to `ChunkBuffer` interface
- Added `CHUNK_BUFFER_TTL = 5min` and `CHUNK_CLEANUP_INTERVAL = 60s`
- `initialize()` starts a periodic cleanup timer; `destroy()` clears it
- `cleanStaleChunkBuffers()` removes buffers older than 5 minutes

### 5. Reconnection backoff cap (SignalingClient.ts)
**Problem:** Exponential backoff was capped at 60s, should be 30s per spec.

**Fix:** Changed `60000` → `30000` in `scheduleReconnect()`.

### 6. Client heartbeat — ping/pong every 30s (SignalingClient.ts)
**Problem:** No client-side heartbeat. Half-open (zombie) connections stay open until TCP timeout (~2 hours).

**Fix:**
- Added `startHeartbeat()` / `stopHeartbeat()` methods
- Sends `{ type: 'ping' }` every 30s after registration
- If no `{ type: 'pong' }` within 10s, closes connection and triggers reconnect
- Heartbeat stopped on `disconnect()`, `ws.onclose`, and before starting new one
- **Note:** Requires server-side `ping`/`pong` handler — requested from backend-engineer

### 7. CallKit single-call tracking fix (CallKitService.ts)
**Problem:** `activeCallData` was a single variable. If CallKit events didn't fire (race condition/bug), the variable was never cleared, blocking all subsequent calls. Also, if a new call came for the same contact while a stale one existed, the old UUID leaked in CallKit.

**Fix:**
- Replaced single `activeCallData` variable with `activeCalls: Map<string, CallData>`
- Tracks all calls by UUID — events now look up the correct call even with overlapping UUIDs
- `reportIncomingCall()` auto-cleans existing calls for the same contact before reporting new
- Added `endAllCalls()` as safety valve for completely stuck state
- Added `cleanStaleCalls()` timer (60s) that auto-ends calls CallKit never reported back on
- Added `reportedAt` timestamp to `CallData` interface for stale detection

### Already implemented (no changes needed)
- **ICE restart** — Already present: `attemptIceRestart()` with `iceRestart: true`, max 2 retries, triggered on `connectionState === 'failed'`
- **Message queue offline** — Already present: `sendQueue` with 500 max size, 30s TTL, `_flushQueue()` on reconnection
