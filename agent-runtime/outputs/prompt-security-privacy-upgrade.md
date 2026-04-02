# PROMPT: QRChat v5.0 — Security & Privacy Hardening

## PRE-CONDIȚIE OBLIGATORIE

**Verifică ÎNAINTE de orice modificare:**
1. Ești pe branch-ul `feature/security-privacy-upgrade` (NU pe main)
2. `git log --oneline -1` arată `f772264 Build 101` ca bază
3. Dacă nu — STOP. Execută mai întâi prompt-ul de revert.

---

## OBIECTIV

Implementează 12 îmbunătățiri de securitate, privacy și UX în QRChat. Toate sunt dezvoltări proprii bazate pe standarde criptografice (RFC 5869 HKDF, NaCl spec, WebRTC Encoded Transforms API) și best practices din industria messengerelor criptate.

Lucrul se face în **4 faze secvențiale**, cu agenți lucrând **în paralel** în cadrul fiecărei faze. Fiecare agent modifică DOAR fișierele din domeniul său. La final, se face verificare totală.

**Proiect:** `/Users/ruslanconstantinovici/QRChat`
**Branch:** `feature/security-privacy-upgrade`
**Baza:** Build 101 (commit `f772264`)
**Fallback:** `git checkout main` — Build 101 stabil
**Tech stack:** React Native 0.84, TypeScript, Node.js server, TweetNaCl, WebRTC, SQLite

---

## REGULI OBLIGATORII PENTRU TOȚI AGENȚII

1. **Citește fișierul ÎNAINTE de a-l modifica** — nu presupune structura
2. **Updatează `agent-runtime/state/status.md`** când începi/finalizezi o sarcină
3. **Dacă depinzi de alt agent** — scrie în `agent-runtime/messages/{de-la}-to-{către}.md` și marchează BLOCKED
4. **Nu face push la git** fără aprobarea lead-ului
5. **Nu modifica fișiere din domeniul altui agent** — dacă ai nevoie, trimite mesaj
6. **Incrementează build number** la finalul fazei, nu după fiecare modificare
7. **Testează compilarea** după fiecare modificare (`npx tsc --noEmit`)
8. **Nu adaugă dependențe npm** fără aprobarea lead-ului
9. **Scrie cod TypeScript strict** — fără `any`, fără `@ts-ignore`
10. **Comentarii în engleză**, referă standarde tehnice (RFC, spec, API), nu produse terțe
11. **Commit messages** descriptive și generice: "Add message padding for traffic analysis prevention"
12. **Nu copia cod** din alte proiecte — implementează de la zero pe baza specificațiilor tehnice
13. **Toate modificările pe branch** `feature/security-privacy-upgrade`, NICIODATĂ pe main

---

## FAZA 1 — SECURITATE CORE (security-engineer + architect — PARALEL)

### Agent: security-engineer

**Sarcini:**

#### 1.1 Message Padding — blocuri fixe de 16KB
**Fisier:** `src/crypto/DoubleRatchet.ts` (260 linii)
**Referință:** Constant-length padding — standard practice în protocoale criptografice pentru prevenirea traffic analysis (vezi: TLS record padding RFC 8446 §5.4)
- Adaugă funcția `padMessage(plaintext: Uint8Array): Uint8Array` care:
  - Prepend 4 bytes cu lungimea originală (uint32 big-endian)
  - Pad cu random bytes până la 16384 bytes total
  - Dacă mesajul > 16380 bytes, pad la următorul multiplu de 16384
- Adaugă funcția `unpadMessage(padded: Uint8Array): Uint8Array` care:
  - Citește primii 4 bytes ca lungime
  - Returnează doar payload-ul original
- Integrează `padMessage` în `encrypt()` ÎNAINTE de `nacl.secretbox`
- Integrează `unpadMessage` în `decrypt()` DUPĂ `nacl.secretbox.open`
- **Test:** mesaj de 5 bytes și mesaj de 1000 bytes produc același output size (16384)

#### 1.2 Message Integrity Chain (prev_msg_hash)
**Fisier:** `src/crypto/DoubleRatchet.ts`
**Referință:** Hash chain integrity — standard în protocoale de comunicare sigură (vezi: Certificate Transparency RFC 6962, Git commit chain)
- Adaugă câmp `prevMsgHash: string` în starea ratchet
- La fiecare mesaj trimis: `currentHash = sha256(prevMsgHash + ciphertext)`
- Include `prevMsgHash` în header-ul mesajului (primele 32 bytes înainte de ciphertext)
- La recepție: verifică că `prevMsgHash` din header == ultimul hash primit de la acel contact
- Dacă nu se potrivește: log warning dar NU refuză mesajul (backward compatibility)
- Folosește `tweetnacl` hash sau importă `js-sha256` (fără dependențe native noi)

#### 1.3 Encrypted Message Headers
**Fisier:** `src/crypto/DoubleRatchet.ts`
**Referință:** Header encryption — Double Ratchet spec §3.2, protejează ratchet state metadata
- Header-ul ratchet (DH public key, message number, previous chain length) să fie criptat cu o cheie derivată separat din root key
- Derivă `headerKey` cu HKDF din root key: `headerKey = hkdf(rootKey, "header")` (RFC 5869)
- Criptează header-ul cu `nacl.secretbox(header, nonce, headerKey)` SEPARAT de body
- Formatul mesajului devine: `[encryptedHeader | encryptedBody]`
- Actualizează `decrypt()` să decripteze header-ul întâi, apoi body-ul

**Rezultat:** Scrie raport în `agent-runtime/outputs/security-phase1-report.md`

---

### Agent: architect

**Sarcini:**

#### 1.4 Definire Protocol Versioning
**Fisier NOU:** `src/utils/protocol.ts`
- Definește `PROTOCOL_VERSION = 2` (v1 = format curent fără padding/hash)
- Definește interfața `MessageEnvelope`:
```typescript
interface MessageEnvelope {
  version: number;           // 1 sau 2
  encryptedHeader: Uint8Array; // doar v2
  encryptedBody: Uint8Array;
  prevMsgHash?: string;      // doar v2
  padding?: boolean;         // doar v2
}
```
- Funcție `serializeEnvelope(env: MessageEnvelope): Uint8Array`
- Funcție `deserializeEnvelope(data: Uint8Array): MessageEnvelope`
- Backward compatible: dacă `version == 1`, parsează ca format vechi
- Exportă tot din `src/utils/protocol.ts`

#### 1.5 Refactorizare MessagingService pentru noul protocol
**Fisier:** `src/services/MessagingService.ts` (2509 linii)
- În metoda de trimitere: wrapează mesajul în `MessageEnvelope` v2
- În metoda de recepție: detectează versiunea și parsează corespunzător
- Dacă receptorul trimite v1 (peer vechi): acceptă fără padding/hash
- Dacă trimitem către peer cu versiune necunoscută: trimitem v1 (safe fallback)
- Adaugă `peerProtocolVersion: Map<string, number>` — se populează la primul mesaj primit
- La handshake/key exchange: include `protocolVersion` în payload

#### 1.6 Server-Side Message Re-encryption
**Fisier:** `server/index.js` (1419 linii)
**Referință:** Transport-layer re-encryption — standard în relay architectures pentru prevenirea ciphertext correlation (NaCl crypto_box spec)
- La înregistrarea clientului: server + client fac DH exchange (Curve25519)
  - Server generează `serverKeyPair = nacl.box.keyPair()`
  - Trimite `serverKeyPair.publicKey` clientului la connect
  - Calculează `sharedSecret = nacl.box.before(clientPublicKey, serverSecretKey)`
- La relay mesaj: server re-criptează cu `sharedSecret` al recipientului
  - Input: `nacl.box.open(ciphertext, nonce, senderShared)` → plaintext E2E criptat
  - Output: `nacl.box(e2ePayload, newNonce, recipientShared)` → alt ciphertext
  - Rezultat: ciphertext care intră pe server != ciphertext care iese
- **NU decriptează E2E** — doar schimbă layer-ul de transport
- Clientul: `src/network/SignalingClient.ts` — adaugă DH exchange la connect

**Rezultat:** Scrie raport în `agent-runtime/outputs/architect-phase1-report.md`

---

### CHECKPOINT FAZA 1
**Înainte de a trece la Faza 2:**
- [ ] `npx tsc --noEmit` — zero erori
- [ ] Mesajele vechi (v1) se pot decripta în continuare
- [ ] Mesaje noi au padding 16KB
- [ ] prevMsgHash se verifică la recepție
- [ ] Server re-encryption funcționează
- [ ] Ambii agenți au scris rapoarte

---

## FAZA 2 — WEBRTC & NETWORKING (network-engineer + backend-engineer — PARALEL)

### Agent: network-engineer

**Sarcini:**

#### 2.1 Frame-Level E2E Encryption pentru WebRTC Calls
**Fisier:** `src/network/WebRTCManager.ts` (1000 linii)
**Referință:** WebRTC Encoded Transforms API (W3C spec), AES-256-GCM (NIST SP 800-38D)
- La inițializarea call-ului:
  - Generează `callEncryptionKey = nacl.randomBytes(32)` (AES-256 key)
  - Trimite cheia prin canalul E2E de mesagerie (NU prin signaling)
  - Mesajul: `{ type: 'call_key', key: base64(callEncryptionKey) }`
- Implementează frame encryption folosind RTCRtpScriptTransform sau encoded transform:
  - Funcția `encryptFrame(frame: RTCEncodedVideoFrame)`:
    - Păstrează primii N bytes ca plaintext (codec header): key frame=10, delta=3, audio=1
    - Restul: criptează cu AES-256-GCM (importă `react-native-aes-gcm-crypto` sau implementează cu SubtleCrypto)
    - Append: `[12-byte IV random] [16-byte auth tag]`
  - Funcția `decryptFrame(frame: RTCEncodedVideoFrame)`:
    - Extrage IV și auth tag de la sfârșit
    - Decriptează payload-ul cu AES-GCM
    - Reconstruiește frame-ul original
- Înregistrează transform-urile pe sender și receiver tracks
- **Fallback:** dacă platforma nu suportă encoded transforms, loghează warning și continuă fără (SRTP/DTLS rămâne activ)

#### 2.2 Call Signaling prin canalul E2E de mesaje
**Fisier:** `src/network/WebRTCManager.ts` + `src/services/MessagingService.ts`
**Referință:** In-band signaling — eliminarea dependenței de signaling server centralizat pentru call setup
- Mută SDP offer/answer și ICE candidates din signaling server în mesaje E2E:
  - Noi tipuri de mesaje: `call_offer`, `call_answer`, `call_ice`, `call_hangup`
  - Comprimă SDP cu LZ-String (base64) pentru a încăpea în limita de mesaj
  - Trimite prin `MessagingService.sendMessage()` cu `type: 'call_signal'`
- **Păstrează fallback pe SignalingClient** pentru cazul în care peer-ul e offline sau nu suportă E2E signaling
- Flow:
  1. Caller trimite `call_offer` ca mesaj E2E
  2. Callee primește, răspunde cu `call_answer` ca mesaj E2E
  3. ICE candidates se trimit ca mesaje `call_ice`
  4. Dacă nu vine răspuns în 10s, fallback la SignalingClient tradițional

#### 2.3 TURN over TLS pe port 443
**Fisier:** `src/network/WebRTCManager.ts`
**Referință:** RFC 7065 (TURN URI), TURN/TLS pe port 443 pentru traversare firewall
- Actualizează configurația ICE servers:
  - STUN: `stuns:stun.qrchat.app:443` (STUN over TLS)
  - TURN: `turns:turn.qrchat.app:443?transport=tcp` (TURN over TLS/TCP)
- Adaugă opțiune în Settings: "Force relay" (`iceTransportPolicy: 'relay'`)
  - Când e activat, tot traficul media trece prin TURN (ascunde IP-ul)
  - Default: `'all'` (P2P preferat, TURN fallback)
- Salvează preferința în AsyncStorage: `@qrchat_force_relay`

**Rezultat:** Scrie raport în `agent-runtime/outputs/network-phase2-report.md`

---

### Agent: backend-engineer

**Sarcini:**

#### 2.4 Server DH Key Exchange Endpoint
**Fisier:** `server/index.js`
- La event `register`: generează DH key pair cu `nacl.box.keyPair()`
- Trimite `serverPublicKey` clientului în răspunsul de register
- Stochează `sharedSecret` per client în memorie (Map)
- La relay `message`: re-criptează cu `sharedSecret`-ul recipientului (coordonare cu architect 1.6)
- Cleanup: șterge `sharedSecret` la disconnect

#### 2.5 Rate Limiting pe Mesaje și Calls
**Fisier:** `server/index.js`
**Referință:** OWASP Rate Limiting guidelines
- Rate limiting per client:
  - Mesaje: max 30/minut, max 5/secundă
  - Call signals: max 10/minut
  - Register: max 3/minut
- Implementează cu un sliding window counter în memorie (nu dependințe noi)
- La depășire: trimite `{ error: 'RATE_LIMITED', retryAfter: seconds }`
- Loghează încercările de flood (>5x limita)

#### 2.6 Message TTL și Auto-Cleanup pe Server
**Fisier:** `server/index.js`
- Mesajele pending pe server: TTL maxim 48 ore
- Cleanup la fiecare 15 minute: șterge mesajele mai vechi de 48h
- Adaugă timestamp la fiecare mesaj stocat: `storedAt: Date.now()`
- La cleanup: `pendingMessages.forEach((msgs, recipientId) => msgs.filter(m => Date.now() - m.storedAt < TTL))`
- Loghează numărul de mesaje curățate

**Rezultat:** Scrie raport în `agent-runtime/outputs/backend-phase2-report.md`

---

### CHECKPOINT FAZA 2
- [ ] `npx tsc --noEmit` — zero erori
- [ ] Apelurile WebRTC funcționează cu frame encryption
- [ ] Call signaling merge prin canal E2E (cu fallback)
- [ ] Server DH exchange funcționează la connect
- [ ] Rate limiting blochează flood
- [ ] Mesaje vechi se curăță automat

---

## FAZA 3 — UX & PRIVACY FEATURES (frontend-engineer + security-engineer — PARALEL)

### Agent: frontend-engineer

**Sarcini:**

#### 3.1 Incognito Mode
**Fisiere:** `src/screens/SettingsScreen.tsx`, `src/utils/types.ts`, `src/screens/QRScanScreen.tsx`
- În Settings: toggle "Incognito Mode" cu descriere "Use a random name for new contacts"
- Când activat, la scanare QR / accept invite:
  - Generează pseudonim random: `adjective + noun + 3 digits` (ex: "QuietFox482")
  - Lista de ~50 adjective și ~50 substantive în `src/utils/incognitoNames.ts`
  - Acel contact va vedea doar pseudonimul, nu profilul real
- Stochează mapping în SQLite: `incognito_names(contactId TEXT, fakeName TEXT)`
- În UI: contactele incognito au un badge mic (mască/icon) lângă nume
- În ChatScreen: banner "Incognito — [contactName] sees you as [fakeName]"
- **NU afectează** contactele existente — doar cele noi create după activare
- Opțiune per-contact la scanare: "Connect as..." dropdown (real name / incognito)
- i18n: adaugă stringuri în en/ro/ru/fr

#### 3.2 Self-Destruct Passcode
**Fisiere:** `src/screens/SettingsScreen.tsx`, NOU: `src/components/SelfDestructSetup.tsx`
- În Settings > Privacy & Security: opțiune "Self-Destruct Passcode"
- Setup flow:
  1. User setează app lock PIN/passcode normal (dacă nu există deja)
  2. User setează un cod alternativ de self-destruct
  3. Confirmare: "If you enter this code, ALL data will be permanently deleted"
- La introducerea self-destruct code:
  - Șterge baza de date SQLite complet
  - Șterge toate cheile din Keychain/SecureStore
  - Șterge AsyncStorage complet
  - Deschide app-ul cu ecran de setup (ca la prima instalare)
  - **NU trimite** niciun semnal pe rețea (să nu alerteze pe nimeni)
- Stochează hash-ul self-destruct code în Keychain (nu plaintext)
- Self-destruct code trebuie să fie DIFERIT de app lock code

#### 3.3 Per-Conversation Themes
**Fisiere:** `src/screens/ChatScreen.tsx`, `src/screens/ContactProfileScreen.tsx`, `src/utils/ThemeContext.tsx`
- În ContactProfileScreen: secțiune "Chat Appearance"
  - Color picker cu 8 culori preset (accent color pentru acel chat)
  - Opțiune "Dark" / "Light" override per chat
- Stochează în SQLite: `contact_themes(contactId TEXT, accentColor TEXT, mode TEXT)`
- În ChatScreen: aplică tema per-contact peste tema globală
- Bubble-urile de mesaj folosesc accentColor al contactului
- Header-ul ChatScreen arată în culoarea contactului
- **Scop practic:** previne trimiterea accidentală la contactul greșit

#### 3.4 Disappearing Messages (per-conversation)
**Fisiere:** `src/screens/ChatScreen.tsx`, `src/screens/ContactProfileScreen.tsx`
- În ContactProfileScreen: "Disappearing Messages" cu opțiuni:
  - Off, 30 secunde, 5 minute, 1 oră, 24 ore, 7 zile, 30 zile
- La activare: trimite mesaj de tip `system` către contact: "Disappearing messages set to [duration]"
- Timer-ul începe: pentru sender la trimitere, pentru receiver la citire (screen focused)
- Mesajele expirate: se șterg din SQLite + UI se actualizează
- Background cleanup: `setInterval` la 60 secunde verifică mesajele expirate
- Indicație vizuală: icon timer mic pe mesajele cu disappearing activ
- i18n: stringuri noi în toate cele 4 limbi

**Rezultat:** Scrie raport în `agent-runtime/outputs/frontend-phase3-report.md`

---

### Agent: security-engineer (continuă din Faza 1)

**Sarcini:**

#### 3.5 App Lock cu Biometrie + PIN
**Fisiere:** NOU: `src/components/AppLock.tsx`, `App.tsx`
- La prima activare: user setează PIN de 6 cifre
- Stochează hash(PIN + salt) în Keychain cu `react-native-keychain`
- Opțiune: activare Face ID / Touch ID (dacă disponibil)
- Trigger: la deschiderea app-ului + după 30 secunde în background
- Ecran de lock: blur pe conținut, input PIN + buton biometric
- 5 încercări greșite: lockout 5 minute
- Integrează cu self-destruct code de la 3.2
- **NU bloca** notificările push — doar UI-ul

#### 3.6 Screen Protection
**Fisier:** `App.tsx`
- iOS: blur view la resign active (UIApplicationWillResignActiveNotification pattern)
- Android: FLAG_SECURE pe activity (previne screenshots + app switcher preview)
- React Native: folosește `react-native-screen-capture` sau implementează nativ:
  - iOS: event listener pe resign active → adaugă blur view
  - iOS: event listener pe become active → șterge blur view
- Opțiune în Settings: "Screen Protection" toggle (default: ON)
- Salvează în AsyncStorage: `@qrchat_screen_protection`

**Rezultat:** Scrie raport în `agent-runtime/outputs/security-phase3-report.md`

---

### CHECKPOINT FAZA 3
- [ ] `npx tsc --noEmit` — zero erori
- [ ] Incognito mode generează nume random la scan QR
- [ ] Self-destruct code șterge totul și deschide setup
- [ ] Per-conversation themes se aplică corect
- [ ] Disappearing messages se șterg după expirare
- [ ] App lock cu PIN + biometrie funcționează
- [ ] Screen protection blur-ează în app switcher

---

## FAZA 4 — QA, INTEGRARE & VERIFICARE (qa-engineer + release-engineer)

### Agent: qa-engineer

**Sarcini:**

#### 4.1 Teste Unitare
**Director:** `__tests__/`
- `MessagePadding.test.ts`:
  - Test: mesaj 5 bytes → output 16384 bytes
  - Test: mesaj 16000 bytes → output 16384 bytes
  - Test: mesaj 17000 bytes → output 32768 bytes (2 blocuri)
  - Test: pad → unpad = mesaj original (round-trip)
  - Test: padding conține random bytes (nu zerouri)
- `MessageIntegrity.test.ts`:
  - Test: hash chain se construiește corect
  - Test: hash mismatch e detectat (warning logged)
  - Test: primul mesaj (fără prev) funcționează
- `ProtocolVersion.test.ts`:
  - Test: serialize/deserialize envelope v2 round-trip
  - Test: deserialize envelope v1 (backward compat)
  - Test: versiune necunoscută → eroare clară
- `IncognitoMode.test.ts`:
  - Test: generateRandomName() produce format corect
  - Test: două apeluri consecutive produc nume diferite
  - Test: mapping se salvează/citește din SQLite
- `SelfDestruct.test.ts`:
  - Test: hash(code) se stochează corect
  - Test: verificare code corect → true
  - Test: self-destruct code != app lock code

#### 4.2 Teste de Integrare
- `E2EMessageFlow.test.ts`:
  - Simulează 2 clienți: trimitere mesaj v2 cu padding + hash → recepție corectă
  - Client v1 trimite → client v2 primește (backward compat)
  - Client v2 trimite → client v1 primește (graceful degradation)
- `CallEncryption.test.ts`:
  - Simulează key exchange prin canal E2E
  - Verifică că frame encryption/decryption e simetrică

#### 4.3 Verificare Manuală Checklist
Scrie în `agent-runtime/outputs/qa-manual-checklist.md`:
```
## Verificare pe Simulator
- [ ] Deschide app → login → trimite mesaj text → apare la destinatar
- [ ] Verifică că mesajul în tranzit e 16KB (log size)
- [ ] Activează Incognito → scan QR → contactul vede nume random
- [ ] Setează Self-Destruct code → introduce-l → app se resetează complet
- [ ] Setează Disappearing 30s → mesajul dispare după 30s
- [ ] Setează temă per-contact → ChatScreen arată culoarea aleasă
- [ ] Inițiază call → verifică audio → închide
- [ ] Pune app în background → verifică blur în app switcher
- [ ] Introduce PIN greșit de 5 ori → lockout 5 min

## Verificare pe Dispozitiv Fizic (iPhone)
- [ ] Repetă toate testele de mai sus pe iPhone fizic
- [ ] Verifică Face ID / Touch ID pentru app lock
- [ ] Verifică că call-urile audio funcționează pe speaker + earpiece
- [ ] Verifică notificări push cu app în background
- [ ] Verifică că screen protection previne screenshots
```

**Rezultat:** Scrie raport complet în `agent-runtime/outputs/qa-upgrade-report.md`

---

### Agent: release-engineer

**Sarcini:**

#### 4.4 Changelog
**Fisier:** `CHANGELOG.md`
- Adaugă intrare pentru noua versiune:
```markdown
## [Build XXX] - 2026-03-30

### Security Hardening
- Message padding: all messages padded to 16KB fixed blocks (prevents traffic analysis)
- Message integrity chain: prev_msg_hash verification on every message
- Encrypted ratchet headers: DH keys hidden from observers
- Server re-encryption: input/output ciphertext differs (prevents correlation)
- Frame-level E2E encryption for WebRTC calls (AES-256-GCM per frame)
- Call signaling via E2E encrypted channel (with SignalingClient fallback)
- Rate limiting on server (30 msg/min, 10 calls/min)
- Message auto-cleanup on server (48h TTL)

### Privacy
- Incognito Mode: random identity per new contact
- Self-Destruct Passcode: wipes all data under coercion
- App Lock: PIN + Face ID / Touch ID
- Screen Protection: blur in app switcher, prevent screenshots
- Disappearing Messages: 30s to 30 days per conversation

### UX
- Per-conversation themes (accent color, dark/light override)
- Protocol versioning (v2) with backward compatibility
```

#### 4.5 Build Number Increment
**Fisier:** `ios/QRChat.xcodeproj/project.pbxproj`, `android/app/build.gradle`
- Setează CURRENT_PROJECT_VERSION = **201** (seria 200 = upgrade branch)
- Următoarele build-uri: 202, 203, 204...
- **NU modifica** APP_VERSION (rămâne 4.3.0)

#### 4.6 Verificare Finală Automată
Rulează și raportează:
```bash
cd /Users/ruslanconstantinovici/QRChat
npx tsc --noEmit                    # TypeScript check
npx jest --passWithNoTests          # Teste unitare
npx react-native bundle --platform ios --dev false --entry-file index.js --bundle-output /tmp/test-bundle.js  # iOS bundle
npx react-native bundle --platform android --dev false --entry-file index.js --bundle-output /tmp/test-bundle-android.js  # Android bundle
```

**Rezultat:** Scrie raport final în `agent-runtime/outputs/release-upgrade-report.md`

---

## DIAGRAMA DE DEPENDENȚE

```
FAZA 1 (PARALEL):
  security-engineer (1.1 padding, 1.2 hash chain, 1.3 encrypted headers)
  architect (1.4 protocol versioning, 1.5 MessagingService refactor, 1.6 server re-encrypt)

  Dependențe interne:
    architect 1.5 DEPINDE DE security-engineer 1.1, 1.2, 1.3
    architect 1.6 e INDEPENDENT

FAZA 2 (PARALEL, după Faza 1):
  network-engineer (2.1 frame encryption, 2.2 E2E signaling, 2.3 TURN/TLS)
  backend-engineer (2.4 server DH, 2.5 rate limiting, 2.6 message TTL)

  Dependențe interne:
    network-engineer 2.2 DEPINDE DE architect 1.5 (MessagingService types)
    backend-engineer 2.4 DEPINDE DE architect 1.6 (server re-encrypt design)

FAZA 3 (PARALEL, după Faza 2):
  frontend-engineer (3.1 incognito, 3.2 self-destruct, 3.3 themes, 3.4 disappearing)
  security-engineer (3.5 app lock, 3.6 screen protection)

  Dependențe interne:
    frontend-engineer 3.2 COORDONEAZĂ CU security-engineer 3.5 (shared PIN storage)

FAZA 4 (SECVENȚIAL, după Faza 3):
  qa-engineer (4.1 teste unitare, 4.2 teste integrare, 4.3 checklist manual)
  release-engineer (4.4 changelog, 4.5 build number, 4.6 verificare finală)

  Dependențe:
    release-engineer 4.6 DUPĂ qa-engineer 4.1-4.3
```

---

## FIȘIERE MODIFICATE — OWNERSHIP

| Fișier | Agent UNIC responsabil |
|--------|----------------------|
| `src/crypto/DoubleRatchet.ts` | security-engineer |
| `src/utils/protocol.ts` (NOU) | architect |
| `src/services/MessagingService.ts` | architect |
| `server/index.js` | architect (1.6) → backend-engineer (2.4, 2.5, 2.6) SECVENȚIAL |
| `src/network/WebRTCManager.ts` | network-engineer |
| `src/network/SignalingClient.ts` | network-engineer |
| `src/screens/SettingsScreen.tsx` | frontend-engineer |
| `src/screens/ChatScreen.tsx` | frontend-engineer |
| `src/screens/ContactProfileScreen.tsx` | frontend-engineer |
| `src/screens/QRScanScreen.tsx` | frontend-engineer |
| `src/utils/ThemeContext.tsx` | frontend-engineer |
| `src/utils/incognitoNames.ts` (NOU) | frontend-engineer |
| `src/components/SelfDestructSetup.tsx` (NOU) | frontend-engineer |
| `src/components/AppLock.tsx` (NOU) | security-engineer |
| `App.tsx` | security-engineer (3.6 screen protection) |
| `__tests__/*` | qa-engineer |
| `CHANGELOG.md` | release-engineer |
| `ios/QRChat.xcodeproj/project.pbxproj` | release-engineer |
| `android/app/build.gradle` | release-engineer |
| `src/i18n/locales/*.json` | frontend-engineer |
| `agent-runtime/state/status.md` | TOȚI (actualizări status) |
| `agent-runtime/outputs/*` | TOȚI (rapoartele proprii) |

---

## COMANDA DE LANSARE

```
Lansează echipa QRChat cu următorii agenți, în ordinea fazelor:

FAZA 1 (paralel): security-engineer + architect
FAZA 2 (paralel, după Faza 1): network-engineer + backend-engineer
FAZA 3 (paralel, după Faza 2): frontend-engineer + security-engineer
FAZA 4 (secvențial, după Faza 3): qa-engineer → release-engineer

Fiecare agent citește acest prompt complet și execută DOAR sarcinile sale.
După fiecare fază, se verifică checkpoint-ul înainte de a trece la următoarea.
La final, release-engineer rulează verificarea totală și raportează rezultatul.

TOATE modificările pe branch-ul feature/security-privacy-upgrade.
NU face push. NU modifica versiunea. Incrementează DOAR build number la final.
```

---

## VERIFICARE FINALĂ (după toate fazele)

Lead-ul (tu) verifică:
1. `git diff main --stat` — confirmă că doar fișierele din tabelul de ownership au fost modificate
2. `npx tsc --noEmit` — zero erori TypeScript
3. `npx jest` — toate testele trec
4. Bundle iOS și Android se construiesc fără erori
5. App-ul pornește pe simulator
6. Trimite un mesaj → apare la destinatar
7. Inițiază un call → audio funcționează
8. Testează Incognito, Self-Destruct, Disappearing, App Lock
9. Verifică că mesajele vechi (v1) se citesc în continuare

**Dacă ceva nu merge:** `git checkout main` — Build 101 stabil, zero risc.

**Dacă totul merge:** merge branch în main, incrementează build number, commit, apoi întreabă user-ul dacă vrea TestFlight deploy.
