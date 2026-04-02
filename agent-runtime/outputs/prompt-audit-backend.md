# Prompt: Backend Audit Complet — backend-engineer

**Rol:** Esti backend-engineer pentru QRChat, un messenger criptat end-to-end.
**Proiect:** `/Users/ruslanconstantinovici/QRChat`
**Server:** Node.js (Express + WebSocket) — deploy pe Railway
**Server LIVE:** https://exciting-success-production-d272.up.railway.app

---

## SARCINA

Executa un audit complet al serverului QRChat. Verifica starea fiecarui endpoint, WebSocket handling, persistenta, rate limiting, si conectivitatea live. Scrie un raport cu ce merge, ce e partial, si ce lipseste.

---

## VERIFICARI (executa pe rand)

### 1. Server Health — Test Live

Executa aceste comenzi si documenta raspunsurile:

```bash
# Health check
curl -s https://exciting-success-production-d272.up.railway.app/ | python3 -m json.tool

# Health endpoint
curl -s https://exciting-success-production-d272.up.railway.app/health | python3 -m json.tool

# Privacy Policy (HTML)
curl -s -o /dev/null -w "%{http_code}" https://exciting-success-production-d272.up.railway.app/privacy

# TURN credentials (fara token — ar trebui sa returneze 403 sau 503)
curl -s https://exciting-success-production-d272.up.railway.app/turn-credentials | python3 -m json.tool
```

Verifica:
- [ ] Root endpoint raspunde cu `{ service: "QRChat Signaling Server", status: "running" }`
- [ ] Health endpoint raspunde cu `{ status: "ok", clients: N }`
- [ ] Health endpoint NU expune informatii sensibile (uptime, queue sizes, etc.)
- [ ] Privacy endpoint returneaza 200 cu HTML complet
- [ ] TURN credentials sunt protejate (403 fara token, sau 503 daca neconfigurat)

### 2. HTTP Endpoints — Inventar Complet

Citeste: `server/index.js` (liniile 168-368)

Inventar toate endpoint-urile HTTP si verifica statusul:

| Endpoint | Metoda | Scop | Protectie |
|----------|--------|------|-----------|
| `/` | GET | Health check | Public |
| `/health` | GET | Status + client count | Public |
| `/turn-credentials` | GET | TURN servers | Token-based |
| `/redeem-promo` | POST | Redeem promo code | Validare body |
| `/check-license` | POST | Check device license | Validare body |
| `/admin/generate-promo` | POST | Generate promo | Admin secret + rate limit |
| `/admin/change-password` | POST | Change admin pw | Admin secret + rate limit |
| `/admin/list-promos` | POST | List promo codes | Admin secret + rate limit |
| `/report` | POST | Report user/content | Validare body |
| `/privacy` | GET | Privacy Policy HTML | Public |

- [ ] Fiecare endpoint are validare de input
- [ ] Admin endpoints au rate limiting (5/minut per IP)
- [ ] Admin rate limit cleanup la fiecare 5 minute

### 3. WebSocket Message Types

Citeste: `server/index.js` (liniile 416-sfarsit)

Inventar TOATE tipurile de mesaje WS:

| Tip mesaj | Directie | Functie | Auth required? |
|-----------|----------|---------|----------------|
| `auth-challenge` | S->C | Trimite nonce | N/A |
| `auth-response` | C->S | Ed25519 signature | No (e auth) |
| `register` | C->S | Inregistrare userId | Da |
| `register-push-token` | C->S | Push token anon | Da |
| `offer/answer/ice-candidate` | C->S->C | WebRTC signaling | Da |
| `call-ended` | C->S->C | End call signal | Da |
| `encrypted-message` | C->S->C | Chat message (relay) | Da |
| `delivery-receipt` | C->S->C | Delivery confirm | Da |
| `read-receipt` | C->S->C | Read confirm | Da |
| `typing` | C->S->C | Typing indicator | Da |
| `contact-request` | C->S->C | Contact request | Da |
| `contact-accepted` | C->S->C | Accept contact | Da |
| `contact-rejected` | C->S->C | Reject contact | Da |
| `ping-user` | C->S->C | Check online | Da |
| `get-turn-credentials` | C->S | Get TURN via WS | Da |
| `ping` | C->S | Heartbeat | Da |

- [ ] Validare globala: `validateMessage()` cu whitelist `VALID_MESSAGE_TYPES`
- [ ] Auth gate: toate tipurile (exceptie `auth-response`) necesita `ws.authenticated`
- [ ] `from: userId` fortat de server pe toate relay-urile

### 4. Pending Messages — Persistenta

Citeste: `server/index.js` (liniile 22-76, 374-395)

Verifica:
- [ ] `PENDING_FILE` — salvat la `DATA_DIR/qrchat_pending_messages.json`
- [ ] `DATA_DIR` = `RAILWAY_VOLUME_MOUNT_PATH` sau `/tmp`
- [ ] Auto-save la fiecare 60s daca dirty
- [ ] Graceful shutdown: save pe SIGTERM si SIGINT
- [ ] Message expiry: 48h TTL
- [ ] Cleanup periodic la fiecare ora
- [ ] DoS protection: max 1000 mesaje / 50MB per user
- [ ] Staggered delivery: 10 mesaje pe batch cu 50ms delay

**ATENTIE:** Daca `RAILWAY_VOLUME_MOUNT_PATH` nu e setat, `/tmp` se sterge la restart Railway. Verifica daca volume-ul Railway e configurat.

### 5. Push Notifications (APNs)

Citeste: `server/push.js` (tot fisierul — ~200 linii)

Verifica:
- [ ] APNs provider initializat cu `@parse/node-apn`
- [ ] Necesita env vars: `APNS_KEY_ID`, `APNS_TEAM_ID`, `APNS_KEY_PATH`
- [ ] Daca env vars lipsesc, push-uri sunt skip-uite cu warning (nu crash)
- [ ] Push tokens persistati in fisier JSON
- [ ] Throttle: max 1 push per 30s per mailbox
- [ ] Push payload: content-available=1, zero continut de mesaj

**Status curent:** APNs NECONFIGURAT pe Railway (lipsesc APNS_KEY_ID, APNS_TEAM_ID)

### 6. Licensing System

Citeste: `server/licensing.js` (tot fisierul — ~230 linii)

Verifica:
- [ ] Admin secret incarcat din env var (fara hardcoded fallback)
- [ ] Promo codes format: QRCHAT-XXXX-XXXX-XXXX
- [ ] Persistent storage pe disc (fisiere JSON)
- [ ] Code redemption: one-time use, linked to deviceId
- [ ] Licensed devices check: O(1) lookup

### 7. Rate Limiting WebSocket

Verifica in `server/index.js`:
- [ ] Token bucket per conexiune: 200 burst, 20 tokens/s refill
- [ ] Payload size cap: 1.5MB per mesaj
- [ ] Rate limited response: `{ type: 'rate-limited', retryAfter: N }`
- [ ] Payload too large response: `{ type: 'payload-too-large', maxSize: N }`

### 8. Railway Deploy Config

Citeste: `server/railway.json`

Verifica:
- [ ] Builder: NIXPACKS
- [ ] Start command: `node index.js`
- [ ] Restart policy: ON_FAILURE, max 10 retries
- [ ] `package.json` server: verifica dependentele

```bash
cat /Users/ruslanconstantinovici/QRChat/server/package.json
```

### 9. Conexiune WebSocket Test

Daca posibil, testeaza conexiunea WS:
```bash
# Test basic WebSocket (daca ai wscat instalat)
# npx wscat -c wss://exciting-success-production-d272.up.railway.app
# Ar trebui sa primesti: { type: "auth-challenge", nonce: "..." }
```

### 10. Probleme Cunoscute & Lipsuri

Evalueaza si documenteaza:
- [ ] APNs neconfigurat — push notifications nu merg
- [ ] Persistent storage — Railway volume configurat? Sau datele se pierd la restart?
- [ ] TURN credentials — sunt env vars setate pe Railway?
- [ ] Server logging — loguri sensibile? (IP, userId prefix OK, nu content)
- [ ] Redis vs JSON files — scalabilitate

---

## FISIERE DE CITIT (lista completa)

| Fisier | Ce verifici |
|--------|------------|
| `server/index.js` | Tot serverul (936 linii) |
| `server/push.js` | Push notifications APNs |
| `server/licensing.js` | Licensing/promo system |
| `server/package.json` | Dependente server |
| `server/railway.json` | Deploy config |
| `server/.gitignore` | Ce nu e comis |

---

## COMANDA DE VERIFICARE

Ai terminat cand:
1. Ai testat LIVE toate endpoint-urile HTTP (cu curl)
2. Ai inventariat toate mesajele WS
3. Ai un scor: X/10 endpoint-uri functionale
4. Ai o lista de "Missing" si "Risks"

---

## UNDE SCRII RAPORTUL

Scrie rezultatul in:
```
/Users/ruslanconstantinovici/Projects/Agent Teams/agent-runtime/outputs/audit-backend.md
```

Format:
```markdown
# Audit Backend — QRChat Server v4.0.0
Data: [data curenta]

## Server Status: [LIVE / DOWN / PARTIAL]

## Endpoints HTTP
| Endpoint | Status | Response | Notes |
|----------|--------|----------|-------|

## WebSocket Messages
| Type | Status | Notes |
|------|--------|-------|

## Persistent Storage: [OK / RISC]
[detalii]

## Push Notifications: [CONFIGURAT / NECONFIGURAT]
[detalii]

## Lipsuri & Riscuri
| # | Severitate | Descriere | Impact |
|---|-----------|-----------|--------|

## Recomandari (prioritizate)
1. ...
```
