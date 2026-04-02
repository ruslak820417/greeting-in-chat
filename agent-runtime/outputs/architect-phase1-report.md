# Architect Phase 1 Report

**Agent:** architect
**Date:** 2026-03-30
**Branch:** `feature/security-privacy-upgrade`
**Status:** COMPLETE (3/3 tasks)

## Tasks Completed

### Task 1.4: Protocol Versioning
**Commit:** `40e9b5a` — Add protocol versioning for backward-compatible message format evolution
**File:** `src/utils/protocol.ts` (NEW, 278 lines)

- Defined `PROTOCOL_VERSION = 2` and `MIN_PROTOCOL_VERSION = 1`
- `MessageEnvelope` interface with version, encryptedHeader, encryptedBody, prevMsgHash, padding fields
- Binary serialize/deserialize with big-endian length-prefixed wire format
- v1 layout: `[version:1][bodyLen:4][body:N]`
- v2 layout: `[version:1][headerLen:4][header:N][bodyLen:4][body:M][flags:1][prevMsgHash?:44]`
- Helper functions: `createV1Envelope`, `createV2Envelope`, `isVersionedEnvelope`
- Forward compatible: unknown versions fall back to raw body parse

### Task 1.6: Server-Side Transport Re-encryption
**Commit:** `f4515ba` — Add transport re-encryption to prevent ciphertext correlation (NaCl crypto_box)
**Files:** `server/index.js`, `src/network/SignalingClient.ts`

Server side:
- Generates ephemeral X25519 key pair per connection at registration
- New `transport-dh-exchange` message type for client DH exchange
- Re-encrypts relayed `encrypted-message` payloads: unwraps sender's transport layer, re-wraps with recipient's transport key
- Ciphertext entering server differs from ciphertext leaving — prevents correlation by network observers
- E2E payload is never touched (only transport layer changes)
- Transport keys cleaned up on disconnect (ephemeral, per-connection)
- Graceful degradation: if transport unwrap fails, relays E2E payload as-is
- Queued messages for offline recipients stored without transport wrapping (keys are per-connection)

Client side (SignalingClient.ts):
- Generates ephemeral X25519 key pair on `registered` event
- Computes shared secret from server's transport public key via `nacl.box.before`
- `wrapTransportEnvelope()`: wraps outgoing E2E payloads in transport encryption
- `unwrapTransportPayload()`: unwraps incoming transport-encrypted payloads
- `sendEncryptedMessage()` automatically includes transport envelope when DH is complete
- Transport keys cleared on disconnect for forward secrecy

### Task 1.5: MessagingService Refactor for New Protocol
**Commit:** `009798f` — Integrate protocol v2 envelope in messaging pipeline with backward compatibility
**Files:** `src/services/MessagingService.ts`, `src/screens/QRScanScreen.tsx`, `src/screens/HomeScreen.tsx`, `src/screens/PendingApprovalScreen.tsx`, `src/screens/InviteAcceptScreen.tsx`

- Added `peerProtocolVersion: Map<string, number>` to track each contact's protocol version
- Send path: includes `protocolVersion` and `padding` flag when peer supports v2, omits for v1 peers
- Receive path: detects `protocolVersion` field on incoming messages and records per-peer
- Transport unwrapping: `handleRelayMessage()` unwraps `_transportEnvelope` before processing
- Handshake integration: `protocolVersion` included in all contact request and accept payloads across 4 screens
- Backward compatible: peers without `protocolVersion` default to v1

## Dependencies

- **Security-engineer Task 1.3 (Padding):** Integrated. Commit `1209ab6` adds padding to DoubleRatchet.ts.
- **Security-engineer Tasks 1.1 (Hash Chain), 1.2 (Key Rotation):** Not yet committed. `prevMsgHash` field is defined in protocol.ts but set to `undefined` in sends. Message sent to `agent-runtime/messages/architect-to-security.md` with coordination details. No blockers -- the system works without hash chain (it's additive).

## Architecture Notes

- Transport re-encryption is fully independent of E2E encryption -- they are layered
- Protocol version negotiation happens at two points: (1) first message received from peer, (2) handshake payloads
- All changes are backward compatible with v1 (pre-upgrade) clients
- Transport keys are ephemeral per-connection, providing forward secrecy for the transport layer
