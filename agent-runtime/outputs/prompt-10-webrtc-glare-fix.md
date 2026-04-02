# Prompt: Fix WebRTC Glare — Perfect Negotiation Pattern

**Agent:** network-engineer
**Fisier principal:** `/Users/ruslanconstantinovici/QRChat/src/network/WebRTCManager.ts`
**Prioritate:** CRITICA — fara acest fix, P2P nu se stabileste si fisierele mari (video 19MB+) merg prin relay minute intregi

---

## Ce este WebRTC Glare

Glare apare cand **ambele dispozitive trimit un SDP offer simultan**. Fiecare dispozitiv ajunge in starea `have-local-offer` si apoi primeste offer-ul celuilalt. Fara rezolvare corecta, ambele ofera sunt ignorate sau distruse si conexiunea P2P nu se stabileste niciodata.

Pattern-ul standard de rezolvare se numeste **Perfect Negotiation** (documentat de W3C/MDN). Ideea: se desemneaza un peer ca "polite" (cedeaza) si unul ca "impolite" (insista pe offer-ul sau).

---

## Analiza codului curent — ce face gresit

### Codul relevant: `handleOffer()`, liniile 676-686

```typescript
// Polite peer: resolve glare (simultaneous offers)
const existingPeer = this.peers.get(from);
if (existingPeer && existingPeer.connection.signalingState === 'have-local-offer') {
  const isPolite = (this.localUserId || '') < from;
  if (!isPolite) {
    console.log('[WebRTCManager] Glare: ignoring offer (impolite)');
    return;                          // BUG 1: impolite ignora, dar answer-ul sau poate fi pierdut
  }
  console.log('[WebRTCManager] Glare: accepting offer (polite)');
  existingPeer.connection.close();   // BUG 2: distruge conexiunea in loc sa faca rollback
}
// ... continua cu CREARE PEER CONNECTION NOI
```

### Bug 1 — Polite peer distruge conexiunea si creeaza una noua

Linia 685: `existingPeer.connection.close()` urmat de `createPeerConnection(from)` la linia 688.

**Efecte:**
- **Pierdere ICE candidates**: Toate ICE candidates adunate pe conexiunea veche sunt invalide. Noua conexiune incepe ICE gathering de la zero.
- **Pierdere data channel**: Polite peer-ul a creat un data channel in `connectToPeer()` (linia 135). Cand inchide conexiunea, canalul se pierde. Noua conexiune NU creeaza un data channel — asteapta `ondatachannel` de la remote.
- **Evenimente parazite**: `connection.close()` declanseaza `onconnectionstatechange` → `disconnected`/`closed` ASINCRON. Asta poate:
  - Apela `attemptIceRestart` pe conexiunea veche (inchisa)
  - Declanseaza `onConnectionStatusCallback(contactId, false)` care afecteaza UI-ul
  - Se executa DUPA ce noua conexiune a fost creata, corupand starea din `peers` Map
- **Race condition**: Intre `close()` (linia 685) si `peers.set()` (linia 690), handlere din alte goroutine pot citi starea veche din `peers` Map.

**Solutia corecta: SDP Rollback**, nu close+recreate. Peer-ul polite trebuie sa faca rollback la local description, apoi sa aplice offer-ul remote, apoi sa creeze answer.

### Bug 2 — Lipsa flag `makingOffer`

Intre `createOffer()` (linia 151) si `setLocalDescription()` (linia 152) exista un gap asincron. Daca un offer remote soseste in acest gap, `signalingState` este inca `stable`, asa ca glare-ul NU este detectat. Rezultat: ambele setRemoteDescription se executa, conexiunea intra intr-o stare invalida.

### Bug 3 — ICE restart cauzeaza glare suplimentar

`attemptIceRestart()` (linia 517-543) trimite un offer nou. Daca ambele dispozitive fac ICE restart simultan (ex: dupa o deconectare temporara), se produce glare din nou — dar de data asta in contextul unui restart, unde logica de glare nu tine cont de iceRestart flag.

### Bug 4 — `handleAnswer()` poate respinge answer-ul valid

Dupa ce polite peer-ul distruge conexiunea veche si creeaza una noua, answer-ul sau ajunge la impolite peer. Dar daca impolite peer-ul a apucat sa faca ICE restart sau alt state change intre timp, `signalingState` nu mai e `have-local-offer` si answer-ul e ignorat (linia 726-728).

---

## Fix: Implementeaza Perfect Negotiation corect

### Referinta: https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API/Perfect_negotiation

### Pas 1: Adauga stare noua pe clasa

```typescript
class WebRTCManager {
  private peers: Map<string, PeerConnection> = new Map();
  // ... existing fields ...

  // ADAUGA:
  private makingOffer: Map<string, boolean> = new Map();   // flag per-peer
  private ignoreOffer: boolean = false;                     // temp flag in handleOffer
}
```

### Pas 2: Modifica `connectToPeer()` — seteaza `makingOffer`

```typescript
async connectToPeer(contactId: string): Promise<void> {
  console.log(`[WebRTCManager] Initiating connection to ${contactId.substring(0, 8)}...`);

  const peerConnection = await this.createPeerConnection(contactId);

  const dataChannel = peerConnection.createDataChannel('qrchat-messages', {
    ordered: true,
  });
  this.setupDataChannel(dataChannel, contactId);

  this.peers.set(contactId, {
    connection: peerConnection,
    dataChannel,
    contactId,
    isConnected: false,
  });

  try {
    this.makingOffer.set(contactId, true);                    // ADAUGAT
    const offer = await peerConnection.createOffer({});
    // Verifica daca signalingState e inca valid (alt offer ar fi putut fi acceptat intre timp)
    if (peerConnection.signalingState !== 'stable'
        && peerConnection.signalingState !== 'have-local-offer') {
      console.log('[WebRTCManager] Aborting offer — state changed during createOffer');
      return;
    }
    await peerConnection.setLocalDescription(offer);

    SignalingClient.sendOffer(contactId, {
      sdp: offer.sdp,
      type: offer.type,
    });
    console.log(`[WebRTCManager] Offer sent to ${contactId.substring(0, 8)}...`);
  } catch (error) {
    console.error('[WebRTCManager] Error creating offer:', error);
  } finally {
    this.makingOffer.set(contactId, false);                   // ADAUGAT
  }
}
```

### Pas 3: Rescrie `handleOffer()` — Perfect Negotiation cu rollback

Aceasta este cea mai importanta modificare. Inlocuieste complet blocul de glare:

```typescript
private async handleOffer(message: any) {
  const { from, payload } = message;
  console.log(`[WebRTCManager] Handling offer from ${from.substring(0, 8)}...`);

  // Ofertele de apel raman neschimbate
  if (payload?.isCall) {
    this.pendingCallPeers.add(from);
    this.iceCandidateQueues.delete(from);
    console.log(`[WebRTCManager] Call offer from ${from.substring(0, 8)} — ICE candidates will be queued`);
    return;
  }

  this.pendingCallPeers.delete(from);

  // === PERFECT NEGOTIATION ===
  const existingPeer = this.peers.get(from);
  const isPolite = (this.localUserId || '') < from;

  // Detectam glare: peer existent in starea "not stable" SAU in curs de creare offer
  const offerCollision =
    this.makingOffer.get(from) === true ||
    (existingPeer && existingPeer.connection.signalingState !== 'stable');

  if (offerCollision) {
    if (!isPolite) {
      // IMPOLITE: ignora offer-ul remote, insistam pe offer-ul nostru
      console.log('[WebRTCManager] Glare: ignoring offer (impolite)');
      return;
    }

    // POLITE: cedam — rollback la offer-ul nostru local, acceptam offer-ul remote
    console.log('[WebRTCManager] Glare: rolling back local offer (polite)');

    try {
      // Rollback: react-native-webrtc suporta setLocalDescription({type:'rollback'})
      // Alternativ, setRemoteDescription(offer) pe un peer in have-local-offer
      // face rollback implicit in unele implementari.
      // Folosim rollback explicit pentru siguranta:
      await existingPeer!.connection.setLocalDescription(
        { type: 'rollback', sdp: '' } as any
      );
    } catch (rollbackErr) {
      // Daca rollback-ul esueaza (versiune veche de react-native-webrtc),
      // fallback la close+recreate, dar cu precautii
      console.warn('[WebRTCManager] Rollback failed, falling back to recreate:', rollbackErr);
      existingPeer!.connection.close();

      const newPc = await this.createPeerConnection(from);
      this.peers.set(from, {
        connection: newPc,
        dataChannel: null,
        contactId: from,
        isConnected: false,
      });

      try {
        await newPc.setRemoteDescription(new RTCSessionDescription(payload));
        await this.drainIceCandidateQueue(from);
        const answer = await newPc.createAnswer();
        await newPc.setLocalDescription(answer);
        SignalingClient.sendAnswer(from, { sdp: answer.sdp, type: answer.type });
        console.log(`[WebRTCManager] Answer sent (fallback) to ${from.substring(0, 8)}...`);
      } catch (error) {
        console.warn('[WebRTCManager] Fallback offer handling failed:', (error as any)?.message);
      }
      return;
    }

    // Rollback reusit — acum aplica offer-ul remote pe conexiunea EXISTENTA
    try {
      await existingPeer!.connection.setRemoteDescription(
        new RTCSessionDescription(payload)
      );
      await this.drainIceCandidateQueue(from);
      const answer = await existingPeer!.connection.createAnswer();
      await existingPeer!.connection.setLocalDescription(answer);
      SignalingClient.sendAnswer(from, { sdp: answer.sdp, type: answer.type });
      console.log(`[WebRTCManager] Answer sent (after rollback) to ${from.substring(0, 8)}...`);
    } catch (error) {
      console.warn('[WebRTCManager] Error handling offer after rollback:', (error as any)?.message);
    }
    return;
  }

  // === NU E GLARE — flow normal (peer nou sau conexiune stabila) ===
  // Daca exista un peer vechi in stare stabila, inchide-l
  if (existingPeer) {
    existingPeer.connection.close();
  }

  const peerConnection = await this.createPeerConnection(from);
  this.peers.set(from, {
    connection: peerConnection,
    dataChannel: null,
    contactId: from,
    isConnected: false,
  });

  try {
    await peerConnection.setRemoteDescription(
      new RTCSessionDescription(payload)
    );
    await this.drainIceCandidateQueue(from);
    const answer = await peerConnection.createAnswer();
    await peerConnection.setLocalDescription(answer);
    SignalingClient.sendAnswer(from, { sdp: answer.sdp, type: answer.type });
    console.log(`[WebRTCManager] Answer sent to ${from.substring(0, 8)}...`);
  } catch (error) {
    console.warn('[WebRTCManager] Error handling offer:', (error as any)?.message);
  }
}
```

### Pas 4: Fix `attemptIceRestart()` — respecta makingOffer

```typescript
private async attemptIceRestart(contactId: string) {
  const peer = this.peers.get(contactId);
  if (!peer) return;
  if (!peer.dataChannel) return;

  const restarts = this.iceRestartCounts.get(contactId) || 0;
  if (restarts >= MAX_ICE_RESTARTS) {
    console.warn(`[WebRTCManager] ICE restart limit (${MAX_ICE_RESTARTS}) reached for ${contactId.substring(0, 8)}`);
    return;
  }

  this.iceRestartCounts.set(contactId, restarts + 1);
  console.log(`[WebRTCManager] ICE restart ${restarts + 1}/${MAX_ICE_RESTARTS} for ${contactId.substring(0, 8)}`);

  try {
    this.makingOffer.set(contactId, true);                    // ADAUGAT
    const offer = await peer.connection.createOffer({ iceRestart: true });
    await peer.connection.setLocalDescription(offer);
    SignalingClient.sendOffer(contactId, {
      sdp: offer.sdp,
      type: offer.type,
    });
  } catch (e) {
    console.error('[WebRTCManager] ICE restart failed:', e);
  } finally {
    this.makingOffer.set(contactId, false);                   // ADAUGAT
  }
}
```

### Pas 5: Cleanup `makingOffer` in disconnect/destroy

Adauga in `disconnectPeer()`:
```typescript
this.makingOffer.delete(contactId);
```

Adauga in `destroy()`:
```typescript
this.makingOffer.clear();
```

---

## React Native WebRTC — Nota despre rollback

`react-native-webrtc` (versiunea 118+) suporta `setLocalDescription({type: 'rollback'})`. Verifica versiunea din `package.json`:

```bash
grep 'react-native-webrtc' /Users/ruslanconstantinovici/QRChat/package.json
```

Daca versiunea e < 118.0.0, rollback-ul explicit NU va functiona. In acest caz, fallback-ul close+recreate din codul de mai sus (blocul catch de la rollback) se va activa automat.

Daca versiunea e >= 118.0.0 (inclusiv 124.x pe care RN 0.84 il foloseste de obicei), rollback-ul explicit functioneaza.

**NU folosi `setRemoteDescription(offer)` ca rollback implicit** — `react-native-webrtc` nu suporta implicit rollback (doar browserii moderni). Trebuie `setLocalDescription({type:'rollback'})` explicit.

---

## Criteriu de succes

1. **P2P se stabileste fara glare** intre 2 dispozitive care deschid aceeasi conversatie simultan
2. In DevTools/console, NU mai apare `Glare: ignoring offer (impolite)` urmat de P2P esuat
3. Dupa glare, in console trebuie sa apara:
   - Pe polite: `Glare: rolling back local offer (polite)` urmat de `Answer sent (after rollback)`
   - Pe impolite: `Glare: ignoring offer (impolite)` urmat de `Answer set from` (cand primeste answer de la polite)
4. Data channel se deschide cu succes (`Data channel OPEN`)
5. Transfer fiser mare (>5MB) merge P2P, nu prin relay
6. ICE restart dupa deconectare temporara (ex: WiFi off/on) reuseste fara glare

### Test manual:
1. Deschide conversatia pe ambele dispozitive **simultan** (1-2 secunde diferenta)
2. Trimite un mesaj text → trebuie sa mearga P2P
3. Trimite un fisier video mare (>10MB) → trebuie sa mearga P2P (repede), nu relay (lent)
4. Opreste WiFi pe un dispozitiv 5 secunde, porneste → ICE restart reuseste
5. Repeta de 5 ori — 0 esecuri

---

## Capcane de evitat

1. **NU folosi `onnegotiationneeded`** pentru a trimite oferte automat. In React Native WebRTC, `onnegotiationneeded` se declanseaza inconsistent. Pastreaza flow-ul explicit: `connectToPeer()` trimite offer, `handleOffer()` raspunde cu answer.

2. **NU inlocui `existingPeer.connection.close()` doar cu rollback fara catch**. Rollback-ul poate esua pe versiuni vechi de `react-native-webrtc`. Trebuie MEREU fallback la close+recreate.

3. **NU uita sa cureti `makingOffer`** — daca o exceptie apare in `createOffer` si `finally` nu se executa, flag-ul ramane `true` si viitoarele oferte de la remote vor fi considerate mereu glare.

4. **NU modifica logica de polite/impolite** (`localUserId < from`). Aceasta e determinista si consistenta pe ambele dispozitive. NU folosi timestamp-ul ofertei (poate fi desincronizat) sau random.

5. **NU sterge data channel-ul la rollback**. Cand polite peer-ul face rollback pe conexiunea existenta, data channel-ul creat de el ramane valid. Doar SDP-ul e resetat, nu track-urile sau channel-urile.

6. **Atentie la `handleAnswer` dupa rollback**: Dupa ce polite peer-ul face rollback si trimite answer, impolite peer-ul va primi acest answer. Asigura-te ca `handleAnswer()` nu il respinge — verifica ca peer.connection.signalingState este `have-local-offer` (trebuie sa fie, daca impolite peer-ul a mentinut offer-ul original).

7. **Nu trimite ICE candidates in paralel cu rollback**: Dupa rollback, ICE candidates vechi sunt invalide. Dar noi candidates vor fi generate automat de conexiune. Codul curent de `onicecandidate` le trimite corect — nu trebuie schimbat.

8. **Deploy pe simulator SI telefon fizic dupa modificari** — regula obligatorie proiect.

---

## Fisiere de modificat

| Fisier | Modificare |
|--------|-----------|
| `src/network/WebRTCManager.ts` | Toate modificarile de mai sus |

Niciun alt fisier nu trebuie modificat. SignalingClient, MessagingService, CallScreen — neschimbate.
