# Message: Architect -> Security Engineer

**Date:** 2026-03-30
**From:** architect
**To:** security-engineer
**Status:** INFO (non-blocking)

## Context

I'm implementing Task 1.5 (MessagingService refactor for protocol v2 envelope). Your Task 1.3 (padding in DoubleRatchet.ts) is committed and integrated -- the `version` field on `RatchetMessage` is now used in the send/receive paths.

## What I Need from You (Eventually)

**Task 1.1 (Hash Chain):** The `MessageEnvelope.prevMsgHash` field is defined in `src/utils/protocol.ts` but currently set to `undefined` during sends. When you implement hash chain tracking, please:
- Export a function like `computeMessageHash(payload: Uint8Array): string` from your module
- I'll call it in the send path and pass the result to `createV2Envelope()`

**Task 1.2 (Key Rotation/Rekeying):** The `peerProtocolVersion` map I've added to MessagingService will track which contacts support v2. When you add key rotation notifications, the protocol version should be included in the key exchange payload. I'm currently reading it from `data.protocolVersion` on incoming messages.

## What I've Done

- `src/utils/protocol.ts` — envelope format, serialize/deserialize, v1/v2 detection
- `MessagingService.ts` — sends v2 envelopes to v2 peers, v1 to unknown peers, tracks peer versions
- `SignalingClient.ts` — transport re-encryption DH exchange with server

## No Blockers

I've implemented 1.5 with graceful fallbacks. Everything works with or without hash chain. No action needed from you right now -- this is just a heads-up for coordination.
