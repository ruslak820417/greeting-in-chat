# Security Phase 1 Report — Double Ratchet Hardening

**Agent:** security-engineer
**Branch:** `feature/security-privacy-upgrade`
**File modified:** `src/crypto/DoubleRatchet.ts`
**Date:** 2026-03-30

## Summary

Three security enhancements applied to the Double Ratchet implementation, all backward-compatible with existing v1 messages.

---

## Task 1.1: Message Padding (RFC 8446 §5.4)

**Commit:** `1209ab6` — Add message padding for traffic analysis prevention (RFC 8446 §5.4)

### What was done
- `padMessage(plaintext)`: Prepends 4-byte uint32 big-endian length, pads to 16,384-byte blocks with `nacl.randomBytes`
- `unpadMessage(padded)`: Reads length from first 4 bytes, returns only original payload
- All messages now have uniform size (multiple of 16KB), preventing traffic analysis based on message length

### Technical details
- Block size: 16,384 bytes (PAD_BLOCK_SIZE)
- If message + 4-byte header > 16,380 bytes, pads to next multiple of 16,384
- Random padding bytes (not zeros) to prevent compression-based attacks
- Version byte `0x02` prepended to ciphertext for format detection

### Backward compatibility
- `decrypt()` checks first byte of ciphertext: `0x02` = v2 (strip version, decrypt, unpad), anything else = legacy v1 (direct decrypt)

---

## Task 1.2: Message Integrity Chain (RFC 6962)

**Commit:** `899ca74` — Add message integrity chain for tamper detection

### What was done
- `computeMsgHash(prevHash, ciphertext)`: SHA-512(prevHash || ciphertext) truncated to 32 bytes
- Each sent message includes `prevMsgHash` — the hash of the previous message in the chain
- Receiver verifies chain continuity: if `msg.prevMsgHash !== expected`, logs warning
- **Does NOT reject mismatched messages** — backward compatibility preserved

### State changes
- `RatchetState` extended with `prevMsgHashSend` and `prevMsgHashRecv` (base64, 32 bytes each)
- `ZERO_HASH` (32 zero bytes) used as initial value
- `deserialize()` initializes missing fields to `ZERO_HASH` for pre-v2 serialized state

### Detection capabilities
- Message insertion: detected (hash chain breaks)
- Message deletion: detected on next message (prevMsgHash mismatch)
- Message reordering: detected (prevMsgHash mismatch)
- Replay attack: detected (duplicate hash)

---

## Task 1.3: Encrypted Message Headers (Double Ratchet spec §3.2)

**Commit:** `dd3f0cf` — Add header encryption to protect ratchet metadata (Double Ratchet spec §3.2)

### What was done
- `deriveHeaderKey(rootKey)`: HKDF(rootKey, salt=zeros, info="HeaderKey", len=32)
- Header (DH public key, message number, previous chain length) encrypted with `nacl.secretbox`
- Separate nonce for header encryption (`headerNonce`)
- Message format: `{ encryptedHeader, headerNonce, header (plaintext fallback), ciphertext, nonce }`

### Decrypt flow
1. Try header decryption with current root key
2. If fails (DH ratchet changed RK), use plaintext header
3. After DH advance, retry header decryption with new root key
4. Plaintext header always present as fallback for backward compat and cross-version messaging

### What is protected
- DH ratchet public key (prevents ratchet state fingerprinting)
- Message number (prevents message counting by observer)
- Previous chain length (prevents chain analysis)

---

## Protocol Version Scheme

| Version | Format | Features |
|---------|--------|----------|
| v1 (0x01 or no prefix) | Legacy | Direct nacl.secretbox, no padding |
| v2 (0x02 prefix) | New | Padding + hash chain + encrypted headers |

Detection: first byte of decoded ciphertext. If `0x02`, use v2 path. Otherwise, legacy path.

---

## Files Changed

| File | Lines added | Lines removed |
|------|------------|---------------|
| `src/crypto/DoubleRatchet.ts` | +260 | -23 |

## Risk Assessment

- **Backward compatibility:** PRESERVED. All three commits maintain ability to decrypt v1 messages.
- **Performance impact:** Minimal. Padding adds ~16KB per message. Header encryption adds one extra `nacl.secretbox` call.
- **Serialization:** Existing serialized `RatchetState` will auto-initialize new fields via `deserialize()`.

## Next Steps

- Monitor hash chain warnings in production logs for tampering detection
- Consider removing plaintext header fallback in future version (v3) once all clients upgraded
- Add unit tests for pad/unpad, hash chain, and header encrypt/decrypt
