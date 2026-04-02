# QRChat Call System Architecture

## Document tehnic complet — bazat pe cercetare WebRTC, Signal, WhatsApp, react-native-incall-manager

---

## A. ALGORITMUL COMPLET DE APEL — Pas cu Pas

### OVERVIEW: Ce se intampla la un apel VoIP

Un apel VoIP in QRChat implica 3 actori: **Apelant** (caller), **Receptor** (callee), **Server** (signaling relay). Serverul NU participa la apel — doar relay-eaza mesaje de semnalizare. Dupa stabilirea conexiunii P2P, audio/video curge direct intre dispozitive.

**Flow-ul complet:**
```
Apelant                     Server                     Receptor
   |                          |                          |
   |--- offer (isCall) ------>|                          |
   |   [start ringback]       |--- offer (isCall) ------>|
   |                          |                  [show UI, play ringtone]
   |                          |                          |
   |                          |<----- answer ------------|
   |<----- answer ------------|         [stop ringtone]  |
   |   [stop ringback]        |                          |
   |                          |                          |
   |<==== ICE candidates ====>|<==== ICE candidates ====>|
   |                          |                          |
   |<============ P2P AUDIO/VIDEO DIRECT ===============>|
   |   [start timer]          |                          |  [start timer]
```

---

### 1. APELANT (Outgoing Call)

#### Pas 1: User apasa "Call"
- App navigheaza la `CallScreen` cu parametrii: `contactId`, `contactName`, `isVideo`, `isIncoming: false`
- `CallScreen.useEffect` apeleaza `startCall()`

#### Pas 2: Setup local (getUserMedia + createOffer)
```
startCall() {
  1. Inregistreaza callbacks: onCallConnected, onCallDisconnected, onRemoteStream
  2. Porneste InCallManager.start({ media: 'audio' | 'video' })
  3. Cere acces la microfon/camera: mediaDevices.getUserMedia()
  4. Salveaza localStream in ref
  5. Apeleaza WebRTCManager.startCall(contactId, stream, isVideo)
}
```

#### Pas 3: WebRTCManager.startCall() — Ce se trimite la server
```
WebRTCManager.startCall() {
  1. Inchide orice peer existent pentru acest contact (evita conflicte)
  2. Creeaza RTCPeerConnection cu ICE servers (STUN + TURN)
  3. Adauga track-urile locale (audio/video) la peer connection
  4. Seteaza handler ontrack pentru stream-ul remote
  5. Creeaza SDP offer: pc.createOffer({ offerToReceiveAudio: true })
  6. Seteaza local description: pc.setLocalDescription(offer)
  7. TRIMITE la server: SignalingClient.sendOffer(contactId, {
       sdp, type, isCall: true, isVideo, callTimestamp
     })
  8. Porneste timeout 45s — daca nimeni nu raspunde, endCall()
}
```

#### Pas 4: Ce sunet se aude — RINGBACK TONE ("tuut...tuut...")

**Starea curenta a codului:** `CallScreen` seteaza `callStatus = 'ringing'` si apoi:
```javascript
// CallScreen.tsx liniile 85-101
useEffect(() => {
  if (callStatus === 'ringing' && !isIncoming) {
    InCallManager.startRingback('_DEFAULT_');
  }
}, [callStatus]);
```

**PROBLEMA PE ANDROID:** `InCallManager.startRingback('_DEFAULT_')` are urmatoarele bug-uri documentate:
1. **Nu exista ton ringback system pe Android** — Android nu are un "system ringback tone" implicit precum iOS. `_DEFAULT_` pe Android fie nu reda nimic, fie reda un sunet scurt care se opreste.
2. **`_BUNDLE_` pe Android reda ringtone-ul (melodia de apel incoming)** — In loc de "tuut...tuut...", se aude melodia de incoming call, ceea ce confuza utilizatorul.
3. **Volume routing gresit** — Chiar daca suna, sunetul iese prin speaker la volum maxim in loc de earpiece la volum normal.
4. **WebRTC interference** — WebRTC preia controlul audio session intern. Daca ringback-ul porneste inainte ca WebRTC sa-si stabileasca audio mode, sunetul se opreste brusc (Issue #101).

**SOLUTIA CORECTA:** Vezi sectiunea B.1.

#### Pas 5: Cand se opreste ringback-ul
- Cand receptorul raspunde: `startConnectedTimer()` apeleaza `InCallManager.stopRingback()`
- Cand receptorul refuza: server trimite `call-ended`, `finishAndGoBack()` opreste ringback
- Timeout 60s (CallScreen) sau 45s (WebRTCManager): `finishAndGoBack()` opreste ringback

#### Pas 6: Ce se intampla cand raspunde
```
1. Server relay-eaza SDP answer inapoi la apelant
2. WebRTCManager.handleAnswer() seteaza remoteDescription
3. ICE candidates se schimba → P2P connection stabilita
4. pc.onconnectionstatechange → 'connected' → markConnected()
5. markConnected() apeleaza onCallConnectedCallback
6. CallScreen.startConnectedTimer():
   - Opreste ringback: InCallManager.stopRingback()
   - Anuleaza timeout-ul de 60s
   - Seteaza callStatus = 'connected'
   - Porneste timer-ul de durata (1s interval)
```

#### Pas 7: Ce se intampla cand nu raspunde (timeout)
```
1. WebRTCManager: dupa 45s, endCall(contactId) — trimite call-ended la server
2. CallScreen: dupa 60s, finishAndGoBack(0, true):
   - Opreste ringback
   - Salveaza call log (duration: 0 = missed)
   - Navigheaza inapoi
```

#### Pas 8: Ce se intampla cand refuza
```
1. Receptorul apasa Decline → trimite call-ended la server
2. Server relay-eaza call-ended la apelant
3. CallScreen listener 'call-ended': finishAndGoBack(duration, false)
4. Ringback se opreste, call log se salveaza, navigheaza inapoi
```

---

### 2. RECEPTOR (Incoming Call)

#### Pas 1: Server trimite offer-ul

Offer-ul ajunge prin SignalingClient ca mesaj cu `type: 'offer'` si `payload.isCall: true`.

**Doua cai de receptie:**
- **Path 1 (SignalingClient direct):** `MessagingService` asculta pe `SignalingClient.on('offer')` si detecteaza `payload.isCall`
- **Path 2 (Encrypted relay):** Mesajul vine criptat E2E, se decripteaza, si se verifica `data.isCall`

#### Pas 2: Guard anti-duplicate — O SINGURA DATA!

```javascript
// MessagingService.ts
SignalingClient.on('offer', async (message) => {
  if (message.payload?.isCall) {
    // GUARD 1: Daca deja avem pending call sau apel activ de la acest caller
    if (pendingCalls.has(message.from) || this.activeIncomingCallFrom === message.from) {
      console.log('Duplicate offer — ignoring');
      return; // NU procesa din nou!
    }
    // ... procesare
  }
});
```

**PROBLEMA CURENTA:** Guard-ul exista dar nu e complet:
- `activeIncomingCallFrom` se reseteaza la `null` cand vine `call-ended`, dar daca serverul retrimite offer-ul (din pending queue la reconectare), guard-ul nu mai protejeaza.
- Nu exista guard pe baza `callTimestamp` — offer-uri vechi din coada pending pot declansa un apel nou.

#### Pas 3: Se porneste melodia de apel (ringtone) — O SINGURA INSTANTA

```javascript
// MessagingService.ts — dupa guard
this.activeIncomingCallFrom = message.from;
NotificationService.showCallNotification(callerName, isVideoCall, message.from);
EventBus.emit('incoming-call', { contactId, contactName, isVideo, offer });
```

**PROBLEMA CURENTA — OVERLAP RINGTONE:**
1. `NotificationService.showCallNotification()` pe Android creeaza o notificare cu `sound: 'ringtone'` care reda melodia de apel.
2. In paralel, `playRingtoneLoop()` porneste un `setInterval` de 3s care reda `SystemSoundModule.playSystemSound()`.
3. Daca offer-ul vine si pe path-ul encrypted (caz real — serverul relay-eaza si pune in pending queue), se pot declansa DOUA instante de ringtone simultan.
4. Mai mult, daca user-ul navigheaza la `CallScreen` si apoi inapoi, `IncomingCallOverlay` ramane montat si ringtone-ul nu se opreste.

**SOLUTIA CORECTA:** Vezi sectiunea B.2.

#### Pas 4: Se afiseaza UI-ul de apel

`EventBus.emit('incoming-call')` → `App.tsx` sau navigatorul principal arata `IncomingCallOverlay`:
- Overlay full-screen cu avatar animat (pulse)
- Doua butoane: Accept (verde) si Decline (rosu)
- Pe iOS: CallKit afiseaza interfata nativa (daca app-ul e in background)

#### Pas 5: User raspunde — ce se intampla
```
1. IncomingCallOverlay.onAccept() se apeleaza
2. App navigheaza la CallScreen cu isIncoming: true + offer
3. CallScreen.startCall():
   a. Porneste InCallManager.start()
   b. getUserMedia() — cere microfon/camera
   c. WebRTCManager.answerCall(contactId, stream, offer):
      - Inchide peer-ul existent (data channel de chat)
      - Creeaza RTCPeerConnection noua
      - Adauga track-uri locale
      - setRemoteDescription(offer) — accepta SDP-ul apelantului
      - Goleste coada ICE candidates (drainIceCandidateQueue)
      - createAnswer() → setLocalDescription(answer)
      - Trimite answer la server: SignalingClient.sendAnswer()
4. ICE candidates se schimba → P2P se stabileste
5. onCallConnected → startConnectedTimer()
6. Ringtone-ul trebuie oprit de IncomingCallOverlay.onAccept() INAINTE de navigare
```

#### Pas 6: User refuza
```
1. IncomingCallOverlay.onDecline() se apeleaza
2. Trimite call-ended la server: SignalingClient.sendCallEnded(contactId)
3. Opreste ringtone: NotificationService.stopCallRingtone()
4. Anuleaza notificarea: NotificationService.cancelCallNotification()
5. Reseteaza activeIncomingCallFrom = null
6. Salveaza call log (missed/declined)
```

#### Pas 7: Timeout fara raspuns
```
1. Apelantul trimite call-ended dupa 45-60s
2. Server relay-eaza call-ended la receptor
3. MessagingService handler 'call-ended':
   - Reseteaza activeIncomingCallFrom = null
   - Salveaza call log ca pierdut
   - Opreste ringtone
   - Dismisses IncomingCallOverlay (daca inca e vizibil)
```

---

### 3. SERVER (Signaling Relay)

#### Ce face serverul — si mai important, ce NU face

Serverul QRChat este un **relay pur**. El:
- **NU interpreteaza** SDP offer/answer
- **NU proceseaza** ICE candidates
- **NU participa** la conexiunea P2P
- **NU stocheaza** media (audio/video)

#### Pas 1: Primeste offer de la apelant
```javascript
// server/index.js — case 'offer':
case 'offer': {
  const targetClient = clients.get(message.to);
  if (targetClient && targetClient.readyState === WebSocket.OPEN) {
    // Destinatarul e online — relay direct
    targetClient.send(JSON.stringify({
      type: 'offer',
      from: userId,
      payload: message.payload,
    }));
  } else {
    // Destinatarul e offline — pune in coada + trimite push
    enqueuePending(message.to, { ... });
    sendPush(message.to, userId, { callerName, isVideo, offer });
  }
}
```

#### Pas 2: Relay-eaza la receptor — O SINGURA DATA

**PROBLEMA CURENTA:** Serverul NU are logica de deduplicare. Daca:
1. Apelantul trimite offer
2. Receptorul e online → server relay-eaza direct
3. Receptorul se deconecteaza si reconecteaza
4. Offer-ul era si in pending queue (daca a fost pus intre timp)
5. La reconectare, server livreaza offer-ul din pending → **DUPLICAT!**

**SI MAI GRAV:** Serverul pune in pending queue TOATE tipurile de mesaje signaling (offer, answer, ice-candidate, call-ended). Offer-urile de apel nu ar trebui niciodata puse in coada — un apel este o actiune in timp real. Daca receptorul nu e online, apelul este pierdut.

#### Pas 3: Relay answer inapoi
Server primeste answer de la receptor, il relay-eaza la apelant. Fara procesare.

#### Pas 4: Relay ICE candidates
Ambele parti trimit ICE candidates — serverul le relay-eaza in ambele directii.

#### Pas 5: Relay call-ended
Cand oricare parte termina apelul, trimite `call-ended` prin server.

---

## B. SOLUTII CONCRETE PENTRU BUG-URILE ACTUALE

### B.1. Ringback pe Android — Ce metoda functioneaza REAL

#### Problema
`InCallManager.startRingback('_DEFAULT_')` nu functioneaza corect pe Android:
- Android nu are un "system ringback tone" standard accesibil prin API-ul folosit de InCallManager
- `_BUNDLE_` pe Android reda fisierul `incallmanager_ringback.mp3` din `res/raw/`, dar daca nu exista, reda ringtone-ul system
- WebRTC preia audio focus si opreste playback-ul

#### Solutia recomandata: Custom ringback cu react-native-sound sau bundled audio

**Varianta 1 (Recomandata): InCallManager cu fisier bundled custom**

1. Creeaza/descarca un fisier ringback tone standard (tonul "tuut...tuut..." clasic)
2. Salveaza ca `incallmanager_ringback.mp3` in `android/app/src/main/res/raw/`
3. Salveaza ca `incallmanager_ringback.caf` (sau .mp3) in bundle-ul iOS
4. Foloseste `InCallManager.startRingback('_BUNDLE_')` pe ambele platforme

```javascript
// CallScreen.tsx — SOLUTIA CORECTA
useEffect(() => {
  if (callStatus === 'ringing' && !isIncoming) {
    // Delay ringback start cu 500ms pe Android — permite WebRTC sa-si stabileasca audio mode
    const delay = Platform.OS === 'android' ? 500 : 0;
    const timer = setTimeout(() => {
      InCallManager.startRingback('_BUNDLE_');
      ringbackRef.current = true;
    }, delay);
    return () => {
      clearTimeout(timer);
      if (ringbackRef.current) {
        InCallManager.stopRingback();
        ringbackRef.current = false;
      }
    };
  } else if (ringbackRef.current) {
    InCallManager.stopRingback();
    ringbackRef.current = false;
  }
}, [callStatus]);
```

**Varianta 2 (Fallback): react-native-sound ca ringback pe Android**

Daca InCallManager continua sa aiba probleme pe Android, se poate folosi `react-native-sound` direct:

```javascript
import Sound from 'react-native-sound';

// La pornirea apelului outgoing (doar Android)
if (Platform.OS === 'android' && callStatus === 'ringing' && !isIncoming) {
  const ringback = new Sound('ringback.mp3', Sound.MAIN_BUNDLE, (error) => {
    if (!error) {
      ringback.setNumberOfLoops(-1); // loop infinit
      ringback.setVolume(0.5);
      ringback.play();
      ringbackSoundRef.current = ringback;
    }
  });
}

// La oprire:
if (ringbackSoundRef.current) {
  ringbackSoundRef.current.stop();
  ringbackSoundRef.current.release();
  ringbackSoundRef.current = null;
}
```

**IMPORTANT:** Plasarea fisierului audio:
- Android: `android/app/src/main/res/raw/ringback.mp3`
- iOS: Adauga in Xcode project bundle

#### Cerinte fisier audio ringback:
- Format: MP3 sau WAV
- Durata: ~5 secunde (un ciclu "tuut...pauza...tuut...pauza")
- Loop: biblioteca face loop automat
- Frecventa: 425 Hz (standardul european) sau 440 Hz (US)
- Pattern: 1s ton, 4s pauza (standard EU) sau 2s ton, 4s pauza (standard US)

---

### B.2. Ringtone Overlap — Unde trebuie pus guard-ul

#### Problema
Pe Android, pot suna simultan mai multe instante de ringtone cand vine un apel incoming:
1. Android notification sound (din Notifee `showCallNotification`)
2. `SystemSoundModule.playSystemSound()` din `playRingtoneLoop()`
3. Daca offer-ul vine duplicat (din pending queue la reconnect), se adauga inca o instanta

#### Solutia: Guard pe 3 niveluri

**Nivel 1 — MessagingService: Dedup offer-uri (EXISTA, dar trebuie imbunatatit)**

```javascript
// MessagingService.ts — GUARD IMBUNATATIT
SignalingClient.on('offer', async (message) => {
  if (message.payload?.isCall) {
    // Guard 1: Deja un apel activ/pending de la acest caller
    if (pendingCalls.has(message.from) || this.activeIncomingCallFrom === message.from) {
      return;
    }

    // Guard 2 NOU: Verifica callTimestamp — rejecteaza offer-uri mai vechi de 30s
    const callTimestamp = message.payload?.callTimestamp;
    if (callTimestamp && Date.now() - callTimestamp > 30000) {
      console.log('[MessagingService] Stale call offer (>30s old) — ignoring');
      return;
    }

    // Guard 3 NOU: Verifica daca suntem deja in CallScreen
    // (previne re-trigger daca user deja raspunde/refuza)
    if (this.isInCallScreen) {
      console.log('[MessagingService] Already in call screen — ignoring new offer');
      return;
    }

    // ... procesare normala
  }
});
```

**Nivel 2 — NotificationService: O singura instanta de ringtone**

```javascript
// NotificationService.ts — GUARD
private isRingtoneActive = false;

playRingtoneLoop(soundId: string) {
  // GUARD: Nu porni daca deja suna
  if (this.isRingtoneActive) {
    console.log('[NotificationService] Ringtone already active — skipping');
    return;
  }
  this.isRingtoneActive = true;

  // ... porneste ringtone
}

stopCallRingtone() {
  this.isRingtoneActive = false;
  // ... opreste ringtone
}
```

**Nivel 3 — Server: NU pune call offer in pending queue**

```javascript
// server/index.js — MODIFICARE CRITICA
case 'offer': {
  const targetClient = clients.get(message.to);
  if (targetClient && targetClient.readyState === WebSocket.OPEN) {
    targetClient.send(JSON.stringify({ type: 'offer', from: userId, payload: message.payload }));
  } else {
    // CALL OFFERS: NU pune in pending queue — apelurile sunt in timp real
    if (message.payload?.isCall) {
      // Trimite doar push notification — receptorul va vedea missed call
      sendPush(message.to, userId, { callerName, isVideo, offer });
      ws.send(JSON.stringify({ type: 'user-offline', to: message.to }));
      // NU apela enqueuePending() pentru call offers!
    } else {
      // Non-call offers (data channel setup) — pune in coada normal
      enqueuePending(message.to, { ... });
    }
  }
  break;
}
```

---

### B.3. Sincronizare iOS vs Android

#### Diferente fundamentale

| Aspect | iOS | Android |
|--------|-----|---------|
| Incoming call UI (background) | CallKit nativ | Notifee full-screen notification |
| Incoming call UI (foreground) | IncomingCallOverlay (custom) | IncomingCallOverlay (custom) |
| Ringtone incoming | CallKit gestioneaza (silence.caf configurat) | Notifee notification sound + SystemSoundModule loop |
| Ringback outgoing | InCallManager._DEFAULT_ functioneaza | InCallManager._DEFAULT_ NU functioneaza |
| VoIP Push | PushKit (instant, wakes app) | FCM data message (poate fi intarziat) |
| Audio routing | InCallManager.setSpeakerphoneOn() | AudioManagerModule.setSpeakerOn() (custom native) |

#### Reguli de sincronizare:

1. **Ringback outgoing:** Foloseste `_BUNDLE_` cu fisier custom pe ambele platforme — comportament identic
2. **Ringtone incoming:** Pe iOS, CallKit gestioneaza sunetul in background. Pe Android, `playRingtoneLoop()` + guard anti-overlap
3. **Audio mode:** Pe Android, delay 500ms inainte de a porni orice sunet dupa `InCallManager.start()` — permite WebRTC sa-si stabileasca audio session
4. **Stop ringtone:** INTOTDEAUNA opreste inainte de navigare la CallScreen:
   ```javascript
   // IncomingCallOverlay.onAccept():
   NotificationService.stopCallRingtone();
   NotificationService.cancelCallNotification();
   // APOI navigheaza la CallScreen
   ```

---

### B.4. WebRTC Perfect Negotiation — Gestionare offer-uri multiple

QRChat DEJA implementeaza Perfect Negotiation in `WebRTCManager.handleOffer()` pentru data channel connections:
- `isPolite` se determina prin compararea `localUserId < from`
- Polite peer face rollback, impolite peer ignora offer-ul conflictual

**IMPORTANT pentru apeluri:** Perfect Negotiation NU se aplica la call offers, deoarece:
- Call offers sunt gestionate separat (nu creeaza peer connection automat)
- Doar UN offer de apel trebuie procesat per sesiune (guard in MessagingService)
- Daca ambii utilizatori apasa "Call" simultan → cel cu ID-ul mai mic este "polite" si cedeaza (rollback + accept offer-ul celuilalt)

**RECOMANDARE:** Adauga glare detection pentru apeluri simultane:
```javascript
// MessagingService.ts — cand primim offer de apel
if (message.payload?.isCall) {
  // Verifica daca NOI suntem in curs de a apela acelasi contact
  const weAreCalling = WebRTCManager.isOutgoingCallActive(message.from);
  if (weAreCalling) {
    const isPolite = (localUserId || '') < message.from;
    if (isPolite) {
      // Noi cedam — anulam apelul nostru, acceptam al lor
      WebRTCManager.endCall(message.from, false);
      // Procesam offer-ul incoming normal
    } else {
      // Noi suntem impolite — ignoram offer-ul lor
      return;
    }
  }
}
```

---

## C. REFERINTE SI SURSE

### WebRTC Standards
- [MDN WebRTC Perfect Negotiation](https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API/Perfect_negotiation)
- [MDN WebRTC Signaling and Video Calling](https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API/Signaling_and_video_calling)
- [WebRTC.org Getting Started](https://webrtc.org/getting-started/peer-connections)

### react-native-incall-manager Issues
- [Issue #101: Ringback plays briefly then stops](https://github.com/react-native-webrtc/react-native-incall-manager/issues/101) — WebRTC audio session override
- [Issue #218: Android ringback too loud](https://github.com/react-native-webrtc/react-native-incall-manager/issues/218) — Speaker routing bug
- [Issue #148: Ringback same as ringtone on iOS](https://github.com/react-native-webrtc/react-native-incall-manager/issues/148)

### Messenger Architecture
- [Signal: End-to-End Encrypted Group Calls](https://signal.org/blog/how-to-build-encrypted-group-calls/)
- [WhatsApp WebRTC Analysis](https://webrtchacks.com/whats-up-with-whatsapp-and-webrtc/)
- WhatsApp optimizeaza latenta prin: relay initial → switch la P2P (ICE upgrade)

### React Native Libraries
- [react-native-incall-manager](https://github.com/react-native-webrtc/react-native-incall-manager) — Audio routing + ringback/ringtone
- [react-native-callkeep](https://github.com/react-native-webrtc/react-native-callkeep) — CallKit (iOS) + ConnectionService (Android)
- [react-native-voip-push-notification](https://github.com/react-native-webrtc/react-native-voip-push-notification) — PushKit (iOS only)
- [Twilio Voice React Native — Ringback Docs](https://github.com/twilio/twilio-voice-react-native/blob/main/docs/play-outgoing-call-ringback-tone.md)

### Diferente iOS vs Android
- iOS 13+: PushKit VoIP push TREBUIE sa afiseze CallKit UI, altfel app-ul e terminat
- Android: FCM data messages + ConnectionService (prin react-native-callkeep)
- Android nu are API standard pentru ringback tone — trebuie fisier audio custom
