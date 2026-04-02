# Audit Backend — QRChat Server v1.0.0
Data: 2026-03-21

Auditor: backend-engineer
Server LIVE: https://exciting-success-production-d272.up.railway.app
Codebase: `/Users/ruslanconstantinovici/QRChat/server/`
Fisiere auditate: `index.js` (937 linii), `push.js` (209 linii), `licensing.js` (263 linii), `package.json`, `railway.json`, `.gitignore`

---

## Server Status: LIVE

Serverul raspunde corect pe toate endpoint-urile. WebSocket accepta conexiuni si trimite auth-challenge. Zero clienti conectati la momentul testului.

---

## Endpoints HTTP — Test LIVE

| # | Endpoint | Metoda | Status | Response | Protectie | Notes |
|---|----------|--------|--------|----------|-----------|-------|
| 1 | `/` | GET | ✅ OK | `{ service: "QRChat Signaling Server", status: "running" }` | Public | Corect, minimal |
| 2 | `/health` | GET | ✅ OK | `{ status: "ok", clients: 0 }` | Public | NU expune info sensibila |
| 3 | `/turn-credentials` | GET | ⚠️ EXPUS | Returneaza credentiale TURN fara token | Token-based (BYPASS) | **CRITICAL — vezi Risc #1** |
| 4 | `/redeem-promo` | POST | ✅ OK | 400 la body gol: `Missing code or deviceId` | Validare body | Corect |
| 5 | `/check-license` | POST | ✅ OK | 400 la body gol: `Missing deviceId` | Validare body | Corect |
| 6 | `/admin/generate-promo` | POST | ✅ OK | 403: `Invalid admin secret` | Admin secret + rate limit | Corect |
| 7 | `/admin/change-password` | POST | ✅ OK | 403: `Invalid current password` | Admin secret + rate limit | Corect |
| 8 | `/admin/list-promos` | POST | ✅ OK | 403: `Invalid admin secret` | Admin secret + rate limit | Corect |
| 9 | `/report` | POST | ✅ OK | 400: `Missing required fields` | Validare body | Fara rate limit |
| 10 | `/privacy` | GET | ✅ OK | 200 cu HTML complet | Public | Privacy Policy ok |

**Scor: 9/10 endpoint-uri complet functionale. 1 endpoint cu problema de securitate (TURN credentials).**

---

## WebSocket — Test LIVE

**Conexiune:** ✅ Reusita
**Auth-challenge:** ✅ Primit imediat: `{ type: "auth-challenge", nonce: "QxKzNsb4t5Z/..." }`
**Auth gate:** ✅ Mesajele fara autentificare sunt respinse cu `Authentication required`
**GRACE_PERIOD:** ✅ Dezactivat pe productie (mesajele neautentificate sunt blocate)

### Inventar Mesaje WebSocket

| # | Tip mesaj | Directie | Functie | Auth? | Validare input | Offline queue |
|---|-----------|----------|---------|-------|---------------|---------------|
| 1 | `auth-challenge` | S→C | Trimite nonce Ed25519 | N/A | N/A | N/A |
| 2 | `auth-response` | C→S | Verificare semnatura | Nu (e auth) | ✅ isBase64String | N/A |
| 3 | `register` | C→S | Inregistrare userId | Da | ✅ isNonEmptyString + publicKey match | N/A |
| 4 | `register-push-token` | C→S | Push token anonim | Da | ✅ mailboxId, token, platform whitelist | N/A |
| 5 | `offer` | C→S→C | WebRTC offer | Da | ✅ isValidRecipientId | ✅ Da |
| 6 | `answer` | C→S→C | WebRTC answer | Da | ✅ isValidRecipientId | ✅ Da |
| 7 | `ice-candidate` | C→S→C | ICE candidate | Da | ✅ isValidRecipientId | ✅ Da |
| 8 | `call-ended` | C→S→C | End call signal | Da | ✅ isValidRecipientId | ✅ Da |
| 9 | `encrypted-message` | C→S→C | Chat mesaj E2E | Da | ✅ to, payload, messageId | ✅ Da + push |
| 10 | `delivery-receipt` | C→S→C | Delivery confirm | Da | ✅ to, messageId, deliveredAt | ✅ Da |
| 11 | `read-receipt` | C→S→C | Read confirm | Da | ✅ to, messageIds array (max 100) | ✅ Da |
| 12 | `typing` | C→S→C | Typing indicator | Da | ✅ to, isTyping boolean | ❌ Nu (corect) |
| 13 | `contact-request` | C→S→C | Contact request | Da | ✅ isValidRecipientId | ✅ Da |
| 14 | `contact-accepted` | C→S→C | Accept contact | Da | ✅ isValidRecipientId | ✅ Da |
| 15 | `contact-rejected` | C→S→C | Reject contact | Da | ✅ isValidRecipientId | ✅ Da |
| 16 | `ping-user` | C→S | Check online status | Da | ✅ targetUserId | N/A |
| 17 | `get-turn-credentials` | C→S | Get TURN via WS | Da | ✅ Auth check | N/A |
| 18 | `ping` | C→S | Heartbeat | Da | ✅ (implicit) | N/A |

**Validare globala:**
- ✅ `validateMessage()` cu whitelist `VALID_MESSAGE_TYPES` (18 tipuri)
- ✅ Auth gate: toate tipurile (exceptie `auth-response`) necesita `ws.authenticated`
- ✅ `from: userId` fortat de server pe TOATE relay-urile (anti-spoofing)
- ✅ Mesajele necunoscute sunt loggate si ignorate

---

## Persistent Storage: RISC MEDIU

| Aspect | Status | Detalii |
|--------|--------|---------|
| `PENDING_FILE` | ✅ | `DATA_DIR/qrchat_pending_messages.json` |
| `DATA_DIR` | ⚠️ | `RAILWAY_VOLUME_MOUNT_PATH` sau `/tmp` |
| Auto-save periodic | ✅ | La fiecare 60s daca dirty |
| Graceful shutdown | ✅ | SIGTERM + SIGINT → saveToDisk + exit |
| Message expiry TTL | ✅ | 48h — verificat la load + periodic cleanup |
| Cleanup periodic | ✅ | La fiecare ora |
| DoS protection (count) | ✅ | Max 1000 mesaje per user |
| DoS protection (size) | ✅ | Max 50MB per user |
| Staggered delivery | ✅ | 10 mesaje/batch, 50ms delay |

**RISC:** Daca `RAILWAY_VOLUME_MOUNT_PATH` nu e setat pe Railway, toate datele sunt in `/tmp` si se pierd la fiecare restart/deploy. Afecteaza: pending messages, push tokens, promo codes, licensed devices, reports, admin secret.

---

## Push Notifications: NECONFIGURAT

| Aspect | Status | Detalii |
|--------|--------|---------|
| APNs provider | ❌ | Necesita `APNS_KEY_ID` + `APNS_TEAM_ID` (env vars) |
| Graceful degradation | ✅ | Skip cu warning, nu crash |
| Push tokens persistence | ✅ | JSON file cu auto-save |
| Throttle | ✅ | Max 1 push per 30s per mailbox |
| Payload security | ✅ | ZERO continut mesaj — doar `{ e: 1, s: senderUserId }` |
| Invalid token cleanup | ✅ | BadDeviceToken/Unregistered → auto-remove |
| Privacy (two-map design) | ✅ | userId→mailboxId si mailboxId→token separate |

**Impact:** Utilizatorii NU primesc notificari cand primesc mesaje offline. Mesajele vor fi livrate doar la urmatoarea conectare.

---

## Licensing System: OK

| Aspect | Status | Detalii |
|--------|--------|---------|
| Admin secret | ✅ | Din env var `QRCHAT_ADMIN_SECRET` (fara fallback hardcodat) |
| Admin secret persistence | ✅ | Se salveaza pe disc dupa change-password |
| Promo code format | ✅ | `QRCHAT-XXXX-XXXX-XXXX` (fara I,O,0,1) |
| Persistent storage | ✅ | Fisiere JSON pe disc |
| Code redemption | ✅ | One-time use, linked to deviceId |
| Reactivare pe acelasi device | ✅ | Permite re-redeem |
| Licensed devices lookup | ✅ | O(1) via Map.has() |
| Code signature | ✅ | HMAC-SHA256 cu admin secret |
| Timing-safe compare | ✅ | `crypto.timingSafeEqual` la admin secret + code verify |
| Admin rate limiting | ✅ | 5 incercari/minut per IP |

**Problema minora:** `changeAdminSecret` accepta parole de minim 4 caractere — prea scurt.

---

## Rate Limiting: OK

| Aspect | Status | Detalii |
|--------|--------|---------|
| Token bucket per conexiune | ✅ | 200 burst, 20 tokens/s refill |
| Payload size cap | ✅ | 1.5MB per mesaj WS |
| Rate limited response | ✅ | `{ type: 'rate-limited', retryAfter: N }` |
| Payload too large response | ✅ | `{ type: 'payload-too-large', maxSize: N }` |
| Admin endpoint rate limit | ✅ | 5/minut per IP cu cleanup la 5 min |
| WS ping keepalive | ✅ | 10s interval, termina conexiuni moarte |

---

## Railway Deploy Config: OK

| Aspect | Status | Detalii |
|--------|--------|---------|
| Builder | ✅ | NIXPACKS |
| Start command | ✅ | `node index.js` |
| Restart policy | ✅ | ON_FAILURE, max 10 retries |

### Dependente server (package.json)

| Package | Versiune | Scop |
|---------|----------|------|
| `ws` | ^8.16.0 | WebSocket server |
| `express` | ^4.18.2 | HTTP server |
| `tweetnacl` | ^1.0.3 | Ed25519 auth |
| `tweetnacl-util` | ^0.15.1 | Base64 utils |
| `@parse/node-apn` | ^7.1.0 | APNs push notifications |

**Nota:** 5 dependente totale — suprafata de atac minima, excelent.

---

## Lipsuri & Riscuri

| # | Severitate | Descriere | Impact | Linie cod |
|---|-----------|-----------|--------|-----------|
| 1 | **CRITICAL** | TURN credentials expuse public — `TURN_ACCESS_TOKEN` nu e setat pe Railway, deci guard-ul `if (TURN_ACCESS_TOKEN && ...)` e bypass-at complet. Oricine poate face GET `/turn-credentials` si primeste username+credential Metered.ca | Abuz TURN relay, costuri Metered.ca, potential relay pentru trafic malitios | `index.js:184` |
| 2 | **HIGH** | APNs neconfigurat — lipsesc `APNS_KEY_ID` si `APNS_TEAM_ID` pe Railway | Utilizatorii nu primesc notificari push. Mesajele offline se livreaza doar la reconectare | `push.js:27` |
| 3 | **HIGH** | Persistent storage — daca `RAILWAY_VOLUME_MOUNT_PATH` nu e setat, datele sunt in `/tmp` si se pierd la restart | Pierdere: pending messages, promo codes, licensed devices, push tokens, reports, admin secret | `index.js:22` |
| 4 | **MEDIUM** | `/report` endpoint fara rate limiting — un atacator poate trimite mii de reports si umple discul | Disk fill, potential DoS | `index.js:268` |
| 5 | **MEDIUM** | Reports file append fara limita — citeste tot fisierul, il parseaza, adauga report, scrie tot inapoi. La mii de reports devine O(n) | Performance degradation + potential OOM | `index.js:282-294` |
| 6 | **LOW** | Admin password minimum 4 caractere — prea scurt pentru productie | Parole slabe posibile | `licensing.js:240` |
| 7 | **LOW** | `isDeviceLicensed()` — dupa Map check face si un loop prin toate promoCodes. Redundant daca Map-ul e complet | Performance minora (nu e critic cu numarul actual de coduri) | `licensing.js:203-210` |
| 8 | **INFO** | Server version in package.json e "1.0.0" dar codul are features de v4.0+ (auth, rate limit, licensing) | Inconsistenta versionare | `package.json:3` |

---

## Recomandari (prioritizate)

### P0 — Imediat

1. **Seteaza `TURN_ACCESS_TOKEN` pe Railway** — genereaza un token random si adauga-l ca env var. Fara asta, credentialele TURN sunt publice.
   ```bash
   # Pe Railway: Settings → Variables → Add
   TURN_ACCESS_TOKEN=<random-32-char-string>
   ```

2. **Verifica `RAILWAY_VOLUME_MOUNT_PATH`** — asigura-te ca un volume persistent e atasat pe Railway. Daca nu, TOATE datele (promo codes, licenses, pending messages) se pierd la fiecare deploy.

### P1 — Curand

3. **Configureaza APNs** — adauga `APNS_KEY_ID`, `APNS_TEAM_ID`, si upload AuthKey.p8 pe Railway. Fara push, utilizatorii nu stiu ca au mesaje noi.

4. **Adauga rate limiting pe `/report`** — reutilizeaza pattern-ul de admin rate limiting (dar cu limita mai mare, ex: 10/minut per IP).

5. **Fix reports file performance** — limiteaza numarul de reports in memorie (ex: max 10000, FIFO) sau foloseste append-only file in loc de citire+scriere JSON complet.

### P2 — Nice to have

6. **Creste minimum admin password** — de la 4 la minim 12 caractere.

7. **Simplifica `isDeviceLicensed`** — `licensedDevices.has(deviceId)` ar trebui sa fie suficient daca Map-ul e tinut in sync corect. Loop-ul prin promoCodes e redundant.

8. **Actualizeaza versiunea in package.json** — "1.0.0" → "4.0.0" sau ce versiune curenta e.

---

## Sumar

| Categorie | Scor | Detalii |
|-----------|------|---------|
| Server Health | ✅ 10/10 | LIVE, raspunde pe toate endpoint-urile |
| HTTP Endpoints | ✅ 9/10 | Toate functionale, 1 expus fara auth |
| WebSocket | ✅ 10/10 | Auth challenge, auth gate, validare, anti-spoofing |
| Persistent Storage | ⚠️ 7/10 | Implementare buna, dar risc daca volume-ul Railway lipseste |
| Push Notifications | ❌ 3/10 | Cod bun, dar neconfigurat pe Railway |
| Licensing | ✅ 9/10 | Complet, cu minori issues |
| Rate Limiting | ✅ 10/10 | Token bucket + admin rate limit + payload cap |
| Deploy Config | ✅ 10/10 | Railway config corect |
| **TOTAL** | **8.5/10** | Server solid, 1 vulnerabilitate critica (TURN), APNs neconfigurat |
