# PROMPT MASTER: QRChat SimpleX-Inspired Security & UX Upgrade

## OBIECTIV GENERAL

Implementeaza 12 imbunatatiri inspirate din SimpleX Chat in QRChat. Lucrul se face in **4 faze secventiale**, cu agenti lucrand **in paralel** in cadrul fiecarei faze. Fiecare agent modifica DOAR fisierele din domeniul sau. La final, se face verificare totala.

**Proiect:** `/Users/ruslanconstantinovici/QRChat`
**Versiune curenta:** 4.3.0
**Tech stack:** React Native 0.84, TypeScript, Node.js server, TweetNaCl, WebRTC, SQLite

---

## REGULI OBLIGATORII PENTRU TOTI AGENTII

1. **Citeste fisierul INAINTE de a-l modifica** — nu presupune structura
2. **Updateaza `agent-runtime/state/status.md`** cand incepi/finalizezi o sarcina
3. **Daca depinzi de alt agent** — scrie in `agent-runtime/messages/{de-la}-to-{catre}.md` si marcheaza BLOCKED
4. **Nu face push la git** fara aprobarea lead-ului
5. **Nu modifica fisiere din domeniul altui agent** — daca ai nevoie, trimite mesaj
6. **Incrementeaza build number** la finalul fazei, nu dupa fiecare modificare
7. **Testeaza compilarea** dupa fiecare modificare (`npx tsc --noEmit`)
8. **Nu adauga dependente npm** fara aprobarea lead-ului
9. **Scrie cod TypeScript strict** — fara `any`, fara `@ts-ignore`
10. **Comentarii in engleza**, nume variabile descriptive

---

## FAZA 1 — SECURITATE CORE (security-engineer + architect — PARALEL)

### Agent: security-engineer

**Sarcini:**

#### 1.1 Message Padding — blocuri fixe de 16KB
**Fisier:** `src/crypto/DoubleRatchet.ts` (260 linii)
- Adauga functia `padMessage(plaintext: Uint8Array): Uint8Array` care:
  - Prepend 4 bytes cu lungimea originala (uint32 big-endian)
  - Pad cu random bytes pana la 16384 bytes total
  - Daca mesajul > 16380 bytes, pad la urmatorul multiplu de 16384
- Adauga functia `unpadMessage(padded: Uint8Array): Uint8Array` care:
  - Citeste primii 4 bytes ca lungime
  - Returneaza doar payload-ul original
- Integreaza `padMessage` in `encrypt()` INAINTE de `nacl.secretbox`
- Integreaza `unpadMessage` in `decrypt()` DUPA `nacl.secretbox.open`
- **Test:** mesaj de 5 bytes si mesaj de 1000 bytes produc acelasi output size (16384)

#### 1.2 Message Integrity Chain (prev_msg_hash)
**Fisier:** `src/crypto/DoubleRatchet.ts`
- Adauga camp `prevMsgHash: string` in starea ratchet
- La fiecare mesaj trimis: `currentHash = sha256(prevMsgHash + ciphertext)`
- Include `prevMsgHash` in header-ul mesajului (primele 32 bytes inainte de ciphertext)
- La receptie: verifica ca `prevMsgHash` din header == ultimul hash primit de la acel contact
- Daca nu se potriveste: log warning dar NU refuza mesajul (backward compatibility)
- Foloseste `tweetnacl` hash sau importa `js-sha256` (fara dependente native noi)

#### 1.3 Encrypted Message Headers
**Fisier:** `src/crypto/DoubleRatchet.ts`
- Header-ul ratchet (DH public key, message number, previous chain length) sa fie criptat cu o cheie derivata separat din root key
- Deriva `headerKey` cu HKDF din root key: `headerKey = hkdf(rootKey, "header")`
- Cripteaza header-ul cu `nacl.secretbox(header, nonce, headerKey)` SEPARAT de body
- Formatul mesajului devine: `[encryptedHeader | encryptedBody]`
- Actualizeaza `decrypt()` sa decripteze header-ul intai, apoi body-ul

**Rezultat:** Scrie raport in `agent-runtime/outputs/security-phase1-report.md`

---

### Agent: architect

**Sarcini:**

#### 1.4 Definire Protocol Versioning
**Fisier NOU:** `src/utils/protocol.ts`
- Defineste `PROTOCOL_VERSION = 2` (v1 = format curent fara padding/hash)
- Defineste interfata `MessageEnvelope`:
```typescript
interface MessageEnvelope {
  version: number;           // 1 sau 2
  encryptedHeader: Uint8Array; // doar v2
  encryptedBody: Uint8Array;
  prevMsgHash?: string;      // doar v2
  padding?: boolean;         // doar v2
}
```
- Functie `serializeEnvelope(env: MessageEnvelope): Uint8Array`
- Functie `deserializeEnvelope(data: Uint8Array): MessageEnvelope`
- Backward compatible: daca `version == 1`, parseaza ca format vechi
- Exporta tot din `src/utils/protocol.ts`

#### 1.5 Refactorizare MessagingService pentru noul protocol
**Fisier:** `src/services/MessagingService.ts` (2509 linii)
- In metoda de trimitere: wrapeaza mesajul in `MessageEnvelope` v2
- In metoda de receptie: detecteaza versiunea si parseaza corespunzator
- Daca receptorul trimite v1 (peer vechi): accepta fara padding/hash
- Daca trimitem catre peer cu versiune necunoscuta: trimitem v1 (safe fallback)
- Adauga `peerProtocolVersion: Map<string, number>` — se populeaza la primul mesaj primit
- La handshake/key exchange: include `protocolVersion` in payload

#### 1.6 Server-Side Message Re-encryption
**Fisier:** `server/index.js` (1419 linii)
- La inregistrarea clientului: server + client fac DH exchange (Curve25519)
  - Server genereaza `serverKeyPair = nacl.box.keyPair()`
  - Trimite `serverKeyPair.publicKey` clientului la connect
  - Calculeaza `sharedSecret = nacl.box.before(clientPublicKey, serverSecretKey)`
- La relay mesaj: server re-cripteaza cu `sharedSecret` al recipientului
  - Input: `nacl.box.open(ciphertext, nonce, senderShared)` → plaintext E2E criptat
  - Output: `nacl.box(e2ePayload, newNonce, recipientShared)` → alt ciphertext
  - Rezultat: ciphertext care intra pe server != ciphertext care iese
- **NU decripteaza E2E** — doar schimba layer-ul de transport
- Clientul: `src/network/SignalingClient.ts` — adauga DH exchange la connect

**Rezultat:** Scrie raport in `agent-runtime/outputs/architect-phase1-report.md`

---

### CHECKPOINT FAZA 1
**Inainte de a trece la Faza 2:**
- [ ] `npx tsc --noEmit` — zero erori
- [ ] Mesajele vechi (v1) se pot decripta in continuare
- [ ] Mesaje noi au padding 16KB
- [ ] prevMsgHash se verifica la receptie
- [ ] Server re-encryption functioneaza
- [ ] Ambii agenti au scris rapoarte

---

## FAZA 2 — WEBRTC & NETWORKING (network-engineer + backend-engineer — PARALEL)

### Agent: network-engineer

**Sarcini:**

#### 2.1 Frame-Level E2E Encryption pentru WebRTC Calls
**Fisier:** `src/network/WebRTCManager.ts` (1000 linii)
- La initializarea call-ului:
  - Genereaza `callEncryptionKey = nacl.randomBytes(32)` (AES-256 key)
  - Trimite cheia prin canalul E2E de mesagerie (NU prin signaling)
  - Mesajul: `{ type: 'call_key', key: base64(callEncryptionKey) }`
- Implementeaza frame encryption folosind RTCRtpScriptTransform sau encoded transform:
  - Functia `encryptFrame(frame: RTCEncodedVideoFrame)`:
    - Pastreaza primii N bytes ca plaintext (codec header): key frame=10, delta=3, audio=1
    - Restul: cripteaza cu AES-256-GCM (importa `react-native-aes-gcm-crypto` sau implementeaza cu SubtleCrypto)
    - Append: `[12-byte IV random] [16-byte auth tag]`
  - Functia `decryptFrame(frame: RTCEncodedVideoFrame)`:
    - Extrage IV si auth tag de la sfarsit
    - Decripteaza payload-ul cu AES-GCM
    - Reconstruieste frame-ul original
- Inregistreaza transform-urile pe sender si receiver tracks
- **Fallback:** daca platforma nu suporta encoded transforms, logheaza warning si continua fara (SRTP/DTLS ramane activ)

#### 2.2 Call Signaling prin canalul E2E de mesaje
**Fisier:** `src/network/WebRTCManager.ts` + `src/services/MessagingService.ts`
- Muta SDP offer/answer si ICE candidates din signaling server in mesaje E2E:
  - Noi tipuri de mesaje: `call_offer`, `call_answer`, `call_ice`, `call_hangup`
  - Comprima SDP cu LZ-String (base64) pentru a incapea in limita de mesaj
  - Trimite prin `MessagingService.sendMessage()` cu `type: 'call_signal'`
- **Pastreaza fallback pe SignalingClient** pentru cazul in care peer-ul e offline sau nu suporta E2E signaling
- Flow:
  1. Caller trimite `call_offer` ca mesaj E2E
  2. Callee primeste, raspunde cu `call_answer` ca mesaj E2E
  3. ICE candidates se trimit ca mesaje `call_ice`
  4. Daca nu vine raspuns in 10s, fallback la SignalingClient traditional

#### 2.3 TURN over TLS pe port 443
**Fisier:** `src/network/WebRTCManager.ts`
- Actualizeaza configuratia ICE servers:
  - STUN: `stuns:stun.qrchat.app:443` (STUN over TLS)
  - TURN: `turns:turn.qrchat.app:443?transport=tcp` (TURN over TLS/TCP)
- Adauga optiune in Settings: "Force relay" (`iceTransportPolicy: 'relay'`)
  - Cand e activat, tot traficul media trece prin TURN (ascunde IP-ul)
  - Default: `'all'` (P2P preferat, TURN fallback)
- Salveaza preferinta in AsyncStorage: `@qrchat_force_relay`

**Rezultat:** Scrie raport in `agent-runtime/outputs/network-phase2-report.md`

---

### Agent: backend-engineer

**Sarcini:**

#### 2.4 Server DH Key Exchange Endpoint
**Fisier:** `server/index.js`
- La event `register`: genereaza DH key pair cu `nacl.box.keyPair()`
- Trimite `serverPublicKey` clientului in raspunsul de register
- Stocheaza `sharedSecret` per client in memorie (Map)
- La relay `message`: re-cripteaza cu `sharedSecret`-ul recipientului (coordonare cu architect 1.6)
- Cleanup: sterge `sharedSecret` la disconnect

#### 2.5 Rate Limiting pe Mesaje si Calls
**Fisier:** `server/index.js`
- Rate limiting per client:
  - Mesaje: max 30/minut, max 5/secunda
  - Call signals: max 10/minut
  - Register: max 3/minut
- Implementeaza cu un sliding window counter in memorie (nu dependinte noi)
- La depasire: trimite `{ error: 'RATE_LIMITED', retryAfter: seconds }`
- Logheaza incercarile de flood (>5x limita)

#### 2.6 Message TTL si Auto-Cleanup pe Server
**Fisier:** `server/index.js`
- Mesajele pending pe server: TTL maxim 48 ore
- Cleanup la fiecare 15 minute: sterge mesajele mai vechi de 48h
- Adauga timestamp la fiecare mesaj stocat: `storedAt: Date.now()`
- La cleanup: `pendingMessages.forEach((msgs, recipientId) => msgs.filter(m => Date.now() - m.storedAt < TTL))`
- Logheaza numarul de mesaje curatate

**Rezultat:** Scrie raport in `agent-runtime/outputs/backend-phase2-report.md`

---

### CHECKPOINT FAZA 2
- [ ] `npx tsc --noEmit` — zero erori
- [ ] Apelurile WebRTC functioneaza cu frame encryption
- [ ] Call signaling merge prin canal E2E (cu fallback)
- [ ] Server DH exchange functioneaza la connect
- [ ] Rate limiting blocheaza flood
- [ ] Mesaje vechi se curata automat

---

## FAZA 3 — UX & PRIVACY FEATURES (frontend-engineer + security-engineer — PARALEL)

### Agent: frontend-engineer

**Sarcini:**

#### 3.1 Incognito Mode
**Fisiere:** `src/screens/SettingsScreen.tsx`, `src/utils/types.ts`, `src/screens/QRScanScreen.tsx`
- In Settings: toggle "Incognito Mode" cu descriere "Use a random name for new contacts"
- Cand activat, la scanare QR / accept invite:
  - Genereaza pseudonim random: `adjective + noun + 3 digits` (ex: "QuietFox482")
  - Lista de ~50 adjective si ~50 substantive in `src/utils/incognitoNames.ts`
  - Acel contact va vedea doar pseudonimul, nu profilul real
- Stocheaza mapping in SQLite: `incognito_names(contactId TEXT, fakeName TEXT)`
- In UI: contactele incognito au un badge mic (masca/icon) langa nume
- In ChatScreen: banner "Incognito — [contactName] sees you as [fakeName]"
- **NU afecteaza** contactele existente — doar cele noi create dupa activare
- Optiune per-contact la scanare: "Connect as..." dropdown (real name / incognito)
- i18n: adauga stringuri in en/ro/ru/fr

#### 3.2 Self-Destruct Passcode
**Fisiere:** `src/screens/SettingsScreen.tsx`, NOU: `src/components/SelfDestructSetup.tsx`
- In Settings > Privacy & Security: optiune "Self-Destruct Passcode"
- Setup flow:
  1. User seteaza app lock PIN/passcode normal (daca nu exista deja)
  2. User seteaza un cod alternativ de self-destruct
  3. Confirmare: "If you enter this code, ALL data will be permanently deleted"
- La introducerea self-destruct code:
  - Sterge baza de date SQLite complet
  - Sterge toate cheile din Keychain/SecureStore
  - Sterge AsyncStorage complet
  - Deschide app-ul cu ecran de setup (ca la prima instalare)
  - **NU trimite** niciun semnal pe retea (sa nu alerteze pe nimeni)
- Stocheaza hash-ul self-destruct code in Keychain (nu plaintext)
- Self-destruct code trebuie sa fie DIFERIT de app lock code

#### 3.3 Per-Conversation Themes
**Fisiere:** `src/screens/ChatScreen.tsx`, `src/screens/ContactProfileScreen.tsx`, `src/utils/ThemeContext.tsx`
- In ContactProfileScreen: sectiune "Chat Appearance"
  - Color picker cu 8 culori preset (accent color pentru acel chat)
  - Optiune "Dark" / "Light" override per chat
- Stocheaza in SQLite: `contact_themes(contactId TEXT, accentColor TEXT, mode TEXT)`
- In ChatScreen: aplica tema per-contact peste tema globala
- Bubble-urile de mesaj folosesc accentColor al contactului
- Header-ul ChatScreen arata in culoarea contactului
- **Scop practic:** previne trimiterea accidentala la contactul gresit

#### 3.4 Disappearing Messages (per-conversation)
**Fisiere:** `src/screens/ChatScreen.tsx`, `src/screens/ContactProfileScreen.tsx`
- In ContactProfileScreen: "Disappearing Messages" cu optiuni:
  - Off, 30 secunde, 5 minute, 1 ora, 24 ore, 7 zile, 30 zile
- La activare: trimite mesaj de tip `system` catre contact: "Disappearing messages set to [duration]"
- Timer-ul incepe: pentru sender la trimitere, pentru receiver la citire (screen focused)
- Mesajele expirate: se sterg din SQLite + UI se actualizeaza
- Background cleanup: `setInterval` la 60 secunde verifica mesajele expirate
- Indicatie vizuala: icon timer mic pe mesajele cu disappearing activ
- i18n: stringuri noi in toate cele 4 limbi

**Rezultat:** Scrie raport in `agent-runtime/outputs/frontend-phase3-report.md`

---

### Agent: security-engineer (continua din Faza 1)

**Sarcini:**

#### 3.5 App Lock cu Biometrie + PIN
**Fisiere:** NOU: `src/components/AppLock.tsx`, `App.tsx`
- La prima activare: user seteaza PIN de 6 cifre
- Stocheaza hash(PIN + salt) in Keychain cu `react-native-keychain`
- Optiune: activare Face ID / Touch ID (daca disponibil)
- Trigger: la deschiderea app-ului + dupa 30 secunde in background
- Ecran de lock: blur pe continut, input PIN + buton biometric
- 5 incercari gresite: lockout 5 minute
- Integreaza cu self-destruct code de la 3.2
- **NU bloca** notificarile push — doar UI-ul

#### 3.6 Screen Protection
**Fisier:** `App.tsx`
- iOS: adauga `UIApplication.shared.windows.first?.layer.addSublayer(secureLayer)` pentru blur in app switcher
- Android: adauga `FLAG_SECURE` pe activity (previne screenshots + app switcher preview)
- React Native: foloseste `react-native-screen-capture` sau implementeaza nativ:
  - iOS: event listener pe `UIApplicationWillResignActiveNotification` → adauga blur view
  - iOS: event listener pe `UIApplicationDidBecomeActiveNotification` → sterge blur view
- Optiune in Settings: "Screen Protection" toggle (default: ON)
- Salveaza in AsyncStorage: `@qrchat_screen_protection`

**Rezultat:** Scrie raport in `agent-runtime/outputs/security-phase3-report.md`

---

### CHECKPOINT FAZA 3
- [ ] `npx tsc --noEmit` — zero erori
- [ ] Incognito mode genereaza nume random la scan QR
- [ ] Self-destruct code sterge totul si deschide setup
- [ ] Per-conversation themes se aplica corect
- [ ] Disappearing messages se sterg dupa expirare
- [ ] App lock cu PIN + biometrie functioneaza
- [ ] Screen protection blur-eaza in app switcher

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
  - Test: padding contine random bytes (nu zerouri)
- `MessageIntegrity.test.ts`:
  - Test: hash chain se construieste corect
  - Test: hash mismatch e detectat (warning logged)
  - Test: primul mesaj (fara prev) functioneaza
- `ProtocolVersion.test.ts`:
  - Test: serialize/deserialize envelope v2 round-trip
  - Test: deserialize envelope v1 (backward compat)
  - Test: versiune necunoscuta → eroare clara
- `IncognitoMode.test.ts`:
  - Test: generateRandomName() produce format corect
  - Test: doua apeluri consecutive produc nume diferite
  - Test: mapping se salveaza/citeste din SQLite
- `SelfDestruct.test.ts`:
  - Test: hash(code) se stocheaza corect
  - Test: verificare code corect → true
  - Test: self-destruct code != app lock code

#### 4.2 Teste de Integrare
- `E2EMessageFlow.test.ts`:
  - Simuleaza 2 clienti: trimitere mesaj v2 cu padding + hash → receptie corecta
  - Client v1 trimite → client v2 primeste (backward compat)
  - Client v2 trimite → client v1 primeste (graceful degradation)
- `CallEncryption.test.ts`:
  - Simuleaza key exchange prin canal E2E
  - Verifica ca frame encryption/decryption e simetrica

#### 4.3 Verificare Manuala Checklist
Scrie in `agent-runtime/outputs/qa-manual-checklist.md`:
```
## Verificare pe Simulator
- [ ] Deschide app → login → trimite mesaj text → apare la destinatar
- [ ] Verifica ca mesajul in tranzit e 16KB (log size)
- [ ] Activeaza Incognito → scan QR → contactul vede nume random
- [ ] Seteaza Self-Destruct code → introduce-l → app se reseteaza complet
- [ ] Seteaza Disappearing 30s → mesajul dispare dupa 30s
- [ ] Seteaza tema per-contact → ChatScreen arata culoarea aleasa
- [ ] Initiaza call → verifica audio → inchide
- [ ] Pune app in background → verifica blur in app switcher
- [ ] Introduce PIN gresit de 5 ori → lockout 5 min

## Verificare pe Dispozitiv Fizic (iPhone)
- [ ] Repeta toate testele de mai sus pe iPhone fizic
- [ ] Verifica Face ID / Touch ID pentru app lock
- [ ] Verifica ca call-urile audio functioneaza pe speaker + earpiece
- [ ] Verifica notificari push cu app in background
- [ ] Verifica ca screen protection previne screenshots
```

**Rezultat:** Scrie raport complet in `agent-runtime/outputs/qa-simplex-upgrade-report.md`

---

### Agent: release-engineer

**Sarcini:**

#### 4.4 Changelog
**Fisier:** `CHANGELOG.md`
- Adauga intrare pentru noua versiune:
```markdown
## [Build XXX] - 2026-03-30

### Security (SimpleX-Inspired Upgrade)
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
- Incrementeaza CURRENT_PROJECT_VERSION cu +1
- **NU modifica** APP_VERSION (ramane 4.3.0)

#### 4.6 Verificare Finala Automata
Ruleaza si raporteaza:
```bash
cd /Users/ruslanconstantinovici/QRChat
npx tsc --noEmit                    # TypeScript check
npx jest --passWithNoTests          # Teste unitare
npx react-native bundle --platform ios --dev false --entry-file index.js --bundle-output /tmp/test-bundle.js  # iOS bundle
npx react-native bundle --platform android --dev false --entry-file index.js --bundle-output /tmp/test-bundle-android.js  # Android bundle
```

**Rezultat:** Scrie raport final in `agent-runtime/outputs/release-simplex-upgrade-report.md`

---

## DIAGRAMA DE DEPENDENTE

```
FAZA 1 (PARALEL):
  security-engineer (1.1 padding, 1.2 hash chain, 1.3 encrypted headers)
  architect (1.4 protocol versioning, 1.5 MessagingService refactor, 1.6 server re-encrypt)

  Dependente interne:
    architect 1.5 DEPINDE DE security-engineer 1.1, 1.2, 1.3
    architect 1.6 e INDEPENDENT

FAZA 2 (PARALEL, dupa Faza 1):
  network-engineer (2.1 frame encryption, 2.2 E2E signaling, 2.3 TURN/TLS)
  backend-engineer (2.4 server DH, 2.5 rate limiting, 2.6 message TTL)

  Dependente interne:
    network-engineer 2.2 DEPINDE DE architect 1.5 (MessagingService types)
    backend-engineer 2.4 DEPINDE DE architect 1.6 (server re-encrypt design)

FAZA 3 (PARALEL, dupa Faza 2):
  frontend-engineer (3.1 incognito, 3.2 self-destruct, 3.3 themes, 3.4 disappearing)
  security-engineer (3.5 app lock, 3.6 screen protection)

  Dependente interne:
    frontend-engineer 3.2 COORDINEAZA CU security-engineer 3.5 (shared PIN storage)

FAZA 4 (SECVENTIAL, dupa Faza 3):
  qa-engineer (4.1 teste unitare, 4.2 teste integrare, 4.3 checklist manual)
  release-engineer (4.4 changelog, 4.5 build number, 4.6 verificare finala)

  Dependente:
    release-engineer 4.6 DUPA qa-engineer 4.1-4.3
```

---

## FISIERE MODIFICATE — OWNERSHIP

| Fisier | Agent UNIC responsabil |
|--------|----------------------|
| `src/crypto/DoubleRatchet.ts` | security-engineer |
| `src/utils/protocol.ts` (NOU) | architect |
| `src/services/MessagingService.ts` | architect |
| `server/index.js` | architect (1.6) → backend-engineer (2.4, 2.5, 2.6) SECVENTIAL |
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
| `agent-runtime/state/status.md` | TOTI (actualizari status) |
| `agent-runtime/outputs/*` | TOTI (rapoartele proprii) |

---

## COMANDA DE LANSARE

```
Lanseaza echipa QRChat cu urmatorii agenti, in ordinea fazelor:

FAZA 1 (paralel): security-engineer + architect
FAZA 2 (paralel, dupa Faza 1): network-engineer + backend-engineer
FAZA 3 (paralel, dupa Faza 2): frontend-engineer + security-engineer
FAZA 4 (secvential, dupa Faza 3): qa-engineer → release-engineer

Fiecare agent citeste acest prompt complet si executa DOAR sarcinile sale.
Dupa fiecare faza, se verifica checkpoint-ul inainte de a trece la urmatoarea.
La final, release-engineer ruleaza verificarea totala si raporteaza rezultatul.

NU face push. NU modifica versiunea. Incrementeaza DOAR build number la final.
```

---

## VERIFICARE FINALA (dupa toate fazele)

Lead-ul (tu) verifica:
1. `git diff --stat` — confirma ca doar fisierele din tabelul de ownership au fost modificate
2. `npx tsc --noEmit` — zero erori TypeScript
3. `npx jest` — toate testele trec
4. Bundle iOS si Android se construiesc fara erori
5. App-ul porneste pe simulator
6. Trimite un mesaj → apare la destinatar
7. Initiaza un call → audio functioneaza
8. Testeaza Incognito, Self-Destruct, Disappearing, App Lock
9. Verifica ca mesajele vechi (v1) se citesc in continuare

**Dupa verificare:** incrementeaza build number, fa commit, apoi intreaba user-ul daca vrea TestFlight deploy.
