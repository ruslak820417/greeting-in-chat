# Prompt: Network Audit Complet — network-engineer

**Rol:** Esti network-engineer pentru QRChat, un messenger criptat end-to-end React Native.
**Proiect:** `/Users/ruslanconstantinovici/QRChat`
**Networking:** WebRTC (P2P), WebSocket signaling, DHT, Gossip Protocol

---

## SARCINA

Executa un audit complet al layer-ului de networking al QRChat. Verifica starea WebRTC, signaling, P2P data channels, heartbeat, call flow, glare handling, chunk transfer, si peer discovery. Scrie un raport cu starea conectivitatii.

---

## VERIFICARI (executa pe rand)

### 1. WebRTCManager — Core P2P

Citeste: `src/network/WebRTCManager.ts` (intreaga — 32366 bytes, ~930 linii)

Verifica:
- [ ] `initialize(userId)` — seteaza localUserId, incarca GossipProtocol + DHT
- [ ] Handler-e signaling: offer, answer, ice-candidate, call-ended — inregistrate corect
- [ ] `signalingHandlers[]` — referinte stocate pentru cleanup
- [ ] `destroy()` — curata handlers, peers, timers
- [ ] `removeSignalingHandlers()` — dezinregistreaza toate handler-ele stocate

#### Event Handler Leak Fix
- [ ] La re-initialize, se curata handler-ele vechi INAINTE de a inregistra altele noi
- [ ] Nu exista listener duplicati dupa multiple initialize/destroy cicluri

### 2. WebRTC Glare Handling — Perfect Negotiation

Citeste in WebRTCManager:
- [ ] `makingOffer` Map — flag per peer, setat la true la createOffer, false dupa setLocalDescription
- [ ] Polite/impolite peer: determinat cum? (comparatie userId? Initiator = cel cu userId mai mic?)
- [ ] La primirea unui offer:
  - Daca `makingOffer[peerId]` = true SI suntem "polite" → SDP rollback + accept offer
  - Daca `makingOffer[peerId]` = true SI suntem "impolite" → ignore offer
- [ ] SDP rollback implementat cu `setLocalDescription({ type: 'rollback' })`
- [ ] `RTCPeerConnection.signalingState` verificat inainte de setRemoteDescription

### 3. ICE / STUN / TURN Configuration

Citeste: `src/utils/constants.ts` (functia `getIceServers()`)

Verifica:
- [ ] STUN servers: `stun.l.google.com:19302` + `stun1` + `stun2` — 3 servere gratuite
- [ ] TURN servers — 2 surse:
  1. WebSocket cached: `SignalingClient.getCachedTurnServers()`
  2. HTTP fallback: `https://exciting-success-production-d272.up.railway.app/turn-credentials`
- [ ] TURN servers (Metered.ca): UDP :80, TCP :80, TLS :443, TURNS :443
- [ ] Fallback: daca TURN nu e disponibil, doar STUN (P2P esueaza pe symmetric NAT)
- [ ] TURN credentials protejate pe server (token-based)

### 4. Data Channel — File Transfer

In WebRTCManager, verifica chunk handling:

- [ ] `CHUNK_SIZE = 16 * 1024` (16KB — sub limita WebRTC)
- [ ] `ChunkBuffer` interface: totalChunks, received Map, messageId, createdAt
- [ ] Reassembly: chunks primite sunt puse in buffer, la primirea ultimului chunk se reconstruieste mesajul
- [ ] `CHUNK_BUFFER_TTL = 5 * 60 * 1000` (5 minute TTL)
- [ ] Cleanup timer: `CHUNK_CLEANUP_INTERVAL = 60 * 1000` (fiecare minut)
- [ ] Chunks expirate sunt sterse automat
- [ ] `MAX_ICE_RESTARTS = 2` — limit ICE restart attempts

### 5. SignalingClient — WebSocket Connection

Citeste: `src/network/SignalingClient.ts` (intreaga — 18384 bytes, ~550 linii)

Verifica:
- [ ] Conectare: `connect(userId)` — incearca relay-uri disponibile
- [ ] Auth flow: primeste `auth-challenge`, semneaza cu Ed25519, trimite `auth-response`
- [ ] Dupa auth: trimite `register` cu userId
- [ ] Pending messages: primite imediat dupa register
- [ ] Send queue: mesaje trimise in timpul reconectarii sunt bufferizate
  - `MAX_QUEUE_SIZE = 500`
  - `QUEUE_MAX_AGE = 30000` (30s — mesaje vechi sunt discard)

#### Heartbeat
- [ ] `HEARTBEAT_INTERVAL = 30000` (ping la fiecare 30s)
- [ ] `HEARTBEAT_TIMEOUT = 10000` (asteapta pong 10s)
- [ ] Daca pong nu vine in 10s → reconectare automata
- [ ] Heartbeat interval se curata la disconnect

#### Reconnection
- [ ] Reconnect attempts: `maxReconnectAttempts = Infinity`
- [ ] Backoff: exponential sau fix?
- [ ] Backoff cap: 30 secunde (conform PROJECT_STATUS)
- [ ] La reconectare, re-autentificare + re-register

#### Relay Pinning
- [ ] `PINNED_RELAY_DOMAINS` — Set cu domenii de incredere
- [ ] `validateRelayUrl()` — verifica protocol + domain
- [ ] Production: doar `wss://` pe domenii pinned
- [ ] Dev: permite `ws://localhost` si `ws://192.168.*`

### 6. BootstrapManager — Relay Pool

Citeste: `src/network/BootstrapManager.ts` (82 linii)

Verifica:
- [ ] Default relays: dev (ws local) + prod (wss Railway)
- [ ] `QUARANTINE_MS = 5 * 60 * 1000` (5 min quarantine dupa failure)
- [ ] `getAvailable()` — filtreaza quarantined, sorteaza by latency
- [ ] `getShuffled()` — random order (load balancing)
- [ ] `markSuccess(url, latencyMs)` — actualizeaza latency
- [ ] `markFailed(url)` — seteaza lastFailed, incrementeaza failCount
- [ ] Community relays: placeholder in cod, niciun relay extern configurat inca

### 7. DHTManager — Kademlia-lite

Citeste: `src/network/DHTManager.ts` (intreaga — 7064 bytes, ~200 linii)

Verifica:
- [ ] Kademlia parameters: `K = 8` (bucket size), `BUCKET_COUNT = 32`
- [ ] `ANNOUNCE_INTERVAL = 5 * 60 * 1000` (5 min)
- [ ] `PEER_TTL = 30 * 60 * 1000` (30 min)
- [ ] XOR distance: `distance * 16` (fix overflow — nu `<< 4`)
- [ ] Bucket index: `Math.floor(Math.log2(dist))`
- [ ] Persistent storage: AsyncStorage
- [ ] DHT este functional in productie? Sau doar in mod dev?

### 8. GossipProtocol — Peer Discovery

Citeste: `src/network/GossipProtocol.ts` (intreaga — 4477 bytes, ~135 linii)

Verifica:
- [ ] `MAX_PEERS = 200` — limita peer table
- [ ] `PEER_TTL_MS = 7 * 24 * 60 * 60 * 1000` (7 zile)
- [ ] `GossipPeer`: peerId, publicKey, signPublicKey, relays, lastSeen
- [ ] `announceSelf()` — adauga propriul profil in peer table
- [ ] Gossip exchange: la deschiderea unui data channel P2P, se schimba peer tables
- [ ] **LIPSA:** Validare semnaturi Ed25519 pe gossip announcements (oricine poate injecta peers falsi)
- [ ] Persistent storage: AsyncStorage

### 9. Call Flow — End-to-End

Analizeaza call flow-ul complet:

1. **Initiere apel:**
   - Caller: `WebRTCManager.initiateCall()` → createOffer → send via signaling
   - Server: relay offer la recipient
   - Recipient: primeste offer via signaling

2. **CallKit integration:**
   Citeste: `src/services/CallKitService.ts` (5367 bytes, ~170 linii)
   - [ ] `reportIncomingCall()` — raporteaza la CallKit iOS
   - [ ] `activeCalls` Map — multiple call tracking
   - [ ] `STALE_CALL_TIMEOUT = 60000` (60s cleanup)
   - [ ] `endCall()` — cleanup din Map + raporteaza la CallKit

3. **Call timeout:**
   - [ ] Outgoing call timeout: 45 secunde (auto-hangup)

4. **Call ended:**
   - [ ] Signal `call-ended` trimis prin signaling
   - [ ] Peer connection closed
   - [ ] Media streams stopped

### 10. Memory Leaks — Cleanup

Verifica in WebRTCManager:
- [ ] `destroy()` curata:
  - Toate peer connections (`peers` Map)
  - Chunk buffers
  - Cleanup timer
  - Signaling handlers
  - ICE restart counts
  - Making offer flags
- [ ] Fiecare `addEventListener` are un `removeEventListener` corespondent
- [ ] `setInterval` are `clearInterval` in destroy

Verifica in SignalingClient:
- [ ] `disconnect()` curata:
  - WebSocket connection
  - Heartbeat interval + timeout
  - Reconnect timeout
  - Send queue
- [ ] Re-connect nu lasa listeners vechi

### 11. Offline → Online Transition

Verifica:
- [ ] La pierderea conexiunii WS:
  - Heartbeat detecteaza (10s timeout)
  - Reconectare automata cu backoff
  - Re-auth + re-register
  - Pending messages primite
- [ ] La pierderea conexiunii P2P:
  - ICE restart (max 2 incercari)
  - Fallback pe relay (signaling/server)
- [ ] Mesaje trimise offline sunt bufferizate in send queue (max 500, 30s TTL)

---

## FISIERE DE CITIT (lista completa)

| Fisier | Linii | Ce verifici |
|--------|-------|------------|
| `src/network/WebRTCManager.ts` | ~930 | P2P core, glare, chunks |
| `src/network/SignalingClient.ts` | ~550 | WS client, heartbeat, reconnect |
| `src/network/BootstrapManager.ts` | 82 | Relay pool management |
| `src/network/DHTManager.ts` | ~200 | Kademlia DHT |
| `src/network/GossipProtocol.ts` | ~135 | Peer gossip discovery |
| `src/services/CallKitService.ts` | ~170 | iOS CallKit integration |
| `src/utils/constants.ts` | 89 | ICE/STUN/TURN config |
| `server/index.js` | 936 | Server-side signaling |

---

## COMANDA DE VERIFICARE

Ai terminat cand:
1. Ai verificat fiecare modul de networking individual
2. Ai documentat call flow-ul complet
3. Ai verificat glare handling (Perfect Negotiation)
4. Ai un inventar de memory leak risks
5. Ai un scor: conectivitate X/10, resilience Y/10

---

## UNDE SCRII RAPORTUL

Scrie rezultatul in:
```
/Users/ruslanconstantinovici/Projects/Agent Teams/agent-runtime/outputs/audit-network.md
```

Format:
```markdown
# Audit Networking — QRChat v4.0.0
Data: [data curenta]

## Scor Conectivitate: X/10
## Scor Resilience: X/10

## WebRTC P2P
- Glare handling: [OK/PARTIAL]
- Chunk transfer: [OK/PARTIAL]
- ICE restart: [OK/PARTIAL]
- Cleanup: [OK/PARTIAL]

## Signaling (WebSocket)
- Auth: [OK/PARTIAL]
- Heartbeat: [OK/PARTIAL]
- Reconnection: [OK/PARTIAL]
- Relay pinning: [OK/PARTIAL]

## Peer Discovery
- DHT: [FUNCTIONAL/PARTIAL/NEFUNCTIONAL]
- Gossip: [FUNCTIONAL/PARTIAL/NEFUNCTIONAL]
- Bootstrap: [OK/PARTIAL]

## Call Flow
[diagrama text]

## Memory Leak Risks
| # | Component | Risk | Mitigare |
|---|-----------|------|---------|

## Offline/Online Resilience
[detalii]

## Vulnerabilitati Networking
| # | Problema | Severitate | Remediere |
|---|---------|------------|-----------|

## Recomandari
1. ...
```
