# PROMPT: Backend Engineer — Fix Server Call Signaling

## Context

Citeste mai intai documentul de cercetare complet:
`/Users/ruslanconstantinovici/Projects/Agent Teams/agent-runtime/outputs/call-system-architecture.md`

Lucreaza pe codebase-ul QRChat: `/Users/ruslanconstantinovici/QRChat`

## Fisiere de modificat

- `server/index.js` — logica de relay a mesajelor signaling

---

## TASK 1: NU pune call offers in pending queue (CRITIC)

### Problema

Serverul trateaza toate mesajele signaling (`offer`, `answer`, `ice-candidate`, `call-ended`) identic — daca destinatarul e offline, le pune in `pendingMessages` queue. Cand destinatarul se reconecteaza, primeste TOATE mesajele din coada, inclusiv offer-uri de apel vechi.

Acest lucru cauzeaza:
1. **Ringtone overlap** — offer-uri duplicate ajung la client, declansand multiple instante de ringtone
2. **Apeluri fantoma** — utilizatorul primeste un apel care nu mai exista (apelantul a renuntat demult)
3. **ICE candidates orfane** — candidates pentru un apel care s-a incheiat se aplica pe peer connection gresita

### Ce trebuie facut

In `server/index.js`, in case-ul `'offer'` / `'answer'` / `'ice-candidate'` / `'call-ended'` (in jurul liniei 578-628), modifica logica de queueing:

**INAINTE (codul curent):**
```javascript
case 'offer':
case 'answer':
case 'ice-candidate':
case 'call-ended': {
  if (!isValidRecipientId(message.to)) { ... break; }
  const targetClient = clients.get(message.to);
  if (targetClient && targetClient.readyState === WebSocket.OPEN) {
    // Online — relay direct
    targetClient.send(JSON.stringify({ type: message.type, from: userId, payload: message.payload }));
  } else {
    // Offline — pune in coada (PROBLEMA!)
    enqueuePending(message.to, { ... });
    // + push notification pentru offers
  }
  break;
}
```

**DUPA (codul corectat):**
```javascript
case 'offer':
case 'answer':
case 'ice-candidate':
case 'call-ended': {
  if (!isValidRecipientId(message.to)) {
    ws.send(JSON.stringify({ type: 'error', message: 'Invalid recipient' }));
    break;
  }
  const targetClient = clients.get(message.to);

  if (targetClient && targetClient.readyState === WebSocket.OPEN) {
    // Destinatarul e online — relay direct
    targetClient.send(JSON.stringify({
      type: message.type,
      from: userId,
      payload: message.payload,
    }));
    console.log(`[->] ${message.type}: ${userId.substring(0, 8)}... -> ${message.to.substring(0, 8)}...`);
  } else {
    // Destinatarul e offline
    const isCallSignaling = message.payload?.isCall ||
                            message.type === 'call-ended' ||
                            message.type === 'answer';

    if (isCallSignaling) {
      // CALL SIGNALING: NU pune in pending queue!
      // Apelurile sunt actiuni in timp real — daca user-ul e offline, apelul e pierdut.
      console.log(`[X] ${message.type} dropped (user offline): ${userId.substring(0, 8)}... -> ${message.to.substring(0, 8)}...`);

      // Notifica apelantul ca destinatarul e offline
      ws.send(JSON.stringify({
        type: 'user-offline',
        to: message.to,
        originalType: message.type,
      }));

      // Trimite push notification DOAR pentru call offers
      // (receptorul va vedea missed call notification)
      if (message.type === 'offer' && message.payload?.isCall) {
        sendPush(message.to, userId, {
          callerName: message.callerName || '',
          isVideo: message.isVideo || false,
          offer: typeof message.payload === 'string'
            ? message.payload
            : JSON.stringify(message.payload || {}),
        }).catch(err => {
          console.error('[Push] Failed to send call push:', err.message);
        });
      }
    } else if (message.type === 'ice-candidate' && !message.payload?.isCall) {
      // ICE candidates pentru DATA CHANNEL (non-call): pune in coada
      // Acestea sunt pentru reconectarea data channel-ului de chat
      const queued = enqueuePending(message.to, {
        timestamp: Date.now(),
        data: { type: message.type, from: userId, payload: message.payload },
      });
      if (queued) {
        console.log(`[Q] Queued ${message.type} for ${message.to.substring(0, 8)}...`);
      }
      ws.send(JSON.stringify({ type: 'queued', originalType: message.type, to: message.to }));
    } else {
      // DATA CHANNEL offers (non-call): pune in coada normal
      const queued = enqueuePending(message.to, {
        timestamp: Date.now(),
        data: { type: message.type, from: userId, payload: message.payload },
      });
      if (queued) {
        console.log(`[Q] Queued ${message.type} for ${message.to.substring(0, 8)}...`);
      }
      ws.send(JSON.stringify({ type: 'queued', originalType: message.type, to: message.to }));
    }
  }
  break;
}
```

### Logica de decizie simplificata:

```
Mesaj signaling primit de server:
  |
  +-- Destinatar ONLINE? --> Relay direct (fara schimbari)
  |
  +-- Destinatar OFFLINE?
       |
       +-- Este call signaling? (isCall, call-ended, answer)
       |    --> NU pune in coada
       |    --> Trimite 'user-offline' la expeditor
       |    --> Daca e call offer: trimite push notification
       |
       +-- Este data channel signaling? (offer/ice fara isCall)
            --> Pune in coada normal (pending queue)
```

---

## TASK 2: Gestioneaza `user-offline` pe client (network-engineer dependency)

Cand serverul trimite `user-offline`, clientul trebuie sa stie ca apelul nu poate fi conectat. Adauga tipul `user-offline` in `VALID_MESSAGE_TYPES`:

```javascript
const VALID_MESSAGE_TYPES = new Set([
  'auth-response', 'register', 'register-push-token',
  'offer', 'answer', 'ice-candidate', 'call-ended',
  'ping-user', 'encrypted-message', 'delivery-receipt', 'read-receipt',
  'get-turn-credentials', 'typing',
  'contact-request', 'contact-accepted', 'contact-rejected',
  'ping',
  'user-offline',  // <-- ADAUGA ACEST TIP
]);
```

**NOTA:** `user-offline` e trimis de SERVER catre client, nu de client catre server. Dar il adaugam in VALID_MESSAGE_TYPES pentru consistenta (serverul trimite mesaje de tipuri validate).

**DEPENDENCY:** Spune network-engineer-ului sa adauge handler in `SignalingClient.ts` sau `WebRTCManager.ts`:
```javascript
SignalingClient.on('user-offline', (message) => {
  // Daca era un apel outgoing, opreste-l si afiseaza "User offline"
  if (message.originalType === 'offer') {
    // Emit event pe EventBus sau direct in CallScreen
    EventBus.emit('call-user-offline', { contactId: message.to });
  }
});
```

---

## TASK 3: Rate limiting specific pentru call signaling (optional, prioritate mica)

### Problema
Call offers sunt mesaje mari (contin SDP care poate fi 2-5KB). Un atacator ar putea trimite call offers false la rate mare.

### Ce trebuie facut (daca timpul permite)

Adauga un rate limiter specific pentru call offers:

```javascript
// Dupa linia cu ws.rateBucket
ws.callOfferCount = 0;
ws.lastCallOfferReset = Date.now();
const MAX_CALL_OFFERS_PER_MINUTE = 10;

// In case 'offer', inainte de relay:
if (message.payload?.isCall) {
  const now = Date.now();
  if (now - ws.lastCallOfferReset > 60000) {
    ws.callOfferCount = 0;
    ws.lastCallOfferReset = now;
  }
  ws.callOfferCount++;
  if (ws.callOfferCount > MAX_CALL_OFFERS_PER_MINUTE) {
    ws.send(JSON.stringify({ type: 'rate-limited', reason: 'Too many call offers' }));
    break;
  }
}
```

---

## Ordinea de executie

1. **TASK 1** — Fix critic: opreste queueing call offers (cauza principala a overlap-ului)
2. **TASK 2** — Suport `user-offline` pentru feedback la apelant
3. **TASK 3** — Rate limiting optional

## Dupa fiecare modificare

- Testeaza local cu `node server/index.js`
- Verifica ca offer-urile de apel NU se pun in pending queue
- Verifica ca offer-urile de data channel (non-call) SE pun in coada
- Verifica ca push notification se trimite cand receptorul e offline
- Deploy cu `deploy.sh` (conform regulii: NICIODATA `railway up` direct)
- Verifica pe Railway ca serverul ruleaza corect
