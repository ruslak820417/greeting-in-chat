# Audit Networking — QRChat v3.0.6
Data: 2026-03-21

## Scor Conectivitate: 8/10
## Scor Resilience: 8/10

---

## 1. WebRTC P2P (WebRTCManager.ts — 879 linii)

### Glare Handling (Perfect Negotiation): OK
- `makingOffer` Map — flag per peer, setat `true` la `createOffer`, `false` in `finally` dupa `setLocalDescription` (linii 152, 171)
- Polite/impolite: determinat prin comparatie `localUserId < remoteId` (linia 693)
- La primirea unui offer cu glare:
  - **Impolite**: ignora remote offer, pastreaza propriul (linia 701-704)
  - **Polite**: SDP rollback via `setLocalDescription({ type: 'rollback', sdp: '' })` + accepta remote offer (linii 710-713)
  - Fallback: daca rollback esueaza (react-native-webrtc vechi), close + recreate peer connection (linii 716-737)
- `signalingState` verificat inainte de `setRemoteDescription` (linia 698, 799)

### Chunk Transfer: OK
- `CHUNK_SIZE = 16 * 1024` (16KB) — sigur sub limita WebRTC data channel
- `ChunkBuffer` interface: `totalChunks`, `received` Map, `messageId`, `createdAt`
- Reassembly: chunks colectate in buffer, la primirea ultimului se reconstruieste mesajul (linii 605-627)
- `CHUNK_BUFFER_TTL = 5 * 60 * 1000` (5 min) — chunks expirate sterse automat
- `CHUNK_CLEANUP_INTERVAL = 60 * 1000` — cleanup la fiecare 60s
- Cleanup timer pornit la `initialize()`, oprit la `destroy()` (linii 101-102, 264-267)

### ICE Restart: OK
- `MAX_ICE_RESTARTS = 2` — limit pe incercari
- `attemptIceRestart()` — doar pentru data channel peers (nu call peers) (linia 534)
- ICE restart counter resetat la conexiune reusita (linia 479)
- Counter curatat la `disconnectPeer()` (linia 239)

### Cleanup (destroy): PARTIAL
- `destroy()` curata: peers (via `disconnectAll`), signaling handlers, chunk buffers, makingOffer, cleanup timer, localUserId
- **PROBLEMA**: `callTimeouts` Map NU e curatat in `destroy()` — timeout-urile pot declansa dupa distrugere
- **PROBLEMA**: `callStreams`, `onRemoteStreamCallback`, `onCallConnectedCallback`, `onCallDisconnectedCallback`, `iceCandidateQueues`, `pendingCallPeers` NU sunt curatate in `destroy()`
- Event handlers pe `RTCPeerConnection` (onicecandidate, etc.) sunt proprietati, nu addEventListener — se curata automat la `connection.close()`
- `setInterval` (chunkCleanupTimer) are `clearInterval` in `destroy()`

### Event Handler Leak Fix: OK
- La re-initialize, `removeSignalingHandlers()` apelat INAINTE de inregistrarea handler-elor noi (linia 83)
- Handler references stocate in `signalingHandlers[]` (linii 94-98)
- `off()` folosit pentru deregistrare (linia 273)
- Nu exista listener duplicati dupa cicluri multiple initialize/destroy

---

## 2. Signaling (WebSocket) — SignalingClient.ts (484 linii)

### Auth: OK
- Auth flow: primeste `auth-challenge` (nonce base64), semneaza cu Ed25519 via `KeyManager.signMessage()`, trimite `auth-response`
- Dupa `auth-success`: trimite `register` cu userId
- Fallback: daca `auth-challenge` nu vine in 3s, register direct (compatibilitate server vechi) (linii 142-149)
- Fallback: daca nu exista signing keys, register direct (linii 163-169)

### Heartbeat: OK
- `HEARTBEAT_INTERVAL = 30000` — ping la fiecare 30s
- `HEARTBEAT_TIMEOUT = 10000` — daca pong nu vine in 10s, reconectare
- `startHeartbeat()` apelat dupa `registered` (linia 399)
- `stopHeartbeat()` apelat la `disconnect()` si `ws.onclose` (linii 208, 231)
- Ambele timere (interval + timeout) curatate in `stopHeartbeat()`

### Reconnection: OK
- `maxReconnectAttempts = Infinity` — reconectare nelimitata
- Backoff: **exponential** — `Math.min(1000 * Math.pow(2, reconnectAttempts), 30000)` (linia 475)
- Backoff cap: **30 secunde**
- La reconectare: re-auth + re-register (prin `connect()` care reface tot flow-ul)
- `forceReconnect()` — pentru app foreground, resetare counter + reconectare imediata (linii 239-246)
- `hardReconnect()` — close + reconnect imediat, pt flush pending messages (linii 251-258)

### Relay Pinning: PARTIAL
- `PINNED_RELAY_DOMAINS` — Set cu domenii de incredere (doar Railway prod)
- `validateRelayUrl()` — verifica protocol (`wss://`) + domain in pinned set
- Dev: permite `ws://localhost` si `ws://192.168.*`
- **PROBLEMA**: Daca TOATE URL-urile sunt respinse de pinning, codul face fallback la URL-urile NEPINNED (linia 103: `pinnedUrls.length > 0 ? pinnedUrls : urls`). Relay pinning poate fi bypassed daca niciun relay pinned nu e disponibil. Ar trebui sa refuze conexiunea in loc de fallback.

### Send Queue: OK
- `MAX_QUEUE_SIZE = 500` — la depasire, se sterge cel mai vechi mesaj
- `QUEUE_MAX_AGE = 30000` (30s) — mesaje mai vechi discardate la flush
- Flush dupa `registered` (linia 398)
- **Nota**: Send queue NU e curatat explicit in `disconnect()`, dar `reconnectAttempts = Infinity` impiedica flush-ul

---

## 3. ICE / STUN / TURN (constants.ts)

### STUN Servers: OK
- 3 servere gratuite Google:
  - `stun:stun.l.google.com:19302`
  - `stun:stun1.l.google.com:19302`
  - `stun:stun2.l.google.com:19302`

### TURN Servers: OK
- **Sursa primara**: WebSocket (dupa autentificare) — `SignalingClient.getCachedTurnServers()`
- **Fallback HTTP**: `https://exciting-success-production-d272.up.railway.app/turn-credentials`
- Provider: Metered.ca — 4 configuratii:
  - `turn:a.relay.metered.ca:80` (UDP)
  - `turn:a.relay.metered.ca:80?transport=tcp` (TCP)
  - `turn:a.relay.metered.ca:443` (TLS)
  - `turns:a.relay.metered.ca:443?transport=tcp` (TURNS)
- Credentials protejate pe server (env vars `TURN_USERNAME`, `TURN_CREDENTIAL`)
- HTTP endpoint protejat cu `TURN_ACCESS_TOKEN` (linia 184 server)
- WebSocket endpoint necesita autentificare (linia 773 server)

### Fallback: OK
- Daca TURN nu e disponibil → doar STUN (cu warning explicit)
- P2P esueaza pe symmetric NAT fara TURN — documentat in cod

---

## 4. Peer Discovery

### DHT (DHTManager.ts — 246 linii): PARTIAL
- Kademlia parameters: `K = 8`, `BUCKET_COUNT = 32`
- `ANNOUNCE_INTERVAL = 5 * 60 * 1000` (5 min) — **definit dar NEFOLOSIT** (niciun setInterval)
- `PEER_TTL = 30 * 60 * 1000` (30 min)
- XOR distance: `distance * 16` (fix overflow — nu `<< 4`)
- Bucket index: `Math.min(Math.floor(Math.log2(dist)), BUCKET_COUNT - 1)`
- Persistent storage: AsyncStorage
- DHT e functional: initializare, addPeer, findClosest, routing exchange pe data channel
- **PROBLEMA**: `ANNOUNCE_INTERVAL` nu e folosit — DHT peers nu se re-anunta periodic. Peers expira dupa 30 min fara reannounce.

### Gossip (GossipProtocol.ts — 142 linii): PARTIAL
- `MAX_PEERS = 200` — limita peer table
- `PEER_TTL_MS = 7 * 24 * 60 * 60 * 1000` (7 zile)
- `GossipPeer`: peerId, publicKey, signPublicKey, relays, lastSeen
- `announceSelf()` — adauga propriul profil in peer table
- Gossip exchange: la deschiderea data channel, se trimit 50 peers + 5 relay URLs
- Persistent storage: AsyncStorage
- **VULNERABILITATE**: Nicio validare semnaturi Ed25519 pe gossip announcements — oricine poate injecta peers falsi
- **PROBLEMA**: Relay URLs primite prin gossip au validare minimala (`url.startsWith('ws')`) — dar SignalingClient are relay pinning, deci riscul e partial mitigat

### Bootstrap (BootstrapManager.ts — 82 linii): OK
- Default relays: dev (`ws://localhost`, `ws://192.168.*`) + prod (`wss://...railway.app`)
- `QUARANTINE_MS = 5 * 60 * 1000` (5 min quarantine dupa failure)
- `getAvailable()` — filtreaza quarantined, sorteaza by latency
- `getShuffled()` — random order (load balancing)
- `markSuccess()` — actualizeaza latency, resetare failCount
- `markFailed()` — seteaza lastFailed, incrementeaza failCount, latency = Infinity
- Community relays: placeholder in cod, niciun relay extern configurat inca
- **Nota**: BootstrapManager nu persista starea (in-memory only). La restart app, toate latency/fail info se pierd.

---

## 5. Call Flow

### Diagrama Call Flow

```
CALLER                          SERVER                        CALLEE
  |                               |                              |
  |-- startCall() --------------->|                              |
  |   createOffer(isCall=true)    |                              |
  |   + callTimestamp             |                              |
  |                               |-- relay offer (isCall) ----->|
  |                               |                              |
  |                               |           CallKitService.reportIncomingCall()
  |                               |           (iOS: afiseaza UI nativ CallKit)
  |                               |                              |
  |                               |                              |-- User Accept
  |                               |                              |   answerCall()
  |                               |<-- relay answer -------------|
  |                               |                              |
  |<-- answer --------------------|                              |
  |   setRemoteDescription()      |                              |
  |                               |                              |
  |<============= ICE candidates exchange ======================>|
  |                               |                              |
  |<=============== P2P Media Stream (audio/video) ==============>|
  |                               |                              |
  | [45s timeout daca nimeni      |                              |
  |  nu raspunde → auto-hangup]   |                              |
  |                               |                              |
  |-- endCall() ----------------->|                              |
  |   signal: call-ended          |-- relay call-ended --------->|
  |   300ms delay → close peer    |                              |
  |   stop media tracks           |                              |
```

### Call Flow Details:
- **Initiere**: `startCall()` → close existing peer → create new peer + add tracks → createOffer (isCall=true) → send via signaling
- **Primire**: Offer cu `isCall=true` marcheaza peer ca `pendingCallPeer` — ICE candidates queued pana la answer
- **Answer**: `answerCall()` → close existing peer → create new peer + add tracks → setRemoteDescription → drain ICE queue → createAnswer → send
- **CallKit**: `reportIncomingCall()` → UUID tracking → `activeCalls` Map → stale cleanup la 60s
- **Timeout**: 45s outgoing call timeout (auto-hangup daca nu raspunde nimeni)
- **End**: `endCall()` → notify remote via signaling → stop media tracks → 300ms delay → close peer connection
- **300ms delay logic**: Permite semnalului `call-ended` sa ajunga la remote INAINTE ca ICE disconnect sa declanseze `onCallDisconnected`

---

## 6. Memory Leak Risks

| # | Component | Risk | Mitigare |
|---|-----------|------|---------|
| 1 | WebRTCManager.callTimeouts | MEDIUM — timeouts nu sunt curatate in `destroy()` | `endCall()` le curata, dar daca `destroy()` e apelat fara `endCall()`, timeout-ul poate declansa pe un obiect distrus |
| 2 | WebRTCManager.callStreams | LOW — media streams nu sunt curatate in `destroy()` | `endCall()` opreste tracks, dar `destroy()` nu apeleaza `endCall()` pt fiecare call |
| 3 | WebRTCManager callback Maps | LOW — `onRemoteStreamCallback`, `onCallConnectedCallback`, `onCallDisconnectedCallback` nu sunt curatate in `destroy()` | Tin referinte la closures din CallScreen; curatate la `endCall()` |
| 4 | WebRTCManager.pendingCallPeers | LOW — Set nu e curatat in `destroy()` | Contine doar string IDs, impact minim |
| 5 | SignalingClient.sendQueue | LOW — nu e curatat la `disconnect()` | `reconnectAttempts = Infinity` previne flush-ul; GC curata la dealocare |
| 6 | BootstrapManager state | NEGLIGIBLE — in-memory only, nu persista | Se pierde la restart (feature, nu bug — dar pierde latency data) |

---

## 7. Offline/Online Resilience

### Pierdere conexiune WebSocket:
1. Heartbeat detecteaza in ~40s (30s interval + 10s timeout)
2. `ws.onclose` declanseaza reconectare automata
3. Backoff exponential: 1s → 2s → 4s → 8s → 16s → 30s (cap)
4. La reconectare: re-auth (auth-challenge) + re-register
5. Mesaje pending livrate imediat dupa register (staggered: 10/batch, 50ms delay)
6. `forceReconnect()` disponibil la app foreground — reconectare imediata
7. `hardReconnect()` — close + reconnect, flush server queue

### Pierdere conexiune P2P:
1. `onconnectionstatechange: 'failed'` detecteaza
2. ICE restart automat (max 2 incercari) — doar data channels, nu calls
3. Fallback pe signaling/server relay (mesaje criptate E2E prin WebSocket)

### Mesaje offline:
- Send queue client: max 500 mesaje, 30s TTL
- Server pending queue: max 1000 mesaje/user, 50MB/user, 48h expiry
- Server persista pending messages pe disk (JSON file, save la 60s + shutdown)

---

## 8. Server-Side Signaling (server/index.js — 937 linii)

### Securitate server:
- Auth challenge: Ed25519 nonce-based (nacl.sign.detached.verify)
- Sender spoofing fix: server inlocuieste `message.from` cu `userId` autentificat (linia 603)
- userId = publicKey enforcement (cand GRACE_PERIOD = false, linia 519)
- Rate limiting: token bucket (200 burst, 20/sec refill)
- Payload size cap: 1.5MB per mesaj WS
- Input validation: `validateMessage()`, `isValidRecipientId()`, `isBase64String()`
- Pending queue DoS protection: 1000 msg/user, 50MB/user
- Server-side WebSocket ping: la 10s, termina conexiuni moarte

### TURN credential delivery:
- WebSocket: dupa autentificare, `get-turn-credentials` → 4 TURN servers (linia 772)
- HTTP: protejat cu `TURN_ACCESS_TOKEN` query param (linia 184)

---

## 9. Vulnerabilitati Networking

| # | Problema | Severitate | Remediere |
|---|---------|------------|-----------|
| 1 | Gossip: nicio validare Ed25519 pe announcements | MEDIUM | Peers falsi pot fi injectati prin P2P data channel. Adauga verificare semnatura pe gossip payloads |
| 2 | Relay pinning bypass | MEDIUM | Daca toate relay-urile pinned sunt down, codul face fallback la URL-uri nepinned (linia 103 SignalingClient). Ar trebui sa refuse conexiunea, nu sa faca fallback |
| 3 | Gossip relay URL injection | LOW-MEDIUM | URLs primite prin gossip au validare minimala (`startsWith('ws')`). Relay pinning mitigheaza partial, dar BootstrapManager stocheaza URL-uri malitioase |
| 4 | DHT ANNOUNCE_INTERVAL nefolosit | LOW | Peers DHT expira dupa 30 min fara re-announce. Routing table se degradeaza in timp |
| 5 | destroy() incomplet pt call resources | LOW | callTimeouts, callStreams, callback Maps nu sunt curatate — potential leak la edge cases |
| 6 | BootstrapManager non-persistent | LOW | Latency data si fail counts se pierd la restart app. Nu e vulnerabilitate, dar afecteaza reconnect speed |

---

## 10. Recomandari

### Prioritate INALTA:
1. **Fix relay pinning bypass** — In `SignalingClient.connect()`, daca `pinnedUrls` e gol, refuza conexiunea in loc de fallback la urls nepinned. Codul curent (linia 103) anuleaza scopul relay pinning.
2. **Adauga validare semnatura pe gossip** — Fiecare gossip announcement sa fie semnat cu Ed25519. La `processGossipPayload()`, verifica semnatura inainte de a adauga peer-ul.

### Prioritate MEDIE:
3. **Fix destroy() complet** — Adauga in `destroy()`:
   ```typescript
   // Clean call resources
   this.callTimeouts.forEach(t => clearTimeout(t));
   this.callTimeouts.clear();
   this.callStreams.forEach(s => { try { s.getTracks().forEach(t => t.stop()); } catch(e){} });
   this.callStreams.clear();
   this.onRemoteStreamCallback.clear();
   this.onCallConnectedCallback.clear();
   this.onCallDisconnectedCallback.clear();
   this.iceCandidateQueues.clear();
   this.pendingCallPeers.clear();
   ```
4. **Implementeaza DHT re-announce** — Adauga `setInterval` cu `ANNOUNCE_INTERVAL` in `DHTManager.initialize()` pentru re-anuntare periodica.
5. **Valideaza gossip relay URLs** — In `processGossipPayload()`, verifica URL-urile prin `validateRelayUrl()` din SignalingClient inainte de `BootstrapManager.addRelay()`.

### Prioritate SCAZUTA:
6. **Persista BootstrapManager state** — Salveaza latency si fail data in AsyncStorage pentru reconnect mai rapid dupa restart.
7. **Curata sendQueue in disconnect()** — Adauga `this.sendQueue = []` in `SignalingClient.disconnect()` pentru cleanup explicit.

---

## Sumar

| Modul | Status | Nota |
|-------|--------|------|
| WebRTC P2P core | OK | Solid, glare handling complet |
| Perfect Negotiation | OK | Cu fallback pt react-native-webrtc vechi |
| Chunk transfer | OK | 16KB chunks, TTL, cleanup automat |
| ICE restart | OK | Max 2 retry, doar data channels |
| SignalingClient | OK | Auth, heartbeat, reconnect, queue |
| Heartbeat | OK | 30s ping, 10s timeout |
| Reconnection | OK | Exponential backoff, cap 30s |
| Relay pinning | PARTIAL | Bypass cand pinned relays = 0 |
| BootstrapManager | OK | Quarantine, latency sorting |
| DHT | PARTIAL | Functional dar fara re-announce |
| Gossip | PARTIAL | Functional dar fara validare semnatura |
| Call flow | OK | E2E complet, timeout 45s, CallKit |
| Memory cleanup | PARTIAL | destroy() incomplet pt call resources |
| Offline resilience | OK | Client queue + server queue + ICE restart |
| Server signaling | OK | Auth, rate limit, input validation |
