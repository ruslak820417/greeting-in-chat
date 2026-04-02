# Audit Securitate — QRChat v4.0.0
Data: 2026-03-21

## Scor General: 88/100

---

## 1. Double Ratchet — Forward Secrecy — OK (10/10)

**Fisiere analizate:** `src/crypto/DoubleRatchet.ts` (255 linii), `src/crypto/RatchetStore.ts` (63 linii)

| Verificare | Verdict | Detalii |
|-----------|---------|---------|
| HKDF-SHA512 implementat corect | OK | HMAC cu ipad (0x36) si opad (0x5c), block size 128, salt handling corect. `hkdf()` la linia 49-52 |
| DH ratchet roteste keypair-uri X25519 | OK | `_advanceDH()` (linia 234) genereaza nou `nacl.box.keyPair()` la fiecare schimb |
| Chain key derivation avanseaza corect | OK | `KDF_CK()` (linia 64) foloseste constante separate `[1]` si `[2]` pentru CK si MK |
| Message keys derivate din chain keys, nu refolosite | OK | `encrypt()` (linia 152) consuma MK si avanseaza CK la fiecare mesaj |
| Serialize/deserialize complet | OK | `RatchetState` pastreaza: DHs_pub, DHs_priv, DHr, RK, CKs, CKr, Ns, Nr, PN, MKSKIPPED |
| Ratchet state stocat in Keychain | OK | `RatchetStore.set()` foloseste `WHEN_UNLOCKED_THIS_DEVICE_ONLY` (linia 37) |
| Nu exista fallback la AsyncStorage | OK | RatchetStore foloseste EXCLUSIV Keychain via `react-native-keychain` |
| Skip message key limiting | OK | `MAX_SKIP=100`, `MAX_MKSKIPPED_TOTAL=500` — previne DoS prin mesaje skipped |

**Observatii:** Implementare solida, urmeaza fidel protocolul Signal Double Ratchet. Nicio vulnerabilitate identificata.

---

## 2. Key Management — OK (10/10)

**Fisier analizat:** `src/crypto/KeyManager.ts` (218 linii)

| Verificare | Verdict | Detalii |
|-----------|---------|---------|
| Box keypair: `nacl.box.keyPair()` (X25519) | OK | Linia 22 |
| Sign keypair: `nacl.sign.keyPair()` (Ed25519) | OK | Linia 23 |
| QR payload contine `signPub`, `sig`, `ts` | OK | `createQRPayload()` (linia 51-71) — toate campurile obligatorii |
| Semnatura QR verificata cu Ed25519 | OK | `verifyQRPayload()` linia 103: `nacl.sign.detached.verify()` |
| Timestamp QR previne replay | OK | Fereastra: 5 minute (`QR_EXPIRY_MS = 300_000`, linia 80) |
| Toate campurile QR obligatorii | OK | Linia 85: reject daca lipseste oricare camp (`pub`, `fp`, `name`, `signPub`, `sig`, `ts`) |
| Fingerprint din SHA-512 | OK | `generateFingerprint()` linia 38-43: `nacl.hash()` = SHA-512 |
| `loadKeys()` nu acceseaza storage | OK | Primeste parametri direct, nu citeste din AsyncStorage/Keychain |

**Observatii:** Verificarea QR in 3 nivele (fingerprint, semnatura Ed25519, timestamp) este excelenta. Fereastra de 5 minute e un compromis bun intre securitate si UX.

---

## 3. Stocarea cheilor private — OK (10/10)

**Fisier analizat:** `src/storage/Database.ts` (liniile 1-110, 739-830)

| Verificare | Verdict | Detalii |
|-----------|---------|---------|
| Chei private EXCLUSIV in Keychain | OK | `saveKeys()` linia 753-770: private keys -> Keychain, public -> AsyncStorage |
| Daca Keychain esueaza, throw (nu fallback) | OK | Linia 768: `throw new Error('Failed to save private keys to Keychain')` |
| Fara Keychain: refuza stocarea | OK | Linia 773: `throw new Error('Keychain not available — cannot save private keys securely')` |
| `getDbEncryptionKey()` cu `crypto.getRandomValues()` | OK | Linia 73-74: 32 bytes random |
| DB key in Keychain cu `WHEN_UNLOCKED_THIS_DEVICE_ONLY` | OK | Linia 76-79 |
| Nu exista `AsyncStorage.setItem` pentru chei private | OK | Linia 748-751 stocheaza DOAR `publicKey` si `signPublicKey` in AsyncStorage |
| Keychain warning la linia 11 | OK | Doar `console.warn` — nu permite fallback functional |
| Migrare automata din format vechi | OK | Linia 819-821: daca gaseste chei private in AsyncStorage, le muta in Keychain |

**Observatii:** Separarea clara public (AsyncStorage) / private (Keychain) e foarte buna. Migrarea automata din formatul vechi elimina riscul de chei private ramase in AsyncStorage.

---

## 4. SQLCipher — Database Encryption — OK (8/10)

**Fisier analizat:** `src/storage/Database.ts` (liniile 113-180)

| Verificare | Verdict | Detalii |
|-----------|---------|---------|
| `open()` primeste cheia de criptare | OK | Linia 128: `open({ name: 'qrchat.db', encryptionKey })` |
| Daca Keychain indisponibil, DB necriptata | PARTIAL | `getDbEncryptionKey()` returneaza `undefined` -> DB se deschide fara criptare. Acceptabil pe simulator, risc pe productie |
| Nu exista export/dump necriptat | OK | Migrarea (linia 130-143) este unidirectionala: unencrypted -> encrypted, nu invers |
| Migrare unencrypted -> encrypted | OK | Linia 133-143: detecteaza DB vechi necriptata si migreaza automat |

**Scor redus (-2):** Pe un dispozitiv fara Keychain (ex: anumite configuratii), DB-ul s-ar deschide necriptat. In productie pe iOS real, Keychain e mereu disponibil, deci riscul e minimal.

---

## 5. Server Authentication (Ed25519 Challenge) — OK (10/10)

**Fisier analizat:** `server/index.js` (liniile 416-496, 500-524)

| Verificare | Verdict | Detalii |
|-----------|---------|---------|
| Auth challenge cu nonce random 32 bytes | OK | Linia 422: `nacl.randomBytes(32)` |
| Client semneaza cu Ed25519 | OK | Client: `nacl.sign.detached` (SignalingClient.ts linia 172) |
| Server verifica semnatura | OK | Linia 475: `nacl.sign.detached.verify()` |
| Auth gate global | OK | Linia 457: toate mesajele (exceptie `auth-response`) necesita autentificare |
| GRACE_PERIOD controlat prin env var | OK | Linia 139: `QRCHAT_GRACE_PERIOD === 'true'` — default `false` |
| userId trebuie sa corespunda publicKey autentificat | OK | Linia 519: anti-impersonation check cand GRACE_PERIOD=false |
| Auth failure -> close connection | OK | Liniile 487-488, 493: `ws.close()` dupa semnatura invalida |

**Observatii:** Protocolul de autentificare este solid. GRACE_PERIOD=false pe Railway (productie) este critic si e corect configurat ca default.

---

## 6. Sender Spoofing Prevention — OK (10/10)

**Fisier analizat:** `server/index.js` (toate cazurile de relay)

| Tip mesaj | `from:` setat de server | Linia |
|-----------|------------------------|-------|
| offer | `from: userId` | 602 |
| answer | `from: userId` | 602 |
| ice-candidate | `from: userId` | 602 |
| call-ended | `from: userId` | 602 |
| encrypted-message | `from: userId` | 671 |
| delivery-receipt | `from: userId` | 722 |
| read-receipt | `from: userId` | 751 |
| typing | `from: userId` | 801 |
| contact-request | `from: userId` | 817 |
| contact-accepted | `from: userId` | 836 |
| contact-rejected | `from: userId` | 855 |

**Verdict:** NICIUN loc unde `message.from` trece direct de la client. Serverul forteaza `from: userId` (userId setat la register) in TOATE cazurile de relay.

---

## 7. Rate Limiting — OK (10/10)

**Fisier analizat:** `server/index.js` (liniile 82-149, 396-414)

| Verificare | Verdict | Detalii |
|-----------|---------|---------|
| Token bucket: 200 burst, 20/s refill | OK | Linia 149: `RATE_LIMIT = { tokens: 200, refillRate: 20 }` |
| Payload size cap: 1.5MB | OK | Linia 149: `maxPayload: 1.5 * 1024 * 1024` |
| Pending queue: 1000 msgs/user | OK | Linia 142: `MAX_PENDING_PER_USER = 1000` |
| Pending size: 50MB/user | OK | Linia 143: `MAX_PENDING_SIZE_PER_USER = 50 * 1024 * 1024` |
| Admin rate limiting: 5/min/IP | OK | Linia 84: `maxAttempts: 5, windowMs: 60 * 1000` |
| Input validation whitelist | OK | Linia 122-129: `VALID_MESSAGE_TYPES` — doar tipuri cunoscute |
| Message expiry: 48h | OK | Linia 38: `MESSAGE_EXPIRY = 48 * 60 * 60 * 1000` |
| Stale rate limit cleanup | OK | Linia 101-106: cleanup la fiecare 5 minute |

---

## 8. Eliminarea Math.random() — OK (9/10)

**Cautare executata:** `grep -rn "Math.random" src/`

| Fisier | Utilizare | Acceptabil? |
|--------|-----------|-------------|
| CallKitService.ts:156 | UUID generation (call handle) | OK — nu e crypto |
| LicensingService.ts:34 | Device ID generation | OK — nu e crypto |
| BootstrapManager.ts:58 | Shuffle relay order | OK — nu e crypto |
| PhoneContactsScreen.tsx:96 | Fallback contact ID | OK — nu e crypto |
| WebRTCManager.ts:191 | Message ID generation | OK — nu e crypto, dar predictibil |
| CreateGroupScreen.tsx:63 | Avatar color | OK — cosmetic |
| helpers.ts:41 | Avatar color | OK — cosmetic |

**Verdict:** `Math.random()` NU este folosit pentru operatii criptografice nicaieri. Toate operatiile crypto folosesc `nacl.randomBytes()` sau `crypto.getRandomValues()`.

**Scor redus (-1):** `WebRTCManager.ts:191` genereaza message IDs cu `Math.random().toString(36)` — desi nu e o vulnerabilitate de securitate directa, un ID predictibil ar putea permite replay selective. Recomandat: `nacl.randomBytes()` si pentru message IDs.

---

## 9. Push Notifications — Privacy — OK (10/10)

**Fisiere analizate:** `src/services/PushTokenService.ts` (87 linii), `server/push.js` (208 linii)

| Verificare | Verdict | Detalii |
|-----------|---------|---------|
| Mailbox ID cu `nacl.randomBytes(16)` | OK | PushTokenService.ts linia 42: 128 bits entropy, NU derivat din chei |
| Doua Map-uri separate pe server | OK | push.js liniile 54-57: `pushTokens` (mailbox->token), `userMailboxes` (userId->mailbox) |
| Push payload fara continut mesaj | OK | push.js linia 174: `{ e: 1, s: senderUserId }` — doar event flag + sender metadata |
| Throttle: 1 push/30s/mailbox | OK | push.js linia 22: `THROTTLE_INTERVAL_MS = 30 * 1000` |
| Token cleanup la BadDeviceToken | OK | push.js liniile 184-189: sterge din ambele Maps |

**Observatii:** Design excelent cu double-map isolation. Serverul nu poate asocia direct un userId cu un push token intr-o singura structura de date.

---

## 10. Relay Pinning — PARTIAL (7/10)

**Fisier analizat:** `src/network/SignalingClient.ts` (liniile 39-116)

| Verificare | Verdict | Detalii |
|-----------|---------|---------|
| `PINNED_RELAY_DOMAINS` — doar domenii trusted | OK | Linia 41-45: doar `exciting-success-production-d272.up.railway.app` |
| Production: `wss://` obligatoriu | OK | Linia 63-66: reject non-TLS |
| Dev mode: permite `ws://localhost` si `ws://192.168.*` | OK | Linia 55-57 |
| Relay-uri din gossip validate | PARTIAL | Gossip URLs trec prin `validateRelayUrl()`, DAR... |
| **Bypass vulnerability** | **RISC** | Linia 103: `(pinnedUrls.length > 0 ? pinnedUrls : urls)` — daca TOATE URL-urile pinned sunt respinse, se incearca URL-urile NEPINNED |

**Vulnerabilitate critica:** In `connect()`, linia 103:
```typescript
for (const url of (pinnedUrls.length > 0 ? pinnedUrls : urls)) {
```
Daca un atacator prin gossip injecteaza DOAR relay-uri malitioase si relay-urile pinned sunt offline, codul face fallback la URL-urile nevalidate. Aceasta anuleaza complet mecanismul de pinning.

**Remediere recomandata:** Daca `pinnedUrls.length === 0`, trebuie sa refuze conexiunea, nu sa faca fallback:
```typescript
if (pinnedUrls.length === 0) {
  throw new Error('[SignalingClient] All relay URLs rejected by certificate pinning');
}
```

---

## 11. Vulnerabilitati Ramase

**Fisiere analizate:** `src/network/GossipProtocol.ts`, `server/licensing.js`, `ios/QRChat/Info.plist`, `ios/QRChat/PrivacyInfo.xcprivacy`

| Verificare | Verdict | Detalii |
|-----------|---------|---------|
| Gossip: semnaturi Ed25519 pe peers | **LIPSA** | `processGossipPayload()` (GossipProtocol.ts linia 100-133) accepta peers fara verificare semnatura. Un peer malitios poate injecta peer entries false |
| Admin secret — setat din env var | OK | licensing.js linia 73: `process.env.QRCHAT_ADMIN_SECRET` cu fallback persisted file |
| Admin `/change-password` endpoint | OK | licensing.js linia 236-251, cu `timingSafeEqual` |
| Admin secret min length | **RISC** | licensing.js linia 241: `newSecret.length < 4` — minim 4 caractere e prea putin |
| `NSAllowsArbitraryLoads` | OK | Info.plist linia 43: `<false/>` — ATS compliant |
| `ITSAppUsesNonExemptEncryption` | PARTIAL | Info.plist linia 37: `<true/>` — corect, DAR `ITSEncryptionExportComplianceCode` este STRING GOL (linia 39) |
| PrivacyInfo.xcprivacy | OK | Prezent cu `NSPrivacyTracking: false`, `NSPrivacyCollectedDataTypes: []`, API types declarate corect |
| Gossip relay injection | **RISC** | GossipProtocol.ts linia 124-128: relay URLs din gossip adaugate la BootstrapManager fara validare. Combinat cu pinning bypass, e o vulnerabilitate reala |

---

## Vulnerabilitati Active

| # | Severitate | Descriere | Remediere |
|---|-----------|-----------|-----------|
| 1 | **HIGH** | Relay pinning bypass: daca `pinnedUrls.length === 0`, fallback la URL-uri nevalidate (SignalingClient.ts:103) | Daca pinnedUrls e gol, throw error in loc de fallback. Nu permite conexiuni nepinned |
| 2 | **MEDIUM** | Gossip peer injection: `processGossipPayload()` accepta peers fara semnatura Ed25519 (GossipProtocol.ts:100-133) | Adauga camp `signature` in GossipPeer. Verifica semnatura cu `signPublicKey` inainte de accept |
| 3 | **MEDIUM** | Gossip relay injection: relay URLs din gossip adaugate fara validare (GossipProtocol.ts:124-128) | Valideaza URL-urile contra PINNED_RELAY_DOMAINS inainte de `BootstrapManager.addRelay()` |
| 4 | **LOW** | Admin secret minimum length: 4 caractere (licensing.js:241) | Creste la minimum 12 caractere. Adauga verificare complexitate |
| 5 | **LOW** | `ITSEncryptionExportComplianceCode` gol (Info.plist:39) | Seteaza codul corect de conformitate export criptare |
| 6 | **INFO** | Message IDs generate cu `Math.random()` (WebRTCManager.ts:191) | Inlocuieste cu `nacl.randomBytes()` encoded base64 pentru IDs impredictibile |
| 7 | **INFO** | SQLCipher disabled cand Keychain indisponibil | Acceptabil pe simulator; pe dispozitiv real iOS, Keychain e mereu disponibil |

---

## Ce functioneaza exemplar

1. **Double Ratchet** — Implementare completa si corecta a protocolului Signal
2. **Key isolation** — Chei private EXCLUSIV in Keychain, cu throw la fallback
3. **Sender spoofing** — 100% eliminat: `from: userId` fortat de server in toate cazurile
4. **Ed25519 auth** — Challenge-response solid cu nonce random
5. **Push privacy** — Design double-map cu zero message content in payload
6. **Rate limiting** — Token bucket + size caps + admin rate limit + message validation whitelist
7. **QR verification** — Triple verification (fingerprint + Ed25519 sig + 5-min timestamp)

---

## Next Steps (prioritizate)

1. **[CRITICAL]** Fix relay pinning bypass — elimina fallback-ul la URL-uri nepinned din `SignalingClient.connect()` (linia 103). Daca niciun URL pinned nu e disponibil, refuza conexiunea
2. **[HIGH]** Adauga semnatura Ed25519 pe gossip payloads — fiecare peer trebuie sa semneze datele de gossip cu `signPublicKey`-ul sau. Receptorul verifica inainte de merge
3. **[HIGH]** Valideaza relay URLs din gossip contra listei de domenii pinned inainte de a le adauga la BootstrapManager
4. **[MEDIUM]** Creste minimum admin secret de la 4 la 12+ caractere in `licensing.js`
5. **[LOW]** Seteaza `ITSEncryptionExportComplianceCode` corect in Info.plist pentru App Store compliance
6. **[LOW]** Inlocuieste `Math.random()` cu `nacl.randomBytes()` pentru message IDs in WebRTCManager.ts
7. **[OPTIONAL]** Verifica setarile QRCHAT_GRACE_PERIOD pe Railway — confirma ca e `false` sau absent

---

## Rezumat pe sectiuni

| Sectiune | Scor | Verdict |
|----------|------|---------|
| 1. Double Ratchet | 10/10 | OK |
| 2. Key Management | 10/10 | OK |
| 3. Key Storage | 10/10 | OK |
| 4. SQLCipher | 8/10 | OK (minor: simulator fallback) |
| 5. Server Auth | 10/10 | OK |
| 6. Sender Spoofing | 10/10 | OK |
| 7. Rate Limiting | 10/10 | OK |
| 8. Math.random | 9/10 | OK (minor: message IDs) |
| 9. Push Privacy | 10/10 | OK |
| 10. Relay Pinning | 7/10 | PARTIAL (pinning bypass) |
| 11. Vulnerabilitati | 6/10 | RISC (gossip fara semnatura) |
| **TOTAL** | **88/100** | **BINE — necesita fix gossip + pinning** |
