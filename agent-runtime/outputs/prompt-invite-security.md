# Prompt: security-engineer — Invite Link Crypto Module (Faza 1)

## Obiectiv

Creeaza modulul `InviteLinkCrypto.ts` — toate operatiile criptografice pentru sistemul de invite links. Acest modul este INDEPENDENT de server/network — lucreaza doar cu bytes si strings.

## Context codebase

### Import pattern existent (foloseste EXACT aceste import-uri):
```typescript
import nacl from 'tweetnacl';
import { encodeBase64, decodeBase64, decodeUTF8, encodeUTF8 } from 'tweetnacl-util';
import 'react-native-get-random-values';
```

### HKDF exista deja in `src/crypto/DoubleRatchet.ts` (liniile 24-52):
```typescript
function hmacSha512(key: Uint8Array, data: Uint8Array): Uint8Array {
  const blockSize = 128;
  let k = key.length > blockSize ? nacl.hash(key) : key;
  const iPad = new Uint8Array(blockSize);
  const oPad = new Uint8Array(blockSize);
  for (let i = 0; i < blockSize; i++) {
    iPad[i] = (k[i] || 0) ^ 0x36;
    oPad[i] = (k[i] || 0) ^ 0x5c;
  }
  const inner = nacl.hash(concat(iPad, data));
  return nacl.hash(concat(oPad, inner));
}

function hkdf(ikm: Uint8Array, salt: Uint8Array, info: Uint8Array, length: number): Uint8Array {
  if (length > 64) throw new Error('HKDF output too long');
  const prk = hmacSha512(salt.length ? salt : new Uint8Array(64), ikm);
  const t = hmacSha512(prk, concat(info, new Uint8Array([1])));
  return t.slice(0, length);
}

function concat(...arrays: Uint8Array[]): Uint8Array {
  const total = arrays.reduce((sum, a) => sum + a.length, 0);
  const result = new Uint8Array(total);
  let offset = 0;
  for (const a of arrays) { result.set(a, offset); offset += a.length; }
  return result;
}
```

### KeyManager.ts (singleton) — metode relevante:
- `KeyManager.getPublicKey()` → `string | null` (base64 X25519 public key)
- `KeyManager.getSignPublicKey()` → `string | null` (base64 Ed25519 public key)
- `KeyManager.signMessage(data: Uint8Array)` → `string` (base64 Ed25519 detached signature)
- `KeyManager.getSecretKeyBytes()` → `Uint8Array | null` (raw X25519 private key)

### Tipuri existente (`src/utils/types.ts`):
```typescript
interface QRPayload {
  pub: string;       // Base64 X25519 public key
  fp: string;        // Fingerprint XXXX-XXXX-XXXX-XXXX
  name: string;      // Display name
  sig: string;       // Base64 Ed25519 detached signature
  ts: number;        // Timestamp
  signPub?: string;  // Base64 Ed25519 public key
}
```

### Helper existent (`src/utils/helpers.ts`):
- `formatFingerprint(fp: string)` → `string` (XXXX-XXXX-XXXX-XXXX format)

---

## Modelul de securitate (Signal-inspired, zero-knowledge server)

### Principii:
1. **linkSecret** (32 bytes random) — generat de Alice, pus in URL fragment (#)
2. **URL fragment NICIODATA nu ajunge la server** — browserul/app-ul il pastreaza local
3. Serverul stocheaza DOAR date criptate — nu vede cheile publice plaintext
4. Din linkSecret se deriveaza:
   - **linkId** = HKDF(linkSecret, info="qrchat-link-id") → 8 bytes → 16 hex chars (pentru URL path)
   - **encKey** = HKDF(linkSecret, info="qrchat-link-enc") → 32 bytes (pentru nacl.secretbox)

### Flow complet:
```
ALICE (creator):
1. linkSecret = nacl.randomBytes(32)
2. linkId = hex(HKDF(linkSecret, "qrchat-link-id", 8))
3. encKey = HKDF(linkSecret, "qrchat-link-enc", 32)
4. payload = { pub, signPub, name, fp }
5. nonce = nacl.randomBytes(24)
6. ciphertext = nacl.secretbox(JSON.stringify(payload), nonce, encKey)
7. signature = Ed25519.sign(ciphertext, Alice.signPrivateKey)
8. Trimite la server: { linkId, ciphertext, nonce, signature }
9. Partajeaza URL: https://domain/invite/LINK_ID#base64url(linkSecret)

BOB (acceptor):
1. Primeste URL → extrage linkId din path, linkSecret din fragment
2. linkId_check = hex(HKDF(linkSecret, "qrchat-link-id", 8)) — trebuie sa coincida
3. encKey = HKDF(linkSecret, "qrchat-link-enc", 32)
4. Fetch de pe server: ciphertext, nonce, signature (folosind linkId)
5. plaintext = nacl.secretbox.open(ciphertext, nonce, encKey)
6. payload = JSON.parse(plaintext) → { pub, signPub, name, fp }
7. Verifica: nacl.sign.detached.verify(ciphertext, signature, payload.signPub)
8. Daca valid → Alice e autentificata, Bob are cheile ei
9. Bob creeaza propriul payload criptat (cheile lui) cu acelasi encKey
10. Bob trimite la server: { acceptor_ciphertext, acceptor_nonce, acceptor_signature }
11. Alice primeste (via Realtime) payload-ul criptat al lui Bob → decripteaza cu encKey
12. Ambii au cheile celuilalt → adauga ca contact → incep chat E2E
```

---

## Fisierul de creat

### `/Users/ruslanconstantinovici/QRChat/src/crypto/InviteLinkCrypto.ts`

```typescript
/**
 * InviteLinkCrypto — Cryptographic operations for the invite link system.
 *
 * Security model: Zero-knowledge server. The linkSecret never leaves the URL fragment.
 * Server stores only encrypted blobs it cannot read.
 */
import nacl from 'tweetnacl';
import {
  encodeBase64,
  decodeBase64,
  decodeUTF8,
  encodeUTF8,
} from 'tweetnacl-util';
import 'react-native-get-random-values';
import KeyManager from './KeyManager';

// ============================================================
// Types
// ============================================================

export interface InvitePayload {
  pub: string;      // Base64 X25519 public key
  signPub: string;  // Base64 Ed25519 public key
  name: string;     // Display name
  fp: string;       // Fingerprint XXXX-XXXX-XXXX-XXXX
}

export interface EncryptedInvite {
  linkId: string;              // Hex string (16 chars), derived from linkSecret
  ciphertext: string;          // Base64 nacl.secretbox output
  nonce: string;               // Base64 24-byte nonce
  signature: string;           // Base64 Ed25519 detached signature of ciphertext
}

export interface InviteURLParts {
  linkId: string;              // From URL path
  linkSecret: Uint8Array;      // From URL fragment (after #)
}

export type TTLOption = '30m' | '1h' | '24h';

// ============================================================
// Internal: HKDF (reuse from DoubleRatchet pattern)
// ============================================================

function concat(...arrays: Uint8Array[]): Uint8Array {
  const total = arrays.reduce((sum, a) => sum + a.length, 0);
  const result = new Uint8Array(total);
  let offset = 0;
  for (const a of arrays) {
    result.set(a, offset);
    offset += a.length;
  }
  return result;
}

function hmacSha512(key: Uint8Array, data: Uint8Array): Uint8Array {
  const blockSize = 128;
  const k = key.length > blockSize ? nacl.hash(key) : key;
  const iPad = new Uint8Array(blockSize);
  const oPad = new Uint8Array(blockSize);
  for (let i = 0; i < blockSize; i++) {
    iPad[i] = (k[i] || 0) ^ 0x36;
    oPad[i] = (k[i] || 0) ^ 0x5c;
  }
  const inner = nacl.hash(concat(iPad, data));
  return nacl.hash(concat(oPad, inner));
}

function hkdf(
  ikm: Uint8Array,
  salt: Uint8Array,
  info: Uint8Array,
  length: number,
): Uint8Array {
  if (length > 64) throw new Error('HKDF output too long (max 64)');
  const prk = hmacSha512(salt.length ? salt : new Uint8Array(64), ikm);
  const t = hmacSha512(prk, concat(info, new Uint8Array([1])));
  return t.slice(0, length);
}

// ============================================================
// Internal: Base64URL encoding (URL-safe, no padding)
// ============================================================

function toBase64URL(bytes: Uint8Array): string {
  return encodeBase64(bytes)
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

function fromBase64URL(str: string): Uint8Array {
  let base64 = str.replace(/-/g, '+').replace(/_/g, '/');
  while (base64.length % 4 !== 0) base64 += '=';
  return decodeBase64(base64);
}

// ============================================================
// Internal: Hex encoding
// ============================================================

function toHex(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

function fromHex(hex: string): Uint8Array {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) {
    bytes[i / 2] = parseInt(hex.substring(i, i + 2), 16);
  }
  return bytes;
}

// ============================================================
// HKDF info constants
// ============================================================

const HKDF_SALT = new Uint8Array(0); // empty salt
const HKDF_INFO_LINK_ID = decodeUTF8('qrchat-invite-link-id');
const HKDF_INFO_ENC_KEY = decodeUTF8('qrchat-invite-enc-key');
const LINK_ID_LENGTH = 8;   // 8 bytes → 16 hex chars
const ENC_KEY_LENGTH = 32;  // 32 bytes for nacl.secretbox

// ============================================================
// Public API
// ============================================================

/**
 * Generate a cryptographically random link secret (32 bytes).
 * This is the root of all derived keys for one invite.
 */
export function generateLinkSecret(): Uint8Array {
  return nacl.randomBytes(32);
}

/**
 * Derive the linkId from a linkSecret.
 * Used as the invite code in the URL path and as the DB lookup key.
 * Returns a 16-char hex string.
 */
export function deriveLinkId(linkSecret: Uint8Array): string {
  const derived = hkdf(linkSecret, HKDF_SALT, HKDF_INFO_LINK_ID, LINK_ID_LENGTH);
  return toHex(derived);
}

/**
 * Derive the encryption key from a linkSecret.
 * Used for nacl.secretbox encrypt/decrypt of the invite payload.
 * Returns a 32-byte Uint8Array.
 */
export function deriveEncryptionKey(linkSecret: Uint8Array): Uint8Array {
  return hkdf(linkSecret, HKDF_SALT, HKDF_INFO_ENC_KEY, ENC_KEY_LENGTH);
}

/**
 * Encrypt an invite payload using a linkSecret.
 *
 * @param payload - The invite data (public keys, name, fingerprint)
 * @param linkSecret - The 32-byte link secret
 * @returns EncryptedInvite with linkId, ciphertext, nonce, signature
 * @throws if KeyManager has no signing key loaded
 */
export function encryptInvitePayload(
  payload: InvitePayload,
  linkSecret: Uint8Array,
): EncryptedInvite {
  const linkId = deriveLinkId(linkSecret);
  const encKey = deriveEncryptionKey(linkSecret);

  // Serialize payload to bytes
  const plaintext = decodeUTF8(JSON.stringify(payload));

  // Generate random nonce (24 bytes for XSalsa20-Poly1305)
  const nonce = nacl.randomBytes(nacl.secretbox.nonceLength); // 24 bytes

  // Encrypt with nacl.secretbox (XSalsa20-Poly1305)
  const ciphertext = nacl.secretbox(plaintext, nonce, encKey);
  if (!ciphertext) {
    throw new Error('Encryption failed');
  }

  // Sign the ciphertext with Ed25519 (proves creator identity)
  const signature = KeyManager.signMessage(ciphertext);

  return {
    linkId,
    ciphertext: encodeBase64(ciphertext),
    nonce: encodeBase64(nonce),
    signature,
  };
}

/**
 * Decrypt an invite payload using a linkSecret.
 * Verifies Ed25519 signature after decryption.
 *
 * @param encrypted - The encrypted invite data from server
 * @param linkSecret - The 32-byte link secret (from URL fragment)
 * @returns The decrypted payload, or null if decryption/verification fails
 */
export function decryptInvitePayload(
  encrypted: { ciphertext: string; nonce: string; signature: string },
  linkSecret: Uint8Array,
): InvitePayload | null {
  try {
    const encKey = deriveEncryptionKey(linkSecret);
    const ciphertextBytes = decodeBase64(encrypted.ciphertext);
    const nonceBytes = decodeBase64(encrypted.nonce);

    // Decrypt
    const plaintext = nacl.secretbox.open(ciphertextBytes, nonceBytes, encKey);
    if (!plaintext) {
      console.warn('[InviteLinkCrypto] Decryption failed — wrong key or corrupted data');
      return null;
    }

    // Parse payload
    const payload: InvitePayload = JSON.parse(encodeUTF8(plaintext));

    // Verify required fields
    if (!payload.pub || !payload.signPub || !payload.name || !payload.fp) {
      console.warn('[InviteLinkCrypto] Invalid payload — missing required fields');
      return null;
    }

    // Verify Ed25519 signature (ciphertext was signed by creator)
    const signatureBytes = decodeBase64(encrypted.signature);
    const signPublicKeyBytes = decodeBase64(payload.signPub);
    const isValid = nacl.sign.detached.verify(
      ciphertextBytes,
      signatureBytes,
      signPublicKeyBytes,
    );

    if (!isValid) {
      console.warn('[InviteLinkCrypto] Signature verification failed');
      return null;
    }

    return payload;
  } catch (error) {
    console.error('[InviteLinkCrypto] decryptInvitePayload error:', error);
    return null;
  }
}

/**
 * Create the invite payload from the current user's keys.
 * Reads keys from KeyManager.
 *
 * @param displayName - User's display name
 * @param fingerprint - User's fingerprint (XXXX-XXXX-XXXX-XXXX)
 * @returns InvitePayload ready for encryption
 * @throws if keys are not loaded in KeyManager
 */
export function createMyPayload(
  displayName: string,
  fingerprint: string,
): InvitePayload {
  const pub = KeyManager.getPublicKey();
  const signPub = KeyManager.getSignPublicKey();

  if (!pub || !signPub) {
    throw new Error('Keys not loaded in KeyManager');
  }

  return {
    pub,
    signPub,
    name: displayName,
    fp: fingerprint,
  };
}

// ============================================================
// URL Construction / Parsing
// ============================================================

const INVITE_BASE_URL = 'https://exciting-success-production-d272.up.railway.app';

/**
 * Build the full invite URL with linkSecret in the fragment.
 * Format: https://domain/invite/LINK_ID#base64url(linkSecret)
 *
 * The fragment (after #) is NEVER sent to the server.
 */
export function buildInviteURL(linkId: string, linkSecret: Uint8Array): string {
  const secretFragment = toBase64URL(linkSecret);
  return `${INVITE_BASE_URL}/invite/${linkId}#${secretFragment}`;
}

/**
 * Parse an invite URL to extract linkId and linkSecret.
 * Supports:
 *   - https://domain/invite/LINK_ID#base64url(linkSecret)
 *   - qrchat://invite/LINK_ID#base64url(linkSecret)
 *
 * @returns InviteURLParts or null if URL is invalid
 */
export function parseInviteURL(url: string): InviteURLParts | null {
  try {
    // Extract the fragment (after #)
    const hashIndex = url.indexOf('#');
    if (hashIndex === -1) {
      console.warn('[InviteLinkCrypto] No fragment in URL');
      return null;
    }

    const fragment = url.substring(hashIndex + 1);
    const urlWithoutFragment = url.substring(0, hashIndex);

    // Extract linkId from path: /invite/LINK_ID
    const match = urlWithoutFragment.match(/\/invite\/([a-f0-9]{16})$/i);
    if (!match) {
      console.warn('[InviteLinkCrypto] Invalid invite URL path');
      return null;
    }

    const linkId = match[1].toLowerCase();
    const linkSecret = fromBase64URL(fragment);

    // Validate linkSecret length
    if (linkSecret.length !== 32) {
      console.warn('[InviteLinkCrypto] Invalid linkSecret length:', linkSecret.length);
      return null;
    }

    // Validate that linkId matches the derivation
    const expectedLinkId = deriveLinkId(linkSecret);
    if (linkId !== expectedLinkId) {
      console.warn('[InviteLinkCrypto] linkId does not match derived value');
      return null;
    }

    return { linkId, linkSecret };
  } catch (error) {
    console.error('[InviteLinkCrypto] parseInviteURL error:', error);
    return null;
  }
}

// ============================================================
// TTL helpers
// ============================================================

/**
 * Get the expiration date for a given TTL option.
 */
export function getExpiresAt(ttl: TTLOption): Date {
  const now = new Date();
  switch (ttl) {
    case '30m':
      return new Date(now.getTime() + 30 * 60 * 1000);
    case '1h':
      return new Date(now.getTime() + 60 * 60 * 1000);
    case '24h':
      return new Date(now.getTime() + 24 * 60 * 60 * 1000);
  }
}

/**
 * Check if an invite has expired.
 */
export function isExpired(expiresAt: string | Date): boolean {
  const expiry = typeof expiresAt === 'string' ? new Date(expiresAt) : expiresAt;
  return new Date() > expiry;
}

/**
 * Get remaining time in a human-readable format.
 * Returns: { minutes, seconds, display } or null if expired.
 */
export function getRemainingTime(expiresAt: string | Date): {
  minutes: number;
  seconds: number;
  display: string;
} | null {
  const expiry = typeof expiresAt === 'string' ? new Date(expiresAt) : expiresAt;
  const now = new Date();
  const remainingMs = expiry.getTime() - now.getTime();

  if (remainingMs <= 0) return null;

  const totalSeconds = Math.floor(remainingMs / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;

  let display: string;
  if (minutes >= 60) {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    display = `${hours}h ${mins}m`;
  } else {
    display = `${minutes}m ${seconds}s`;
  }

  return { minutes, seconds, display };
}

// ============================================================
// Base64URL exports (needed by InviteLinkService for URL handling)
// ============================================================

export { toBase64URL, fromBase64URL, toHex, fromHex };
```

---

## Pasi de implementare

### Pas 1: Creeaza fisierul
Creeaza `/Users/ruslanconstantinovici/QRChat/src/crypto/InviteLinkCrypto.ts` cu codul de mai sus.

### Pas 2: Verifica ca KeyManager.signMessage() accepta Uint8Array
Citeste `src/crypto/KeyManager.ts` si confirma ca metoda `signMessage(data: Uint8Array)` exista si returneaza base64 string. Daca semnatura e diferita, adapteaza apelul in `encryptInvitePayload()`.

### Pas 3: Verifica import-urile
Asigura-te ca `tweetnacl` si `tweetnacl-util` sunt in `package.json` (SUNT — nu trebuie instalate).

### Pas 4: Test manual rapid
In `src/crypto/InviteLinkCrypto.ts`, adauga un bloc de test la sfarsit (comentat, pentru debug):

```typescript
// === DEBUG TEST (remove before production) ===
// export function _selfTest(): boolean {
//   const secret = generateLinkSecret();
//   const linkId = deriveLinkId(secret);
//   const encKey = deriveEncryptionKey(secret);
//
//   // Verify deterministic derivation
//   const linkId2 = deriveLinkId(secret);
//   const encKey2 = deriveEncryptionKey(secret);
//   if (linkId !== linkId2) return false;
//   if (encodeBase64(encKey) !== encodeBase64(encKey2)) return false;
//
//   // Verify URL round-trip
//   const url = buildInviteURL(linkId, secret);
//   const parsed = parseInviteURL(url);
//   if (!parsed) return false;
//   if (parsed.linkId !== linkId) return false;
//   if (encodeBase64(parsed.linkSecret) !== encodeBase64(secret)) return false;
//
//   console.log('[InviteLinkCrypto] Self-test PASSED');
//   return true;
// }
```

---

## Reguli stricte

1. **NU modifica** `DoubleRatchet.ts` — duplicheaza HKDF in InviteLinkCrypto.ts (evita regresia)
2. **NU modifica** `KeyManager.ts` — foloseste API-ul existent
3. **NU instala** pachete noi — totul e deja in package.json
4. **NU crea** fisiere de test (qa-engineer face asta in Faza 3)
5. **NU adauga** stringuri i18n (frontend-engineer face asta in Faza 2)
6. **Formatul URL**: `https://exciting-success-production-d272.up.railway.app/invite/LINK_ID#base64url(linkSecret)`
7. linkId = 16 hex chars (8 bytes HKDF output)
8. linkSecret = 32 bytes random, base64url encoded in fragment
9. Encryption: nacl.secretbox (XSalsa20-Poly1305)
10. Signature: Ed25519 detached, over ciphertext (not plaintext)

---

## Output

Dupa ce ai terminat:

1. Scrie in `agent-runtime/state/status.md`:
   ```
   | security-engineer | DONE | InviteLinkCrypto.ts creat si testat | — |
   ```

2. Scrie in `agent-runtime/messages/security-to-backend.md`:
   ```
   # Mesaj de la security-engineer catre backend-engineer

   InviteLinkCrypto.ts este gata.

   Ce trebuie sa stii:
   - Import: `import { EncryptedInvite, InvitePayload, TTLOption, ... } from '../crypto/InviteLinkCrypto'`
   - Serverul primeste: { linkId, ciphertext, nonce, signature, creator_display_name (optional), ttl_option }
   - Serverul stocheaza exact aceste campuri (NU decripteaza niciodata)
   - linkId este cheia de cautare in DB (UNIQUE, 16 hex chars)
   - ciphertext si nonce sunt base64 strings
   - signature este base64 Ed25519 detached signature over ciphertext
   ```

---

## Dependente

- **Depinzi de**: nimic (poti incepe imediat)
- **Te asteapta**: backend-engineer (schema DB + Edge Functions), frontend-engineer (ecrane), qa-engineer (teste)
- **Nu blochezi** pe nimeni — backend-engineer poate lucra la schema/Edge Functions in paralel, folosind tipurile EncryptedInvite ca referinta
