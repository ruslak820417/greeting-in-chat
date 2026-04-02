# Prompt: Security Audit Complet — security-engineer

**Rol:** Esti security-engineer pentru QRChat, un messenger criptat end-to-end React Native.
**Proiect:** `/Users/ruslanconstantinovici/QRChat`
**Versiune:** 4.0.0 (build 16)
**Server LIVE:** https://exciting-success-production-d272.up.railway.app

---

## SARCINA

Executa un audit complet de securitate al aplicatiei QRChat. Evalueaza TOATA starea criptografica, autentificarea, stocarea securizata si vulnerabilitatile ramase. Scrie un raport detaliat cu ce e bine, ce e partial, si ce lipseste.

---

## VERIFICARI (executa pe rand)

### 1. Double Ratchet — Forward Secrecy

Citeste si analizeaza:
- `src/crypto/DoubleRatchet.ts` (9071 linii → 280 linii — verifica implementarea)
- `src/crypto/RatchetStore.ts` (63 linii — Keychain persistence)

Verifica:
- [ ] HKDF-SHA512 implementat corect (HMAC ipad/opad, salt handling)
- [ ] DH ratchet step roteste keypair-uri X25519 la fiecare schimb
- [ ] Chain key derivation (KDF chain) avanseaza corect la fiecare mesaj
- [ ] Message keys sunt derivate din chain keys si nu sunt refolosite
- [ ] Serialize/deserialize pastreaza starea complet (dhPair, rootKey, sendChain, recvChain, counters)
- [ ] Ratchet state este stocat in Keychain cu `WHEN_UNLOCKED_THIS_DEVICE_ONLY`
- [ ] Nu exista fallback la AsyncStorage pentru starea ratchet

### 2. Key Management

Citeste si analizeaza:
- `src/crypto/KeyManager.ts` (6480 linii → ~200 linii)

Verifica:
- [ ] Keypair-uri generate cu `nacl.box.keyPair()` (X25519) si `nacl.sign.keyPair()` (Ed25519)
- [ ] QR payload contine `signPub`, `sig`, `ts` obligatoriu
- [ ] Semnatura QR este verificata cu Ed25519 la scanare
- [ ] Timestamp-ul QR previne replay attacks (cat de mare e fereastra?)
- [ ] `loadKeys()` incarca DOAR din Keychain, nu din AsyncStorage
- [ ] Fingerprint derivat din hash SHA-512 al cheii publice

### 3. Stocarea cheilor private

Citeste si analizeaza:
- `src/storage/Database.ts` (primele 150 linii — initializare, Keychain, SQLCipher)

Verifica:
- [ ] Cheile private sunt stocate EXCLUSIV in Keychain (nu AsyncStorage)
- [ ] `getDbEncryptionKey()` genereaza cheia SQLCipher din `crypto.getRandomValues()`
- [ ] Cheia DB este stocata in Keychain cu `WHEN_UNLOCKED_THIS_DEVICE_ONLY`
- [ ] Nu exista `AsyncStorage.setItem` pentru chei private nicaieri in codebase
- [ ] `Keychain` fallback warning la linia ~11 — este doar warning, nu fallback functional

### 4. SQLCipher — Database encryption

In `Database.ts`, verifica:
- [ ] `open()` primeste parametrul de criptare (cheia din Keychain)
- [ ] Daca Keychain nu e disponibil, DB se deschide necriptat? (acceptabil pe simulator, periculos in productie)
- [ ] Nu exista export/dump de baza de date fara criptare

### 5. Server Authentication (Ed25519 challenge)

Citeste: `server/index.js` (liniile 416-496 — auth challenge/response)

Verifica:
- [ ] Serverul trimite `auth-challenge` cu nonce random 32 bytes
- [ ] Clientul semneaza cu Ed25519 (`nacl.sign.detached`)
- [ ] Serverul verifica semnatura cu `nacl.sign.detached.verify`
- [ ] Auth gate: toate mesajele (exceptie `auth-response`) necesita autentificare
- [ ] GRACE_PERIOD controlat prin env var `QRCHAT_GRACE_PERIOD` (default false)
- [ ] `GRACE_PERIOD=false` pe Railway (productie)

### 6. Sender Spoofing Prevention

In `server/index.js`, verifica toate locurile unde se face relay:
- [ ] `from: userId` este fortat de server (nu din mesajul clientului)
- [ ] Tipurile de mesaje cu relay: offer, answer, ice-candidate, call-ended, encrypted-message, delivery-receipt, read-receipt, typing, contact-request, contact-accepted, contact-rejected, ping-user
- [ ] Niciun loc unde `from: message.from` trece direct de la client

### 7. Rate Limiting

In `server/index.js`, verifica:
- [ ] Token bucket: 200 burst, 20/s refill
- [ ] Payload size cap: 1.5MB per mesaj WS
- [ ] Pending queue: 1000 mesaje, 50MB per user
- [ ] Admin rate limiting: 5 incercari / minut pe IP
- [ ] Input validation: whitelist de tipuri de mesaje (`VALID_MESSAGE_TYPES`)

### 8. Eliminarea Math.random()

Cauta in TOATE fisierele `.ts` si `.tsx`:
```bash
grep -rn "Math.random" /Users/ruslanconstantinovici/QRChat/src/
```
- [ ] `Math.random()` NU este folosit pentru operatii criptografice
- [ ] Unde apare (BootstrapManager shuffle, etc.) — este acceptabil? (shuffle order, nu crypto)

### 9. Push Notifications — Privacy

Citeste:
- `src/services/PushTokenService.ts` (87 linii)
- `server/push.js` (primele 80 linii)

Verifica:
- [ ] Mailbox ID generat cu `nacl.randomBytes(16)` (nu derivat din chei)
- [ ] Doua Map-uri separate pe server: `pushTokens` (mailbox->token) si `userMailboxes` (userId->mailbox)
- [ ] Push payload NU contine continut de mesaj
- [ ] Throttle: max 1 push per 30s per mailbox

### 10. Relay Pinning

Citeste: `src/network/SignalingClient.ts` (liniile 39-76)

Verifica:
- [ ] `PINNED_RELAY_DOMAINS` — doar domenii de incredere
- [ ] Production: necesita `wss://` (TLS obligatoriu)
- [ ] Dev mode: permite `ws://localhost` si `ws://192.168.*`
- [ ] Relay-uri din gossip sunt validate inainte de conectare

### 11. Vulnerabilitati ramase

Evalueaza si documenteaza:
- [ ] Gossip relay validation — semnaturile Ed25519 sunt verificate? (`src/network/GossipProtocol.ts`)
- [ ] Admin secret — cum e setat pe Railway? Exista endpoint `/admin/change-password`?
- [ ] `server/licensing.js` — codul de admin secret se incarca din env var?
- [ ] `NSAllowsArbitraryLoads` in Info.plist — este `false`? Confirma ATS compliance
- [ ] `ITSAppUsesNonExemptEncryption = YES` + ITSEncryptionExportComplianceCode setat

---

## FISIERE DE CITIT (lista completa)

| Fisier | Ce verifici |
|--------|------------|
| `src/crypto/DoubleRatchet.ts` | Implementare Double Ratchet |
| `src/crypto/KeyManager.ts` | Generare/incarcare chei |
| `src/crypto/RatchetStore.ts` | Persistenta Keychain |
| `src/storage/Database.ts` | SQLCipher, Keychain storage |
| `server/index.js` | Auth, rate limiting, sender spoofing |
| `server/push.js` | Push privacy, mailbox isolation |
| `server/licensing.js` | Admin secret management |
| `src/services/PushTokenService.ts` | Mailbox ID generation |
| `src/network/SignalingClient.ts` | TLS pinning, relay validation |
| `src/network/GossipProtocol.ts` | Peer gossip (semnaturi?) |
| `ios/QRChat/Info.plist` | ATS, encryption compliance |
| `ios/QRChat/PrivacyInfo.xcprivacy` | Apple Privacy Manifest |

---

## COMANDA DE VERIFICARE

Ai terminat cand:
1. Fiecare punct de mai sus are un verdict: OK / PARTIAL / LIPSA / RISC
2. Ai un scor general (ex: 85/100)
3. Ai o lista de "Next Steps" prioritizata

---

## UNDE SCRII RAPORTUL

Scrie rezultatul in:
```
/Users/ruslanconstantinovici/Projects/Agent Teams/agent-runtime/outputs/audit-security.md
```

Format:
```markdown
# Audit Securitate — QRChat v4.0.0
Data: [data curenta]

## Scor General: XX/100

## 1. Double Ratchet — [OK/PARTIAL/RISC]
[detalii]

## 2. Key Management — [OK/PARTIAL/RISC]
[detalii]

... (pentru fiecare sectiune)

## Vulnerabilitati Active
| # | Severitate | Descriere | Remediere |
|---|-----------|-----------|-----------|

## Next Steps (prioritizate)
1. ...
```
