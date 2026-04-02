# Prompt: Security Engineer — Privacy Policy Audit & Validation

**Agent:** security-engineer
**Data:** 2026-03-21
**Prioritate:** CRITICA — blocheaza release-engineer
**Rezultat:** `agent-runtime/outputs/privacy-security-audit.md`

---

## Context

QRChat pregateste o noua versiune a Privacy Policy-ului care trebuie sa fie conforma cu GDPR, CCPA/CPRA, Apple App Store Guidelines 5.1, Google Play User Data Policy, COPPA, Legea Republicii Moldova Nr. 133/2011 privind protectia datelor cu caracter personal, si ePrivacy Directive.

**Tu, security-engineer, trebuie sa auditezi si sa validezi ca fiecare afirmatie tehnica din Privacy Policy este 100% corecta si reflecta exact ce face codul.** Release-engineer-ul va folosi audit-ul tau pentru a rescrie HTML-ul final.

---

## Fisiere de citit si analizat

### Server-side (ce date trec prin server, ce se stocheaza)
1. `/Users/ruslanconstantinovici/QRChat/server/index.js` — serverul principal WebSocket
   - Verifica: ce date tranziteaza serverul, ce se logheaza, ce se stocheaza pe disk
   - Verifica: pending messages — format, criptare, TTL (48h), dimensiune maxima
   - Verifica: daca exista vreun log care capteaza date personale sau continut de mesaje
   - Verifica: WebSocket connections — ce date se transmit la handshake

2. `/Users/ruslanconstantinovici/QRChat/server/push.js` — push notifications
   - Verifica: ce date se stocheaza pentru push (mailboxId, APNs token)
   - Verifica: ce payload se trimite catre APNs (confirma ca NU contine text mesaj)
   - Verifica: separarea userId <-> mailboxId <-> pushToken (doua Map-uri separate)
   - Verifica: ce se intampla cand un token devine invalid (BadDeviceToken/Unregistered)
   - Verifica: throttling (1 push per 30s per mailbox)
   - Verifica: persistenta pe disk (qrchat_push_tokens.json, qrchat_user_mailboxes.json)

3. `/Users/ruslanconstantinovici/QRChat/server/licensing.js` — licensing/promo codes
   - Verifica: ce device ID se stocheaza (hashed? raw?)
   - Verifica: cum se persisteaza (qrchat_licensed.json)
   - Verifica: daca device ID-ul poate fi legat de user identity

### Client-side (ce se stocheaza pe device)
4. `/Users/ruslanconstantinovici/QRChat/crypto/CryptoService.ts` — criptografie
   - Verifica: algoritmii exacti folositi (TweetNaCl: XSalsa20-Poly1305 pentru box, X25519 pentru key exchange, Ed25519 pentru signing)
   - Verifica: cum se genereaza key pair-ul
   - Verifica: cum se stocheaza private key (Keychain)
   - Verifica: cum functioneaza Double Ratchet (daca e implementat)

5. `/Users/ruslanconstantinovici/QRChat/storage/Database.ts` — SQLCipher
   - Verifica: criptarea bazei de date (AES-256 via SQLCipher)
   - Verifica: cum se stocheaza cheia DB in Keychain
   - Verifica: accessibility level (WHEN_UNLOCKED_THIS_DEVICE_ONLY)
   - Verifica: ce date se stocheaza in DB (mesaje, contacte, settings)

6. `/Users/ruslanconstantinovici/QRChat/services/PushTokenService.ts` — client push
   - Verifica: cum se genereaza mailbox ID (nacl.randomBytes(16))
   - Verifica: cum se trimite push token-ul la server
   - Verifica: daca mailbox ID-ul e derivat din vreun key material sau e pur random

7. `/Users/ruslanconstantinovici/QRChat/services/MessagingService.ts` — messaging
   - Verifica: criptarea mesajelor inainte de transmisie
   - Verifica: ce tipuri de mesaje se cripteaza (text, image, audio, video, file)
   - Verifica: daca vreun mesaj ajunge necriptat pe server

8. `/Users/ruslanconstantinovici/QRChat/network/` — WebRTC, P2P
   - Verifica: criptarea media streams (voice/video calls)
   - Verifica: TURN relay — ce date trec prin Metered.ca
   - Verifica: signaling — ce date se trimit pentru stabilirea conexiunii

### Privacy-related files
9. `/Users/ruslanconstantinovici/QRChat/ios/QRChat/PrivacyInfo.xcprivacy` — Apple Privacy Manifest
10. `/Users/ruslanconstantinovici/QRChat/ios/QRChat/Info.plist` — encryption flags, usage descriptions
11. `/Users/ruslanconstantinovici/QRChat/docs/privacy.html` — privacy policy actuala

---

## Sarcini concrete

### Task 1: Audit complet al fluxurilor de date
Creeaza un tabel cu TOATE datele care parasesc device-ul utilizatorului si ajung pe server sau la third-party services:

| Data | Destinatie | Criptat E2E? | Stocheaza server? | Retentie | Poate fi legat de identitate? |
|------|-----------|-------------|-------------------|----------|-------------------------------|

Include explicit:
- WebSocket handshake data
- Public key (user ID)
- Mailbox ID
- APNs device token
- Pending encrypted messages
- Licensed device ID
- TURN relay traffic
- Signaling data (SDP offers, ICE candidates)
- Push notification payloads trimise catre APNs

### Task 2: Verificare afirmatii privacy policy
Verifica fiecare afirmatie din privacy policy-ul curent (citeste `/Users/ruslanconstantinovici/QRChat/docs/privacy.html`) si confirma/infirma cu referinta la cod:

1. "All messages are end-to-end encrypted before leaving your device" — **CONFIRMA/INFIRMA** cu path la cod
2. "Our server relays encrypted blobs it cannot decrypt" — **CONFIRMA/INFIRMA**
3. "QRChat requires no registration, no phone number, and no email address" — **CONFIRMA/INFIRMA**
4. "Contact discovery happens exclusively via in-person QR code scanning" — **CONFIRMA/INFIRMA**
5. "QRChat contains no analytics SDKs, no crash reporting services" — **CONFIRMA/INFIRMA** (verifica package.json, Podfile)
6. "QRChat does not use IDFA, IDFV" — **CONFIRMA/INFIRMA**
7. "Private keys are stored exclusively in the iOS Keychain" — **CONFIRMA/INFIRMA**
8. "The database encryption key is stored in the iOS Keychain with WHEN_UNLOCKED_THIS_DEVICE_ONLY" — **CONFIRMA/INFIRMA**
9. "Anonymous Mailbox ID: A random 128-bit identifier (not derived from any key material or personal data)" — **CONFIRMA/INFIRMA**
10. "Push notification throttling (maximum 1 per 30 seconds per mailbox)" — **CONFIRMA/INFIRMA**
11. "Encrypted pending messages stored for maximum 48 hours" — **CONFIRMA/INFIRMA** (verifica TTL enforcement)
12. "WebSocket connections over TLS (wss://)" — **CONFIRMA/INFIRMA**
13. "Licensed Device ID — a hashed device identifier" — **CONFIRMA/INFIRMA** (e hashed sau raw?)

### Task 3: Identificare lipsuri de securitate relevante pentru privacy
Raporteaza orice descoperi care ar putea fi problematic din punct de vedere al privacy-ului:

- Server logs care capteaza date sensibile
- Metadata expusa (timestamps, IP addresses, message sizes)
- Corelari posibile intre date (public key + mailbox ID + device token)
- Potential de fingerprinting
- Date care se transmit in clar (necriptat)

### Task 4: Recomandari pentru privacy policy
Bazeaza-te pe codul real pentru a recomanda:
- Ce trebuie adaugat in privacy policy (lipsuri)
- Ce trebuie corectat (afirmatii incorecte)
- Ce trebuie detaliat mai bine (afirmatii vagi)

---

## Legislatie relevanta pe care trebuie sa o tii cont

### GDPR (EU) — Regulation (EU) 2016/679
- **Art. 5(1)(c)**: Principiul minimizarii datelor — verifica ca se colecteaza strict minimul necesar
- **Art. 25**: Privacy by design and by default — verifica ca arhitectura reflecta privacy-by-design
- **Art. 32**: Masuri tehnice de securitate — verifica ca masurile descrise sunt reale si suficiente
- **Art. 35**: DPIA (Data Protection Impact Assessment) — evalueaza daca e necesar un DPIA
- **Recital 26**: Date anonimizate vs. pseudonimizate — stabileste daca mailbox ID + public key sunt date personale sub GDPR

### Apple App Store Guidelines — Section 5.1
- **5.1.1(i)**: Privacy policy trebuie sa descrie corect ce date se colecteaza si cum
- **5.1.1(ii)**: Orice colectare de date necesita consimtamant explicit
- **5.1.1(iii)**: Data minimization — sa nu ceara acces la mai multe date decat e necesar

### Google Play — User Data Policy
- Trebuie declarate toate datele colectate/trimise de app in Data Safety Section
- Trebuie specificat daca datele sunt criptate in transit si end-to-end
- Trebuie specificat daca utilizatorul poate solicita stergerea datelor

---

## Format rezultat

Scrie rezultatul in `agent-runtime/outputs/privacy-security-audit.md` cu urmatoarea structura:

```markdown
# Privacy Policy — Security Audit

## 1. Data Flow Audit
[tabelul de la Task 1]

## 2. Privacy Policy Claim Verification
[rezultatele Task 2 — fiecare afirmatie cu CONFIRMAT/INFIRMAT + referinta cod]

## 3. Privacy Concerns Identified
[rezultatele Task 3]

## 4. Recommendations for Privacy Policy
### 4.1 Items to Add
### 4.2 Items to Correct
### 4.3 Items to Clarify

## 5. GDPR Technical Compliance Assessment
[evaluare succinta a conformitatii tehnice cu GDPR Art. 5, 25, 32]

## 6. Server-Side Data Inventory
[inventar complet: ce fisiere creeaza serverul pe disk, ce contin, cat dureaza]
```

---

## Criterii de succes

- [ ] Fiecare afirmatie din privacy policy verificata cu referinta la linia de cod specifica
- [ ] Tabel complet al tuturor datelor care parasesc device-ul
- [ ] Identificate toate fisierele create pe server (JSON persistence files)
- [ ] Confirmat ca push notification payload-ul NU contine text de mesaj
- [ ] Confirmat ca separarea userId/mailboxId/pushToken functioneaza corect
- [ ] Evaluat daca mailbox ID / public key constituie "date personale" sub GDPR
- [ ] Verificat package.json si Podfile pentru SDKs de analytics/tracking
- [ ] Raportat orice discrepanta intre ce spune privacy policy si ce face codul
- [ ] Rezultatul scris in `agent-runtime/outputs/privacy-security-audit.md`

---

## Dependente

- **Output-ul tau blocheaza release-engineer.** El nu poate scrie privacy policy-ul final pana nu primeste audit-ul tau.
- Dupa ce termini, actualizeaza `agent-runtime/state/status.md` cu statusul tau.
- Scrie un mesaj in `agent-runtime/messages/security-to-release.md` cu un rezumat al constatarilor critice.
