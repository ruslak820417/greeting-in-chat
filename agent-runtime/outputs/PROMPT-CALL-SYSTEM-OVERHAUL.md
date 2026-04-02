# QRChat Call System Overhaul — Complete Implementation Prompt

**Data:** 31 Martie 2026
**Versiune curenta:** v4.3.0, Build 203
**Obiectiv:** Sistem de apeluri audio/video de nivel WhatsApp/Signal
**Codebase:** `/Users/ruslanconstantinovici/QRChat`
**Stack:** React Native 0.84, TypeScript, Node.js server (Railway), TweetNaCl crypto, WebRTC, SQLite

---

## CONTEXT SI MOTIVATIE

QRChat este un messenger criptat React Native cu sistem de apeluri audio/video bazat pe WebRTC. Sistemul actual are o fundatie buna (scor 8.5/10 vs best practices), dar are lacune critice care trebuie rezolvate pentru a atinge nivelul de calitate WhatsApp/Signal. Aceasta sarcina este PRIORITATEA #1 a proiectului.

### Ce avem deja (NU rescrie):
- `useManualAudio = true` in AppDelegate (pattern Signal/Wire)
- `RTCAudioBridge.swift` — bridge nativ pentru audio session
- `ColdStartCoordinator.ts` — 3-path SDP retrieval (VoIP push / WebSocket / pending queue)
- `CallKitService.ts` — integrare CallKit cu UUID tracking
- `WebRTCManager.ts` — peer connections, ICE candidate queueing + drain, ICE restart (max 2)
- `SignalingClient.ts` — WebSocket cu Noise Pipes auth, heartbeat, reconnect exponential
- `server/index.js` — signaling relay, activeCalls Map, VoIP push, TURN credentials
- `continualGatheringPolicy: 'gatherContinually'` — network change resilience
- `call-accepted-pending` — callee ACK inainte de WebRTC ready
- Event listeners in `index.js` INAINTE de AppRegistry (cold start capture)
- `didLoadWithEvents` pentru buffered CallKit events

### Ce LIPSESTE (trebuie implementat):

**CRITICE (Blockers):**
1. Foreground incoming calls NU folosesc CallKit — doar IncomingCallOverlay React component. Apple Watch, AirPods, CarPlay nu vad apelul
2. Video toggle mid-call LIPSESTE complet — apelul ramane audio-only sau video-only
3. Camera flip (front/rear) LIPSESTE
4. Timeout disconnect de 10 secunde e PREA agresiv — apelurile pica pe reteaua slaba
5. NU exista UI "Reconnecting..." — userul vede "Connected" apoi apelul se termina brusc
6. Debounce 600ms pe incoming calls adauga latenta perceptibila

**IMPORTANTE (Quality):**
7. Perfect Negotiation pattern INCOMPLET — lipseste rollback complet polite/impolite
8. NU exista adaptare bandwidth — video calls pe retea slaba degrade fara ajustare
9. Lipseste Opus codec optimization (useinbandfec=1, dtx=1)
10. Lipseste state machine formala pentru call states
11. Lipseste proactive network change detection (NetInfo listener)
12. VoIP push payload size NU e validat (risc depasire 5KB APNs limit)
13. Lipseste SDP minification in VoIP push payload
14. Duplicate missed call logging (App.tsx SI MessagingService)
15. Lipseste call analytics/CDR (call duration, quality, path used)

---

## ARHITECTURA TINTA (Inspirata din WhatsApp + Signal)

### Stiva de protocoale QRChat (adaptata):

```
Layer 4: CallKit (CXProvider)         — controleaza audio session lifecycle
Layer 3: RTCAudioSession              — wrapper peste AVAudioSession, manual mode
Layer 2: WebRTC (react-native-webrtc) — peer connections, codecs, media
Layer 1: Node.js Server (Socket.IO)   — signaling relay, TURN, push, call state
Layer 0: TweetNaCl                    — E2E encryption (deja existent)
```

### Strategia WhatsApp: RELAY-FIRST, P2P-OPTIMIZE

WhatsApp nu asteapta P2P — conecteaza prin TURN imediat, apoi face upgrade la P2P daca e posibil. QRChat trebuie sa adopte aceeasi strategie:

```
Faza 1: RELAY IMMEDIATE
  1. Cere TURN credentials (cache-uite, deja disponibile)
  2. Adauga TURN servers cu prioritate in ICE config
  3. Media curge prin TURN relay (latenta mai mare dar fiabil)
  4. Apelul e "conectat" din perspectiva userului

Faza 2: P2P PROBE (background)
  5. ICE continua sa caute peer reflexive candidates
  6. Daca gaseste ruta directa, comuta transparent
  7. Sequence numbers mentin continuitatea

Faza 3: FALLBACK
  8. Daca P2P pica, revine pe relay fara intrerupere
```

### Call State Machine (Formala)

```
                    +----------+
                    |   IDLE   |
                    +----+-----+
                         |
              +----------+----------+
              |                     |
              v                     v
     +--------+------+    +--------+------+
     |   CALLING     |    |   RINGING     |
     |  (outgoing)   |    |  (incoming)   |
     +--------+------+    +--------+------+
              |                     |
              |  callee accepts     |  user answers
              v                     v
     +--------+---------------------+------+
     |        CONNECTING_AFTER_ACCEPTED    |
     |  (ICE + DTLS/SRTP negotiation)     |
     +------------------+------------------+
                        |
                        v
     +------------------+------------------+
     |              CONNECTED              |
     |          (media flowing)            |
     +---+-------------------------+---+---+
         |                         |   |
         v                         v   v
  +------+------+         +--------+---+----+
  | RECONNECTING|         |    ON HOLD      |
  | (ICE restart)|        | (interruption)  |
  +------+------+         +--------+--------+
         |                         |
         | recovered               | resumed
         +------+------------------+
                |
                v
         +------+------+
         |    ENDED    |
         +-------------+
```

Implementeaza ca un `CallStateMachine` class cu tranzitii explicite si guards.

---

## PLAN DE IMPLEMENTARE DETALIAT

### TASK 1: Call State Machine (`src/services/CallStateMachine.ts`) — NOU

Creeaza o clasa formala care gestioneaza toate tranzitiile:

```typescript
type CallState =
  | 'idle'
  | 'calling'           // outgoing, asteapta raspuns
  | 'ringing'           // incoming, suna
  | 'connecting'        // acceptat, ICE in progress
  | 'connected'         // media curge
  | 'reconnecting'      // ICE restart in curs
  | 'on-hold'           // audio interruption
  | 'ended';            // cleanup

type CallEvent =
  | 'initiate-call'
  | 'receive-call'
  | 'remote-accept'
  | 'local-accept'
  | 'ice-connected'
  | 'ice-disconnected'
  | 'ice-failed'
  | 'ice-restart-success'
  | 'audio-interrupted'
  | 'audio-resumed'
  | 'local-hangup'
  | 'remote-hangup'
  | 'timeout';

class CallStateMachine {
  private state: CallState = 'idle';
  private listeners: Set<(state: CallState, prev: CallState) => void> = new Set();

  transition(event: CallEvent): boolean {
    const next = this.getNextState(event);
    if (!next) return false; // invalid transition
    const prev = this.state;
    this.state = next;
    this.listeners.forEach(fn => fn(next, prev));
    return true;
  }

  // Defineste TOATE tranzitiile valide
  private getNextState(event: CallEvent): CallState | null {
    const transitions: Record<CallState, Partial<Record<CallEvent, CallState>>> = {
      'idle': {
        'initiate-call': 'calling',
        'receive-call': 'ringing',
      },
      'calling': {
        'remote-accept': 'connecting',
        'local-hangup': 'ended',
        'remote-hangup': 'ended',
        'timeout': 'ended',
      },
      'ringing': {
        'local-accept': 'connecting',
        'local-hangup': 'ended',
        'remote-hangup': 'ended',
        'timeout': 'ended',
      },
      'connecting': {
        'ice-connected': 'connected',
        'ice-failed': 'ended',
        'local-hangup': 'ended',
        'remote-hangup': 'ended',
        'timeout': 'ended',
      },
      'connected': {
        'ice-disconnected': 'reconnecting',
        'audio-interrupted': 'on-hold',
        'local-hangup': 'ended',
        'remote-hangup': 'ended',
      },
      'reconnecting': {
        'ice-restart-success': 'connected',
        'ice-failed': 'ended',
        'local-hangup': 'ended',
        'remote-hangup': 'ended',
        'timeout': 'ended',
      },
      'on-hold': {
        'audio-resumed': 'connected',
        'local-hangup': 'ended',
        'remote-hangup': 'ended',
        'timeout': 'ended',
      },
      'ended': {}, // terminal state
    };
    return transitions[this.state]?.[event] ?? null;
  }
}
```

### TASK 2: CallKit in Foreground — FIX CRITIC

**Problema actuala:** In `App.tsx`, cand app e foreground, incoming calls arata doar `IncomingCallOverlay` (component React). Apple Watch, AirPods, CarPlay NU vad apelul.

**Solutia WhatsApp:** CallKit se foloseste MEREU, inclusiv in foreground.

**Modificari necesare:**

In `App.tsx`, handlerul `incoming-call`:
```typescript
// INAINTE (gresit):
if (appState === 'active') {
  // Arata IncomingCallOverlay — NU CallKit
  showOverlay(callerName);
}

// DUPA (corect — ca WhatsApp):
// MEREU foloseste CallKit, indiferent de app state
CallKitService.reportIncomingCall(contactId, callerName, isVideo, offer);
// CallKit arata native UI pe Apple Watch, AirPods, lock screen, etc.
// IncomingCallOverlay devine OPTIONAL — doar pentru custom UI in-app
```

In `AppDelegate.swift`, pentru VoIP push cand app e active:
```swift
// INAINTE: report + end silently (gresit pentru appuri cu CallKit serios)
// DUPA: report normal — JS side gestioneaza dedup-ul
if application.applicationState == .active {
  // Tot reporteaza — CallKit gestioneaza UI-ul
  // JS side va vedea ca deja are acest call si va skip duplicate
  RNCallKeep.reportNewIncomingCall(...)
  completion()
  return
}
```

### TASK 3: Video Toggle Mid-Call (`WebRTCManager.ts`)

**Approach: Pre-negotiate + replaceTrack** (pattern WhatsApp — FARA renegociere SDP)

Modificari in `WebRTCManager.ts`:

```typescript
// La initializarea PeerConnection (startCall/answerCall):
// Adauga MEREU un transceiver video, chiar daca apelul e audio-only
const audioTransceiver = pc.addTransceiver('audio', { direction: 'sendrecv' });
const videoTransceiver = pc.addTransceiver('video', {
  direction: isVideo ? 'sendrecv' : 'inactive'
});

// Toggle video MID-CALL (fara renegociere SDP):
async toggleVideo(contactId: string, enable: boolean): Promise<boolean> {
  const peer = this.peers.get(contactId);
  if (!peer?.connection) return false;

  const videoTransceiver = peer.connection.getTransceivers()
    .find(t => t.receiver.track?.kind === 'video' || t.sender.track?.kind === 'video');

  if (!videoTransceiver) return false;

  if (enable) {
    // Porneste camera si inlocuieste track-ul
    const stream = await mediaDevices.getUserMedia({
      video: { facingMode: this.cameraFacing }
    });
    const videoTrack = stream.getVideoTracks()[0];
    await videoTransceiver.sender.replaceTrack(videoTrack);
    videoTransceiver.direction = 'sendrecv';

    // Notifica remote peer prin signaling (custom event, nu SDP)
    this.signalingClient.send({
      type: 'video-toggle',
      to: contactId,
      enabled: true,
    });
    return true;
  } else {
    // Opreste video
    videoTransceiver.sender.track?.stop();
    await videoTransceiver.sender.replaceTrack(null);
    videoTransceiver.direction = 'inactive';

    this.signalingClient.send({
      type: 'video-toggle',
      to: contactId,
      enabled: false,
    });
    return true;
  }
}

// Camera flip (front/rear) — replaceTrack, FARA renegociere:
async flipCamera(contactId: string): Promise<void> {
  this.cameraFacing = this.cameraFacing === 'user' ? 'environment' : 'user';
  const stream = await mediaDevices.getUserMedia({
    video: { facingMode: this.cameraFacing }
  });
  const newTrack = stream.getVideoTracks()[0];

  const peer = this.peers.get(contactId);
  const videoSender = peer?.connection?.getSenders()
    .find(s => s.track?.kind === 'video');
  if (videoSender) {
    const oldTrack = videoSender.track;
    await videoSender.replaceTrack(newTrack);
    oldTrack?.stop();
  }
}
```

**Server-side** (`server/index.js`) — adauga relay pentru `video-toggle`:
```javascript
socket.on('video-toggle', ({ to, enabled }) => {
  forwardToUser(to, {
    type: 'video-toggle',
    from: socket.userId,
    enabled,
  });
});
```

### TASK 4: Reconnection UI + Timeout Fix (`CallScreen.tsx`)

**Probleme:**
- 10s disconnect timeout e prea agresiv (WhatsApp: 30-60s)
- NU exista "Reconnecting..." in UI

**Modificari in `CallScreen.tsx`:**

```typescript
// Timeout-uri (inspirate din WhatsApp):
const TIMEOUTS = {
  RING: 60_000,           // 60s — cit suna inainte de "No Answer" (deja existent)
  CONNECT: 30_000,        // 30s — ICE negotiation timeout
  RECONNECT: 30_000,      // 30s — de la disconnect pina la drop (ERA 10s!)
  ICE_RESTART_DELAY: 3_000, // 3s — delay inainte de ICE restart (deja existent)
};

// State-ul de reconnecting:
const [callState, setCallState] = useState<CallState>('idle');
// Inlocuieste callStatus string cu CallStateMachine

// In UI:
{callState === 'reconnecting' && (
  <View style={styles.reconnectingBanner}>
    <ActivityIndicator color="#fff" />
    <Text style={styles.reconnectingText}>Reconnecting...</Text>
  </View>
)}

// Handler disconnect:
const onCallDisconnected = useCallback(() => {
  if (callStateMachine.transition('ice-disconnected')) {
    // Arata "Reconnecting..." in UI
    setCallState('reconnecting');
    // 30s timeout (nu 10s!)
    reconnectTimeoutRef.current = setTimeout(() => {
      finishAndGoBack(durationRef.current, true);
    }, TIMEOUTS.RECONNECT);
  }
}, []);

const onCallReconnected = useCallback(() => {
  if (callStateMachine.transition('ice-restart-success')) {
    setCallState('connected');
    clearTimeout(reconnectTimeoutRef.current);
  }
}, []);
```

### TASK 5: Perfect Negotiation Pattern (`WebRTCManager.ts`)

**Implementeaza polite/impolite peer complet:**

```typescript
// Determina rolurile (deterministic, bazat pe userId):
private isPolite(localId: string, remoteId: string): boolean {
  return localId < remoteId; // lexicografic mai mic = polite
}

// In handleOffer():
async handleOffer(fromId: string, payload: any) {
  const peer = this.peers.get(fromId);
  if (!peer) return;
  const pc = peer.connection;

  const polite = this.isPolite(this.localUserId, fromId);
  const offerCollision = peer.makingOffer ||
    pc.signalingState !== 'stable';

  if (!polite && offerCollision) {
    // Impolite: ignora offer-ul incoming, pastreaza-l pe al nostru
    console.log('[WebRTC] Ignoring colliding offer (impolite peer)');
    return;
  }

  if (offerCollision) {
    // Polite: rollback propriul offer si accepta incoming
    console.log('[WebRTC] Rolling back own offer (polite peer)');
    await pc.setLocalDescription({ type: 'rollback' });
  }

  await pc.setRemoteDescription(new RTCSessionDescription(payload));
  const answer = await pc.createAnswer();
  await pc.setLocalDescription(answer);
  this.signalingClient.sendAnswer(fromId, answer);
}

// Guard makingOffer in createOffer:
async createOffer(contactId: string) {
  const peer = this.peers.get(contactId);
  if (!peer) return;
  try {
    peer.makingOffer = true;
    const offer = await peer.connection.createOffer({
      offerToReceiveAudio: true,
      offerToReceiveVideo: true, // MEREU — pentru pre-negotiated video
    });
    if (peer.connection.signalingState !== 'stable') return;
    await peer.connection.setLocalDescription(offer);
    this.signalingClient.sendOffer(contactId, offer);
  } finally {
    peer.makingOffer = false;
  }
}
```

### TASK 6: Opus Codec Optimization

In `WebRTCManager.ts`, dupa crearea PeerConnection:

```typescript
// Seteaza preferinte codec INAINTE de createOffer/createAnswer:
private configureCodecPreferences(pc: RTCPeerConnection) {
  const transceivers = pc.getTransceivers();
  for (const transceiver of transceivers) {
    if (transceiver.receiver.track?.kind === 'audio') {
      try {
        const codecs = RTCRtpReceiver.getCapabilities('audio')?.codecs || [];
        const opus = codecs.filter(c => c.mimeType === 'audio/opus');
        if (opus.length > 0) {
          transceiver.setCodecPreferences(opus);
        }
      } catch (e) {
        // Fallback: SDP munging
        console.log('[WebRTC] setCodecPreferences not supported, using SDP munging');
      }
    }
  }
}

// SDP munging fallback (Opus FEC + DTX):
private optimizeSdpForOpus(sdp: string): string {
  return sdp.replace(
    /(a=fmtp:\d+ .*)/g,
    (match) => {
      if (!match.includes('useinbandfec')) {
        match += ';useinbandfec=1';
      }
      if (!match.includes('dtx')) {
        match += ';dtx=1';
      }
      return match;
    }
  );
}
```

### TASK 7: Network Change Detection (Proactiv)

Adauga NetInfo listener in `WebRTCManager.ts`:

```typescript
import NetInfo from '@react-native-community/netinfo';

// In constructor/init:
this.netInfoUnsubscribe = NetInfo.addEventListener(state => {
  if (this.hasActiveCall() && state.isConnected) {
    // Network changed (WiFi -> Cellular sau invers)
    // Trigger proactive ICE restart pe toate peer connections active
    for (const [contactId, peer] of this.peers) {
      if (peer.connected && peer.connection.connectionState === 'connected') {
        console.log(`[WebRTC] Network change detected, proactive ICE restart for ${contactId}`);
        this.performIceRestart(contactId);
      }
    }
  }
});

// Cleanup:
destroy() {
  this.netInfoUnsubscribe?.();
}
```

### TASK 8: VoIP Push Payload Optimization

In `server/push.js`:

```javascript
// SDP Minification (reduce de la ~2KB la ~1.2KB):
function minifySdp(sdp) {
  return sdp
    .split('\r\n')
    .filter(line => {
      // Pastreaza doar liniile esentiale:
      if (line.startsWith('v=')) return true;
      if (line.startsWith('o=')) return true;
      if (line.startsWith('s=')) return true;
      if (line.startsWith('t=')) return true;
      if (line.startsWith('m=')) return true;
      if (line.startsWith('c=')) return true;
      if (line.startsWith('a=rtpmap:')) return true;
      if (line.startsWith('a=fmtp:')) return true;
      if (line.startsWith('a=ice-ufrag:')) return true;
      if (line.startsWith('a=ice-pwd:')) return true;
      if (line.startsWith('a=fingerprint:')) return true;
      if (line.startsWith('a=setup:')) return true;
      if (line.startsWith('a=mid:')) return true;
      if (line.startsWith('a=sendrecv')) return true;
      if (line.startsWith('a=recvonly')) return true;
      if (line.startsWith('a=group:')) return true;
      if (line.startsWith('a=msid:')) return true;
      if (line.startsWith('a=ssrc:')) return true;
      return false;
    })
    .join('\r\n') + '\r\n';
}

// Validare payload size:
function buildVoIPPayload(callerName, isVideo, sdp, turnServers) {
  const minifiedSdp = minifySdp(sdp);

  const payload = {
    from: callerId,
    callerName: callerName.substring(0, 50), // limit name
    isVideo,
    sdp: minifiedSdp,
    turn: turnServers.map(t => ({
      u: t.urls[0],    // compact key names
      n: t.username,
      c: t.credential,
    })),
  };

  const size = Buffer.byteLength(JSON.stringify(payload));
  if (size > 4800) { // 4.8KB safety margin (APNs limit 5KB)
    // Remove SDP from push — callee will use PATH B (get-call-state)
    delete payload.sdp;
    console.warn(`VoIP push payload too large (${size} bytes), SDP removed`);
  }

  return payload;
}
```

### TASK 9: Server-side — Video Toggle + Call Quality Events

In `server/index.js`, adauga:

```javascript
// Video toggle relay:
socket.on('video-toggle', ({ to, enabled }) => {
  const targetSocket = findSocket(to);
  if (targetSocket) {
    targetSocket.emit('video-toggle', {
      from: socket.userId,
      enabled,
    });
  }
});

// Call quality reporting (CDR — Call Detail Record):
socket.on('call-quality-report', ({ contactId, duration, stats }) => {
  // Store pentru analytics
  console.log(`[CDR] ${socket.userId} -> ${contactId}: ${duration}s, ` +
    `RTT=${stats.rtt}ms, loss=${stats.packetLoss}%, path=${stats.path}`);
  // Optional: save to database pentru diagnostics
});
```

### TASK 10: CallScreen Video UI

In `CallScreen.tsx`, adauga butoane video:

```typescript
// State:
const [isVideoEnabled, setIsVideoEnabled] = useState(isVideo);
const [isFrontCamera, setIsFrontCamera] = useState(true);
const [remoteVideoEnabled, setRemoteVideoEnabled] = useState(false);

// Toggle video:
const handleToggleVideo = async () => {
  const result = await WebRTCManager.toggleVideo(contactId, !isVideoEnabled);
  if (result) setIsVideoEnabled(!isVideoEnabled);
};

// Flip camera:
const handleFlipCamera = async () => {
  await WebRTCManager.flipCamera(contactId);
  setIsFrontCamera(!isFrontCamera);
};

// Listen for remote video toggle:
useEffect(() => {
  const handler = (data: { from: string; enabled: boolean }) => {
    if (data.from === contactId) {
      setRemoteVideoEnabled(data.enabled);
    }
  };
  signalingClient.on('video-toggle', handler);
  return () => signalingClient.off('video-toggle', handler);
}, [contactId]);

// UI — butoane in call controls:
<View style={styles.callControls}>
  <TouchableOpacity onPress={handleToggleMute}>
    <Icon name={isMuted ? 'mic-off' : 'mic'} />
  </TouchableOpacity>

  <TouchableOpacity onPress={handleToggleVideo}>
    <Icon name={isVideoEnabled ? 'videocam' : 'videocam-off'} />
  </TouchableOpacity>

  {isVideoEnabled && (
    <TouchableOpacity onPress={handleFlipCamera}>
      <Icon name="flip-camera" />
    </TouchableOpacity>
  )}

  <TouchableOpacity onPress={handleToggleSpeaker}>
    <Icon name={isSpeaker ? 'volume-up' : 'volume-down'} />
  </TouchableOpacity>

  <TouchableOpacity onPress={handleHangup} style={styles.hangupButton}>
    <Icon name="call-end" color="white" />
  </TouchableOpacity>
</View>

// Video views:
{(isVideoEnabled || remoteVideoEnabled) && (
  <View style={styles.videoContainer}>
    {remoteVideoEnabled && remoteStream && (
      <RTCView
        streamURL={remoteStream.toURL()}
        style={styles.remoteVideo}
        objectFit="cover"
      />
    )}
    {isVideoEnabled && localStream && (
      <RTCView
        streamURL={localStream.toURL()}
        style={styles.localVideo}
        objectFit="cover"
        mirror={isFrontCamera}
      />
    )}
  </View>
)}
```

### TASK 11: Reduce Incoming Call Debounce

In `MessagingService.ts`:

```typescript
// INAINTE: 600ms debounce pe TOATE incoming calls (perceptibil)
// DUPA: 200ms debounce (suficient pentru call-ended check, imperceptibil)

const INCOMING_CALL_DEBOUNCE = 200; // redus de la 600ms

// + Skip debounce complet daca userul deja a raspuns pe CallKit (cold start):
if (ColdStartCoordinator.hasAnswer) {
  // Zero debounce — userul deja raspunde
  this.processIncomingCall(offer, callerName, contactId, isVideo);
  return;
}
```

### TASK 12: Call Analytics (CDR)

In `CallScreen.tsx`, la terminarea apelului:

```typescript
// Salveaza CDR in baza de date locala:
const callRecord = {
  contactId,
  direction: isIncoming ? 'incoming' : 'outgoing',
  isVideo,
  duration: durationRef.current,
  startTime: callStartTime,
  endTime: Date.now(),
  endReason: reason, // 'local-hangup' | 'remote-hangup' | 'timeout' | 'ice-failed'
  coldStartPath: ColdStartCoordinator.getDiagnosticSummary()?.path,
  quality: {
    avgRtt: qualityStats.avgRtt,
    maxRtt: qualityStats.maxRtt,
    packetLoss: qualityStats.totalPacketLoss,
    iceRestarts: qualityStats.iceRestartCount,
  },
};

// Save to SQLite
await Database.saveCallRecord(callRecord);

// Report to server (anonymous, pentru diagnostics):
signalingClient.send({
  type: 'call-quality-report',
  contactId: contactId,
  duration: durationRef.current,
  stats: callRecord.quality,
});
```

---

## ORDINEA DE IMPLEMENTARE (STRICT)

```
Faza 1 — Critice (blocheaza UX):
  1. CallStateMachine.ts (TASK 1) — fundatia pentru tot restul
  2. CallKit in foreground (TASK 2) — Apple Watch/AirPods/CarPlay
  3. Reconnection UI + timeout 30s (TASK 4) — opritea call drops
  4. Reduce debounce 200ms (TASK 11) — latenta incoming calls

Faza 2 — Video (feature major):
  5. Video toggle mid-call (TASK 3) — replaceTrack, pre-negotiate
  6. CallScreen video UI (TASK 10) — butoane, RTCView
  7. Server video-toggle relay (TASK 9) — socket.on('video-toggle')

Faza 3 — Calitate (polish):
  8. Perfect Negotiation (TASK 5) — glare resolution complet
  9. Opus optimization (TASK 6) — FEC + DTX
  10. Network change detection (TASK 7) — NetInfo proactiv
  11. VoIP push optimization (TASK 8) — SDP minification, size validation

Faza 4 — Analytics:
  12. Call analytics CDR (TASK 12) — diagnostics
```

---

## FLOW-URI COMPLETE DUPA IMPLEMENTARE

### Outgoing Call (Audio):
```
User taps Call -> CallStateMachine.transition('initiate-call') -> state='calling'
  -> CallKitService.startCall(uuid)
  -> CallKit activates audio
  -> RTCAudioBridge.activateAudioSession()
  -> getUserMedia(audio) + pre-negotiate video transceiver (inactive)
  -> WebRTCManager.startCall() -> createOffer (offerToReceiveVideo: true)
  -> SDP optimized (Opus FEC+DTX) -> send via SignalingClient
  -> Server relays or sends VoIP push
  -> Wait for answer...
  -> Answer received -> CallStateMachine.transition('remote-accept') -> state='connecting'
  -> setRemoteDescription(answer) -> drain ICE queue
  -> ICE connected -> CallStateMachine.transition('ice-connected') -> state='connected'
  -> Timer starts, quality monitoring begins
```

### Incoming Call (App Killed — Cold Start):
```
VoIP push -> AppDelegate.didReceiveIncomingPush
  -> Parse payload (callerName, SDP minified, TURN compact)
  -> Store in UserDefaults
  -> reportNewIncomingCall() IMMEDIATE (< 100ms)
  -> CallKit native UI appears (lock screen, Apple Watch, AirPods)
  -> User taps Answer
  -> CallKit activates audio -> RTCAudioBridge.activateAudioSession()
  -> index.js: didLoadWithEvents -> ColdStartCoordinator.setAnswerUUID()
  -> App.tsx mounts -> ColdStartCoordinator.run()
  -> PATH A: Read SDP from UserDefaults (20ms)
  -> Navigate to CallScreen
  -> CallStateMachine.transition('local-accept') -> state='connecting'
  -> getUserMedia(audio) + pre-negotiate video transceiver
  -> WebRTCManager.answerCall() -> setRemoteDescription -> createAnswer
  -> ICE connected -> state='connected'
```

### Video Toggle Mid-Call:
```
User taps Video button -> handleToggleVideo()
  -> WebRTCManager.toggleVideo(contactId, true)
  -> getUserMedia(video, facingMode: 'user')
  -> videoTransceiver.sender.replaceTrack(newVideoTrack) -- NO SDP renegotiation!
  -> videoTransceiver.direction = 'sendrecv'
  -> signalingClient.send('video-toggle', enabled: true)
  -> Remote receives 'video-toggle' -> setRemoteVideoEnabled(true)
  -> RTCView renders remote video
  -> User can flip camera (replaceTrack with new facing mode)
  -> User taps Video off -> replaceTrack(null), direction='inactive'
```

### Network Change (WiFi -> Cellular):
```
NetInfo detects change -> proactive ICE restart
  -> CallStateMachine.transition('ice-disconnected') -> state='reconnecting'
  -> UI shows "Reconnecting..." banner
  -> performIceRestart() -> createOffer(iceRestart: true)
  -> New ICE candidates gathered (continualGatheringPolicy)
  -> TURN relay fallback (relay-first strategy)
  -> ICE connected -> CallStateMachine.transition('ice-restart-success') -> state='connected'
  -> "Reconnecting..." banner hidden
  -> Timeout 30s daca nu se reconecteaza
```

---

## REGULI DE IMPLEMENTARE

1. **NU rescrie** ce functioneaza deja — modifica DOAR ce e necesar
2. **Testeaza pe dispozitiv real** (iPhone fizic) dupa fiecare modificare
3. **Testeaza COLD START** — kill app, trimite VoIP push, verifica ca apelul apare
4. **Testeaza network switch** — porneste pe WiFi, comuta pe cellular mid-call
5. **Testeaza audio** — verifica ca audio functioneaza pe earpiece, speaker, Bluetooth
6. **Testeaza video toggle** — porneste audio, toggle video on/off, flip camera
7. **Incrementeaza BUILD NUMBER** dupa fiecare schimbare
8. **NU face push fara aprobare**
9. **CallKit e OBLIGATORIU** pentru TOATE incoming calls (inclusiv foreground)
10. **30s timeout** pe reconnect (nu 10s)
11. **replaceTrack** pentru video toggle (nu renegociere SDP)
12. **Pre-negotiate** video transceiver la initializare (chiar pt audio calls)
13. **Opus FEC+DTX** activat mereu
14. **SDP minified** in VoIP push (sub 4.8KB total payload)
