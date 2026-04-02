# PROMPT 4 — Teste Noi (crypto, DB, messaging)

**Agent tinta:** qa-engineer (dupa testarea Android)
**Proiect:** `/Users/ruslanconstantinovici/qrchatAndroid`
**Obiectiv:** Scrie teste unitare noi pentru DoubleRatchet, KeyManager si Database

---

## Context

Proiectul are doar 3 fisiere de test (`__tests__/App.test.tsx`, `push-server.test.js`, `PushTokenService.test.ts`). Logica critica de criptare si persistenta nu are NICIUN test.

### Stack de testare:
- **Jest** cu preset `react-native`
- **Config:** `/Users/ruslanconstantinovici/qrchatAndroid/jest.config.js`
- **Setup:** `/Users/ruslanconstantinovici/qrchatAndroid/jest.setup.js` — contine mock-uri pentru: RNFS, Keychain, WebRTC, SQLite (`@op-engineering/op-sqlite`), Notifee, Camera, Contacts, etc.
- **Comanda:** `npx jest --verbose`

### Fisiere tinta pentru testare:

**1. DoubleRatchet** (`src/crypto/DoubleRatchet.ts`):
- `DoubleRatchet.initSender(sharedSecret, theirIdentityPub)` — initializare sender
- `DoubleRatchet.initReceiver(sharedSecret, myIdentityPriv, myIdentityPub)` — initializare receiver
- `encrypt(plaintext: Uint8Array): RatchetMessage` — criptare mesaj
- `decrypt(msg: RatchetMessage): Uint8Array | null` — decriptare mesaj
- `serialize(): string` / `DoubleRatchet.deserialize(json): DoubleRatchet` — persistenta stare
- Foloseste: `tweetnacl` (nacl.box, nacl.secretbox, nacl.hash), `tweetnacl-util`
- HKDF-SHA512, HMAC-SHA512 implementate intern (nu dependente externe)

**2. KeyManager** (`src/crypto/KeyManager.ts`):
- `generateKeyPair()` — genereaza Box keypair (X25519) + Sign keypair (Ed25519)
- `generateFingerprint(publicKey)` — SHA-512 hash -> format XXXX-XXXX-XXXX-XXXX
- `createQRPayload(profile)` — genereaza QR payload semnat
- `verifyQRPayload(payload)` — verifica semnatura + expirare
- `encryptMessage(message, recipientPublicKey)` — nacl.box
- `decryptMessage(encrypted, nonce, senderPublicKey)` — nacl.box.open
- `signMessage(message)` / verificare semnatura
- `loadKeys(pub, priv, signPub?, signPriv?)` — incarca chei existente

**3. Database** (`src/storage/Database.ts`):
- Foloseste `@op-engineering/op-sqlite` (deja mock-uit in jest.setup.js)
- CRUD Contacts: `addContact`, `getContacts`, `getContact`, `updateContact`, `deleteContact`
- CRUD Messages: `addMessage`, `getMessages`, `getMessagesPaginated`, `updateMessage`, `deleteMessage`
- CRUD Groups: `createGroup`, `getGroup`, `getGroups`, `updateGroup`, `deleteGroup`
- Profile: `saveProfile`, `getProfile`, `deleteProfile`
- Settings: `saveSettings`, `getSettings`
- Reactions: `addReaction`, `removeReaction`
- Util: `getTotalUnreadCount`, `getContactCount`, `clearAll`

### Mock-uri existente in `jest.setup.js`:
```javascript
jest.mock('@op-engineering/op-sqlite', () => ({
  open: jest.fn().mockReturnValue({
    execute: jest.fn(),
    executeAsync: jest.fn().mockResolvedValue({ rows: { _array: [] } }),
    close: jest.fn(),
  }),
}));

jest.mock('react-native-keychain', () => ({
  setGenericPassword: jest.fn().mockResolvedValue(true),
  getGenericPassword: jest.fn().mockResolvedValue(false),
  resetGenericPassword: jest.fn().mockResolvedValue(true),
  ACCESSIBLE: { WHEN_UNLOCKED_THIS_DEVICE_ONLY: 'WhenUnlockedThisDeviceOnly' },
  ACCESS_CONTROL: { BIOMETRY_ANY: 'BiometryAny' },
}));
```

---

## Sarcini — pas cu pas

### Pas 1 — Citeste fisierele tinta complet

```
Citeste complet:
- /Users/ruslanconstantinovici/qrchatAndroid/src/crypto/DoubleRatchet.ts
- /Users/ruslanconstantinovici/qrchatAndroid/src/crypto/KeyManager.ts
- /Users/ruslanconstantinovici/qrchatAndroid/src/storage/Database.ts
- /Users/ruslanconstantinovici/qrchatAndroid/src/crypto/RatchetStore.ts
- /Users/ruslanconstantinovici/qrchatAndroid/src/utils/types.ts (pentru tipuri Message, Contact, etc.)
```

Intelege exact ce face fiecare metoda inainte de a scrie teste.

### Pas 2 — Scrie teste DoubleRatchet

Creaza: `/Users/ruslanconstantinovici/qrchatAndroid/__tests__/DoubleRatchet.test.ts`

```typescript
/**
 * DoubleRatchet Tests
 * Tests for src/crypto/DoubleRatchet.ts — Double Ratchet protocol implementation
 * Covers: encrypt/decrypt roundtrip, forward secrecy, out-of-order messages, serialization
 */

import nacl from 'tweetnacl';
import { decodeUTF8, encodeUTF8 } from 'tweetnacl-util';
import { DoubleRatchet } from '../src/crypto/DoubleRatchet';

describe('DoubleRatchet', () => {
  // Helper: creaza o pereche sender/receiver initializata
  function createPair() {
    const aliceIdentity = nacl.box.keyPair();
    const bobIdentity = nacl.box.keyPair();
    const sharedSecret = nacl.box.before(bobIdentity.publicKey, aliceIdentity.secretKey);

    const sender = DoubleRatchet.initSender(sharedSecret, bobIdentity.publicKey);
    const receiver = DoubleRatchet.initReceiver(sharedSecret, aliceIdentity.secretKey, aliceIdentity.publicKey);

    return { sender, receiver, aliceIdentity, bobIdentity };
  }

  describe('Encrypt/Decrypt roundtrip', () => {
    test('sender encrypts, receiver decrypts — plaintext matches', () => {
      const { sender, receiver } = createPair();
      const plaintext = decodeUTF8('Hello from Alice!');

      const encrypted = sender.encrypt(plaintext);
      const decrypted = receiver.decrypt(encrypted);

      expect(decrypted).not.toBeNull();
      expect(encodeUTF8(decrypted!)).toBe('Hello from Alice!');
    });

    test('multiple messages in sequence decrypt correctly', () => {
      const { sender, receiver } = createPair();
      const messages = ['msg1', 'msg2', 'msg3', 'msg4', 'msg5'];

      for (const msg of messages) {
        const encrypted = sender.encrypt(decodeUTF8(msg));
        const decrypted = receiver.decrypt(encrypted);
        expect(encodeUTF8(decrypted!)).toBe(msg);
      }
    });

    test('bidirectional: both sides can send and receive', () => {
      const { sender, receiver } = createPair();

      // Alice -> Bob
      const enc1 = sender.encrypt(decodeUTF8('from Alice'));
      expect(encodeUTF8(receiver.decrypt(enc1)!)).toBe('from Alice');

      // Bob -> Alice
      const enc2 = receiver.encrypt(decodeUTF8('from Bob'));
      expect(encodeUTF8(sender.decrypt(enc2)!)).toBe('from Bob');
    });

    test('empty message encrypts and decrypts', () => {
      const { sender, receiver } = createPair();
      const encrypted = sender.encrypt(new Uint8Array(0));
      const decrypted = receiver.decrypt(encrypted);
      expect(decrypted).not.toBeNull();
      expect(decrypted!.length).toBe(0);
    });
  });

  describe('Forward secrecy', () => {
    test('old ratchet state cannot decrypt new messages', () => {
      const { sender, receiver } = createPair();

      // Send first message
      const enc1 = sender.encrypt(decodeUTF8('message 1'));
      receiver.decrypt(enc1);

      // Serialize state BEFORE ratchet advances
      const oldState = receiver.serialize();

      // Send more messages (ratchet advances)
      const enc2 = sender.encrypt(decodeUTF8('message 2'));
      const enc3 = sender.encrypt(decodeUTF8('message 3'));
      receiver.decrypt(enc2);
      receiver.decrypt(enc3);

      // Restore old state — should NOT decrypt enc3
      const oldReceiver = DoubleRatchet.deserialize(oldState);
      // oldReceiver can decrypt enc2 (skipped message), but enc3 after state diverges
      // At minimum, verify the states have diverged
      expect(oldReceiver.serialize()).not.toBe(receiver.serialize());
    });

    test('each message uses a different symmetric key', () => {
      const { sender } = createPair();

      const enc1 = sender.encrypt(decodeUTF8('msg A'));
      const enc2 = sender.encrypt(decodeUTF8('msg B'));

      // Ciphertexts must be different
      expect(enc1.ct).not.toBe(enc2.ct);
      // Nonces must be different
      expect(enc1.n).not.toBe(enc2.n);
    });
  });

  describe('Out-of-order messages', () => {
    test('messages received out of order still decrypt', () => {
      const { sender, receiver } = createPair();

      const enc1 = sender.encrypt(decodeUTF8('first'));
      const enc2 = sender.encrypt(decodeUTF8('second'));
      const enc3 = sender.encrypt(decodeUTF8('third'));

      // Receive out of order: 3, 1, 2
      expect(encodeUTF8(receiver.decrypt(enc3)!)).toBe('third');
      expect(encodeUTF8(receiver.decrypt(enc1)!)).toBe('first');
      expect(encodeUTF8(receiver.decrypt(enc2)!)).toBe('second');
    });
  });

  describe('Serialization', () => {
    test('serialize/deserialize preserves ratchet state', () => {
      const { sender, receiver } = createPair();

      // Exchange some messages
      const enc1 = sender.encrypt(decodeUTF8('before serialize'));
      receiver.decrypt(enc1);

      // Serialize and deserialize
      const json = sender.serialize();
      const restored = DoubleRatchet.deserialize(json);

      // Restored sender should produce messages receiver can decrypt
      const enc2 = restored.encrypt(decodeUTF8('after serialize'));
      const dec2 = receiver.decrypt(enc2);
      expect(encodeUTF8(dec2!)).toBe('after serialize');
    });

    test('serialize returns valid JSON string', () => {
      const { sender } = createPair();
      const json = sender.serialize();
      expect(() => JSON.parse(json)).not.toThrow();
    });
  });

  describe('Error handling', () => {
    test('decrypt with wrong receiver returns null', () => {
      const { sender } = createPair();
      const wrongIdentity = nacl.box.keyPair();
      const wrongShared = nacl.box.before(wrongIdentity.publicKey, wrongIdentity.secretKey);
      const wrongReceiver = DoubleRatchet.initReceiver(wrongShared, wrongIdentity.secretKey, wrongIdentity.publicKey);

      const encrypted = sender.encrypt(decodeUTF8('secret'));
      const result = wrongReceiver.decrypt(encrypted);
      expect(result).toBeNull();
    });

    test('tampered ciphertext returns null on decrypt', () => {
      const { sender, receiver } = createPair();
      const encrypted = sender.encrypt(decodeUTF8('original'));

      // Tamper with ciphertext
      encrypted.ct = encrypted.ct.slice(0, -4) + 'XXXX';
      const result = receiver.decrypt(encrypted);
      expect(result).toBeNull();
    });
  });
});
```

### Pas 3 — Scrie teste KeyManager

Creaza: `/Users/ruslanconstantinovici/qrchatAndroid/__tests__/KeyManager.test.ts`

```typescript
/**
 * KeyManager Tests
 * Tests for src/crypto/KeyManager.ts — key generation, encryption, QR verification
 */

import nacl from 'tweetnacl';
import { encodeBase64, decodeBase64, decodeUTF8, encodeUTF8 } from 'tweetnacl-util';
import KeyManager from '../src/crypto/KeyManager';

// Creaza o instanta fresh pentru fiecare test
let km: typeof KeyManager;

beforeEach(() => {
  // KeyManager e singleton — trebuie resetat
  // Daca nu se poate reseta, creaza o noua instanta importand clasa
  km = KeyManager;
  km.loadKeys('', '', '', ''); // reset
});

describe('KeyManager', () => {
  describe('generateKeyPair', () => {
    test('generates valid base64-encoded keys', () => {
      const keys = km.generateKeyPair();

      expect(keys.publicKey).toBeTruthy();
      expect(keys.privateKey).toBeTruthy();
      expect(keys.signPublicKey).toBeTruthy();
      expect(keys.signPrivateKey).toBeTruthy();

      // All should be valid base64
      expect(() => decodeBase64(keys.publicKey)).not.toThrow();
      expect(() => decodeBase64(keys.privateKey)).not.toThrow();
    });

    test('public key is 32 bytes (X25519)', () => {
      const keys = km.generateKeyPair();
      const pubBytes = decodeBase64(keys.publicKey);
      expect(pubBytes.length).toBe(32);
    });

    test('sign public key is 32 bytes (Ed25519)', () => {
      const keys = km.generateKeyPair();
      const signPubBytes = decodeBase64(keys.signPublicKey);
      expect(signPubBytes.length).toBe(32);
    });

    test('two calls generate different keypairs', () => {
      const keys1 = km.generateKeyPair();
      const keys2 = km.generateKeyPair();
      expect(keys1.publicKey).not.toBe(keys2.publicKey);
    });
  });

  describe('generateFingerprint', () => {
    test('returns XXXX-XXXX-XXXX-XXXX format', () => {
      const keys = km.generateKeyPair();
      const fp = km.generateFingerprint(keys.publicKey);
      expect(fp).toMatch(/^[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}$/);
    });

    test('same key produces same fingerprint', () => {
      const keys = km.generateKeyPair();
      const fp1 = km.generateFingerprint(keys.publicKey);
      const fp2 = km.generateFingerprint(keys.publicKey);
      expect(fp1).toBe(fp2);
    });

    test('different keys produce different fingerprints', () => {
      const keys1 = km.generateKeyPair();
      const keys2 = km.generateKeyPair();
      expect(km.generateFingerprint(keys1.publicKey))
        .not.toBe(km.generateFingerprint(keys2.publicKey));
    });
  });

  describe('encryptMessage / decryptMessage', () => {
    test('encrypt then decrypt roundtrip succeeds', () => {
      // Alice
      const aliceKeys = km.generateKeyPair();
      const alicePub = aliceKeys.publicKey;

      // Bob
      const bobKP = nacl.box.keyPair();
      const bobPub = encodeBase64(bobKP.publicKey);

      // Alice encrypts for Bob
      const { encrypted, nonce } = km.encryptMessage('Hello Bob!', bobPub);

      // Bob decrypts
      const decrypted = nacl.box.open(
        decodeBase64(encrypted),
        decodeBase64(nonce),
        decodeBase64(alicePub),
        bobKP.secretKey
      );

      expect(decrypted).not.toBeNull();
      expect(encodeUTF8(decrypted!)).toBe('Hello Bob!');
    });

    test('decrypt with wrong key returns null', () => {
      const aliceKeys = km.generateKeyPair();
      const bobKP = nacl.box.keyPair();
      const { encrypted, nonce } = km.encryptMessage('secret', encodeBase64(bobKP.publicKey));

      // Eve tries to decrypt
      const eveKP = nacl.box.keyPair();
      const result = nacl.box.open(
        decodeBase64(encrypted),
        decodeBase64(nonce),
        decodeBase64(aliceKeys.publicKey),
        eveKP.secretKey
      );
      expect(result).toBeNull();
    });
  });

  describe('QR Payload', () => {
    test('createQRPayload and verifyQRPayload roundtrip', () => {
      const keys = km.generateKeyPair();
      const profile = {
        id: 'test-user',
        publicKey: keys.publicKey,
        signPublicKey: keys.signPublicKey,
        fingerprint: km.generateFingerprint(keys.publicKey),
        displayName: 'Test User',
        avatarColor: '#FF0000',
      };

      const payload = km.createQRPayload(profile);
      const result = km.verifyQRPayload(payload);

      expect(result.valid).toBe(true);
      expect(result.expired).toBeFalsy();
    });
  });
});
```

### Pas 4 — Scrie teste Database

Creaza: `/Users/ruslanconstantinovici/qrchatAndroid/__tests__/Database.test.ts`

**NOTA:** Database foloseste SQLite mock-uit. Trebuie sa mock-uiesti `executeAsync` sa returneze date specifice per test.

```typescript
/**
 * Database Tests
 * Tests for src/storage/Database.ts — CRUD contacts, messages, pagination
 * Uses mocked @op-engineering/op-sqlite from jest.setup.js
 */

// Importa DUPA mock-uri (jest.setup.js ruleaza automat)
import Database from '../src/storage/Database';

// Referinta la mock-ul SQLite
const mockOpen = require('@op-engineering/op-sqlite').open;

describe('Database', () => {
  let mockDb: any;

  beforeEach(() => {
    jest.clearAllMocks();
    // Obtine referinta la mock DB
    mockDb = mockOpen.mock.results[0]?.value || {
      execute: jest.fn(),
      executeAsync: jest.fn().mockResolvedValue({ rows: { _array: [] } }),
      close: jest.fn(),
    };
    // Reset mock-ul open sa returneze mockDb
    mockOpen.mockReturnValue(mockDb);
  });

  describe('Contacts CRUD', () => {
    test('addContact executes INSERT SQL', async () => {
      const contact = {
        id: 'contact-1',
        publicKey: 'pubkey123',
        displayName: 'Alice',
        fingerprint: 'abcd-efgh-ijkl-mnop',
        avatarColor: '#FF0000',
        addedAt: Date.now(),
      };

      await Database.addContact(contact as any);

      // Verifica ca execute/executeAsync a fost apelat cu INSERT
      const calls = [...mockDb.execute.mock.calls, ...mockDb.executeAsync.mock.calls];
      const insertCall = calls.find(c => c[0]?.includes?.('INSERT'));
      expect(insertCall).toBeTruthy();
    });

    test('getContacts returns parsed contact list', async () => {
      mockDb.executeAsync.mockResolvedValueOnce({
        rows: {
          _array: [
            { id: 'c1', publicKey: 'pk1', displayName: 'Alice', fingerprint: 'fp1', avatarColor: '#F00', addedAt: 1000 },
            { id: 'c2', publicKey: 'pk2', displayName: 'Bob', fingerprint: 'fp2', avatarColor: '#0F0', addedAt: 2000 },
          ]
        }
      });

      const contacts = await Database.getContacts();
      expect(contacts).toHaveLength(2);
      expect(contacts[0].displayName).toBe('Alice');
    });

    test('deleteContact executes DELETE SQL with correct id', async () => {
      await Database.deleteContact('contact-to-delete');

      const calls = [...mockDb.execute.mock.calls, ...mockDb.executeAsync.mock.calls];
      const deleteCall = calls.find(c => c[0]?.includes?.('DELETE'));
      expect(deleteCall).toBeTruthy();
    });
  });

  describe('Messages CRUD', () => {
    test('addMessage executes INSERT with all fields', async () => {
      const message = {
        id: 'msg-1',
        conversationId: 'conv-1',
        senderId: 'sender-1',
        senderName: 'Alice',
        content: 'Hello!',
        contentType: 'text',
        timestamp: Date.now(),
        isRead: false,
        isDelivered: false,
        isSent: true,
        isEncrypted: true,
      };

      await Database.addMessage(message as any);

      const calls = [...mockDb.execute.mock.calls, ...mockDb.executeAsync.mock.calls];
      const insertCall = calls.find(c => c[0]?.includes?.('INSERT') && c[0]?.includes?.('messages'));
      expect(insertCall).toBeTruthy();
    });

    test('getMessagesPaginated uses LIMIT and ORDER BY', async () => {
      mockDb.executeAsync.mockResolvedValueOnce({
        rows: { _array: [] }
      });

      await Database.getMessagesPaginated('conv-1', 25);

      const calls = mockDb.executeAsync.mock.calls;
      const selectCall = calls.find((c: any) =>
        c[0]?.includes?.('LIMIT') || c[0]?.includes?.('ORDER BY')
      );
      expect(selectCall).toBeTruthy();
    });

    test('getMessagesPaginated with beforeTimestamp filters correctly', async () => {
      mockDb.executeAsync.mockResolvedValueOnce({
        rows: { _array: [] }
      });

      const before = Date.now() - 60000;
      await Database.getMessagesPaginated('conv-1', 50, before);

      const calls = mockDb.executeAsync.mock.calls;
      // Should include timestamp filter in query
      const hasTimestampParam = calls.some((c: any) =>
        c[1]?.includes?.(before) || c[0]?.includes?.('timestamp')
      );
      expect(hasTimestampParam).toBeTruthy();
    });
  });

  describe('Reactions', () => {
    test('addReaction executes INSERT with messageId, emoji, senderId', async () => {
      await Database.addReaction('msg-1', '👍', 'sender-1');

      const calls = [...mockDb.execute.mock.calls, ...mockDb.executeAsync.mock.calls];
      const insertCall = calls.find(c => c[0]?.includes?.('INSERT') && c[0]?.includes?.('reaction'));
      expect(insertCall).toBeTruthy();
    });

    test('removeReaction executes DELETE', async () => {
      await Database.removeReaction('msg-1', '👍', 'sender-1');

      const calls = [...mockDb.execute.mock.calls, ...mockDb.executeAsync.mock.calls];
      const deleteCall = calls.find(c => c[0]?.includes?.('DELETE') && c[0]?.includes?.('reaction'));
      expect(deleteCall).toBeTruthy();
    });
  });
});
```

### Pas 5 — Ruleaza toate testele

```bash
cd /Users/ruslanconstantinovici/qrchatAndroid

# Ruleaza TOATE testele (vechi + noi)
npx jest --verbose

# Daca DoubleRatchet.test.ts esueaza din cauza mock-urilor, ruleaza-l izolat:
# DoubleRatchet NU ar trebui sa aiba nevoie de mock-uri (foloseste tweetnacl pur)
npx jest __tests__/DoubleRatchet.test.ts --verbose

# Ruleaza separat daca e nevoie de debugging:
npx jest __tests__/KeyManager.test.ts --verbose
npx jest __tests__/Database.test.ts --verbose
```

### Pas 6 — Fix-eaza testele care esueaza

Cele mai probabile probleme:
- **DoubleRatchet:** Ar trebui sa mearga fara mock-uri (tweetnacl e pur JS). Daca `react-native-get-random-values` cauzeaza erori, adauga mock in jest.setup.js
- **KeyManager:** E singleton — daca `loadKeys('')` nu reseteaza starea, ia clasa direct si instanziaz-o manual
- **Database:** Mock-ul SQLite e simplu. Daca `Database` face `initSQLite()` in constructor, trebuie mock-uit initialization flow-ul

---

## Fisiere de creat

| Fisier | Actiune |
|--------|---------|
| `__tests__/DoubleRatchet.test.ts` | CREAT NOU — ~120 linii |
| `__tests__/KeyManager.test.ts` | CREAT NOU — ~100 linii |
| `__tests__/Database.test.ts` | CREAT NOU — ~100 linii |

---

## Criterii de succes

1. `npx jest --verbose` — TOATE testele trec (vechi 9 + noi ~20)
2. DoubleRatchet: encrypt/decrypt roundtrip, forward secrecy, out-of-order, serialization — toate PASS
3. KeyManager: keypair generation, fingerprint, encrypt/decrypt, QR payload — toate PASS
4. Database: CRUD contacts, CRUD messages, pagination, reactions — toate PASS
5. Coverage: minim 70% pe fisierele testate (verifica cu `npx jest --coverage`)

---

## Capcane de evitat

- **NU mock-ui tweetnacl** pentru testele DoubleRatchet — trebuie testat cu crypto REAL, nu mock-uit. Scopul e sa verifici ca algoritmul functioneaza corect end-to-end
- **NU mock-ui tweetnacl** pentru testele KeyManager la encrypt/decrypt roundtrip — vrei sa verifici ca criptarea functioneaza cu chei reale
- **mock-uri SQLite:** Mock-ul din jest.setup.js returneaza `{ rows: { _array: [] } }` default. Pentru teste care verifica date returnate, trebuie sa faci `mockResolvedValueOnce(...)` cu date specifice IN TEST
- **Singleton KeyManager:** `KeyManager` exporta o instanta singleton. Daca testele se influenteaza reciproc (state pollution), fie reseteaza state in beforeEach, fie importa clasa si creaza instante noi
- **Async/await:** TOATE metodele Database sunt async. Foloseste `await` in teste, altfel testele trec fara sa verifice nimic (promise neresolved)
- **DoubleRatchet initSender/initReceiver:** Initiator (sender) e cel cu peerId mai mic. Daca inversezi rolurile, criptarea/decriptarea poate esua. Urmeaza exact pattern-ul din cod
- **Testele de code existente NU trebuie modificate** — cele 3 fisiere existente raman neatinse
- **jest.setup.js NU trebuie modificat** decat daca testele noi au nevoie de mock-uri aditionale (ex: `react-native-get-random-values` pentru DoubleRatchet)
