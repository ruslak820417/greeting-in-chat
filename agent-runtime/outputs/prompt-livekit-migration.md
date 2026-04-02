# PROMPT: QRChat — Migrare Call System la LiveKit (Build 300)

## OBIECTIV

Înlocuiește complet sistemul manual de apeluri (WebRTC + CallKit + VoIP push + audio session) cu **LiveKit SDK**, care gestionează totul nativ: signaling, TURN/STUN, PushKit/CallKit, audio session, cold start.

Mesajele text, criptarea E2E, și serverul Node.js pentru chat rămân neatinse.

**Proiect:** `/Users/ruslanconstantinovici/QRChat`
**Branch:** `feature/livekit-calls`
**Baza:** main (Build 203 sau ultimul stabil)
**Fallback:** `git checkout main`
**Build final:** 300 (seria 300 = LiveKit)
**Tech stack:** React Native 0.84, TypeScript, Node.js server, TweetNaCl, WebRTC, SQLite

---

## DE CE MIGRĂM

Sistemul actual de apeluri are 6 buguri critice identificate, toate cauzate de gestionarea manuală a:
- PushKit/CallKit lifecycle (cold start)
- AVAudioSession (useManualAudio, InCallManager, RTCAudioBridge — 3 sisteme în conflict)
- WebRTC signaling (SDP offer/answer, ICE candidates)
- VoIP push delivery (token management, duplicate notifications)
- Navigation timing (splash block, NavigationService queue)

LiveKit SDK rezolvă TOATE aceste probleme cu o singură integrare.

---

## CE SE ELIMINĂ (4446 linii de cod manual)

| Fișier | Linii | Ce face | Înlocuit de |
|--------|-------|---------|-------------|
| `src/network/WebRTCManager.ts` | 1000 | WebRTC manual, signaling, P2P data + calls | LiveKit SDK (calls), păstrează data channel |
| `src/services/CallKitService.ts` | 233 | CallKit management manual | LiveKit CallKit integration |
| `src/services/ColdStartCoordinator.ts` | 421 | Cold start 3-path SDP retrieval | LiveKit push handling |
| `src/screens/CallScreen.tsx` | 1179 | UI + WebRTC + audio management | Nou CallScreen cu LiveKit |
| `server/push.js` (doar VoIP part) | ~200 | VoIP push APNs manual | LiveKit server push |
| `ios/QRChat/RTCAudioBridge.swift` | 43 | Audio session bridge manual | LiveKit audio management |
| `index.js` call listeners | ~50 | didLoadWithEvents, answerCall guards | LiveKit native handling |

## CE SE PĂSTREAZĂ (neatins)

| Component | Fișier | De ce |
|-----------|--------|-------|
| Mesaje E2E | `src/services/MessagingService.ts` | Chat funcționează independent de calls |
| Double Ratchet | `src/crypto/DoubleRatchet.ts` | Criptare mesaje neatinsă |
| P2P Data Channel | `src/network/WebRTCManager.ts` (partial) | Se păstrează `connectToPeer`, `sendMessage`, `onMessage` pentru chat P2P |
| Server chat | `server/index.js` | Relay mesaje, register, status online |
| Push mesaje | `server/push.js` (silent push part) | Notificări mesaje text |
| SignalingClient | `src/network/SignalingClient.ts` | WebSocket pentru chat + status |
| Toate ecranele | `src/screens/*` (minus CallScreen) | UI chat neatins |
| i18n | `src/i18n/locales/*` | Doar stringuri call noi |
| Storage | `src/storage/Database.ts` | SQLite neatins |

---

## REGULI OBLIGATORII PENTRU TOȚI AGENȚII

1. **Citește fișierul ÎNAINTE de a-l modifica** — nu presupune structura
2. **Updatează `agent-runtime/state/status.md`** când începi/finalizezi o sarcină
3. **Dacă depinzi de alt agent** — scrie în `agent-runtime/messages/` și marchează BLOCKED
4. **Nu face push la git** fără aprobarea lead-ului
5. **Nu modifica fișiere din domeniul altui agent**
6. **Testează compilarea** după fiecare modificare (`npx tsc --noEmit`)
7. **Nu adaugă dependențe npm** fără aprobarea lead-ului (excepție: LiveKit SDK — pre-aprobat)
8. **Scrie cod TypeScript strict** — fără `any`, fără `@ts-ignore`
9. **Comentarii în engleză**, referă documentația LiveKit, nu alte produse
10. **Toate modificările pe branch** `feature/livekit-calls`, NICIODATĂ pe main
11. **Nu atinge** MessagingService, DoubleRatchet, Database, sau alte componente de chat
12. **Commit messages** descriptive: "Replace manual WebRTC with LiveKit Room"

---

## FAZA 0 — SETUP (architect — SINGUR)

### Agent: architect

#### 0.1 Instalare LiveKit SDK
```bash
cd /Users/ruslanconstantinovici/QRChat
npm install @livekit/react-native @livekit/react-native-webrtc
# iOS
cd ios && pod install && cd ..
```

**Verificare:**
- `npx tsc --noEmit` — zero erori
- `pod install` fără erori
- Importul `import { Room, RoomEvent } from '@livekit/react-native'` compilează

#### 0.2 LiveKit Server Setup
**Opțiuni (alege UNA):**

**A) LiveKit Cloud (recomandat pentru start rapid):**
- Crează cont pe https://cloud.livekit.io (free tier: 50 participanți simultani)
- Obține `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `LIVEKIT_URL`
- Adaugă în Railway env vars

**B) Self-hosted pe Railway (recomandat pentru producție):**
- Adaugă serviciu nou pe Railway: Docker image `livekit/livekit-server`
- Env vars: `LIVEKIT_KEYS="APIKey: secret"`, port 7880
- Generează API key/secret cu `livekit-cli create-key`

#### 0.3 Token Service pe Server
**Fișier NOU:** `server/livekit.js`
```javascript
const { AccessToken } = require('livekit-server-sdk');

const LIVEKIT_API_KEY = process.env.LIVEKIT_API_KEY;
const LIVEKIT_API_SECRET = process.env.LIVEKIT_API_SECRET;

/**
 * Generate LiveKit access token for a user to join a call room.
 * Room name = sorted(callerId, calleeId) — ensures both join same room.
 * Token grants: room join, publish audio/video, subscribe.
 */
function generateCallToken(userId, roomName, callerName) {
  const token = new AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET, {
    identity: userId,
    name: callerName,
    ttl: 300, // 5 minutes
  });
  token.addGrant({
    roomJoin: true,
    room: roomName,
    canPublish: true,
    canSubscribe: true,
    canPublishData: true,
  });
  return token.toJwt();
}

module.exports = { generateCallToken };
```

#### 0.4 Server Endpoint pentru Call Tokens
**Fișier:** `server/index.js` — adaugă handler NOU (NU modifica handlerii existenți)
```javascript
// LIVEKIT: Generate call token
case 'request-call-token': {
  const { generateCallToken } = require('./livekit');
  const roomName = [userId, message.targetUserId].sort().join('-');
  const token = generateCallToken(userId, roomName, message.callerName || 'Unknown');
  ws.send(JSON.stringify({
    type: 'call-token',
    token: token,
    roomName: roomName,
    livekitUrl: process.env.LIVEKIT_URL,
  }));
  // Also notify callee
  const calleeClient = clients.get(message.targetUserId);
  if (calleeClient && calleeClient.readyState === WebSocket.OPEN) {
    const calleeToken = generateCallToken(message.targetUserId, roomName, '');
    calleeClient.send(JSON.stringify({
      type: 'incoming-livekit-call',
      from: userId,
      callerName: message.callerName || 'Unknown',
      isVideo: message.isVideo || false,
      roomName: roomName,
      token: calleeToken,
      livekitUrl: process.env.LIVEKIT_URL,
    }));
  }
  // VoIP push for offline callee
  if (!calleeClient || calleeClient.readyState !== WebSocket.OPEN) {
    const { sendVoIPPush } = require('./push');
    sendVoIPPush(message.targetUserId, userId, {
      callerName: message.callerName || 'Unknown',
      isVideo: message.isVideo || false,
      roomName: roomName,
    });
  }
  // ALWAYS send VoIP push (even if online — covers WS disconnect race)
  const { sendVoIPPush } = require('./push');
  sendVoIPPush(message.targetUserId, userId, {
    callerName: message.callerName || 'Unknown',
    isVideo: message.isVideo || false,
    roomName: roomName,
  });
  break;
}
```

**Rezultat:** Scrie raport în `agent-runtime/outputs/architect-livekit-setup-report.md`

---

### CHECKPOINT FAZA 0
- [ ] LiveKit SDK instalat, pod install OK
- [ ] LiveKit server accesibil (cloud sau self-hosted)
- [ ] `request-call-token` handler funcționează pe server
- [ ] Token-ul se generează corect (test manual cu curl)
- [ ] `npx tsc --noEmit` — zero erori

---

## FAZA 1 — LIVEKIT CALL SERVICE (network-engineer + security-engineer — PARALEL)

### Agent: network-engineer

#### 1.1 LiveKit Call Service
**Fișier NOU:** `src/services/LiveKitCallService.ts`

Serviciu nou care înlocuiește WebRTCManager pentru CALLS (nu pentru data channel):

```typescript
import { Room, RoomEvent, Track, TrackPublication } from '@livekit/react-native';
import SignalingClient from '../network/SignalingClient';
import { Log, LogCategory } from './LogService';

class LiveKitCallService {
  private room: Room | null = null;
  private livekitUrl: string = '';

  // Callbacks for CallScreen
  private onRemoteTrackCb: ((track: Track) => void) | null = null;
  private onConnectedCb: (() => void) | null = null;
  private onDisconnectedCb: ((reason: string) => void) | null = null;

  /**
   * Start an outgoing call.
   * 1. Request token from server via WebSocket
   * 2. Create LiveKit Room
   * 3. Connect to room
   * 4. Publish local audio/video tracks
   */
  async startCall(contactId: string, contactName: string, isVideo: boolean): Promise<void> {
    // Request token from server
    const { token, roomName, livekitUrl } = await this.requestCallToken(contactId, contactName, isVideo);
    this.livekitUrl = livekitUrl;

    // Create and connect room
    this.room = new Room();
    this.setupRoomListeners();
    await this.room.connect(livekitUrl, token);

    // Publish local tracks
    await this.room.localParticipant.enableMicrophone();
    if (isVideo) {
      await this.room.localParticipant.enableCamera();
    }

    Log.info(LogCategory.CALL, `LiveKit call started: room=${roomName}`);
  }

  /**
   * Accept an incoming call.
   * Token and room info arrive via WebSocket or VoIP push.
   */
  async acceptCall(token: string, livekitUrl: string, isVideo: boolean): Promise<void> {
    this.livekitUrl = livekitUrl;
    this.room = new Room();
    this.setupRoomListeners();
    await this.room.connect(livekitUrl, token);

    await this.room.localParticipant.enableMicrophone();
    if (isVideo) {
      await this.room.localParticipant.enableCamera();
    }

    Log.info(LogCategory.CALL, `LiveKit call accepted`);
  }

  /**
   * End the current call.
   */
  async endCall(): Promise<void> {
    if (this.room) {
      await this.room.disconnect();
      this.room = null;
    }
    Log.info(LogCategory.CALL, `LiveKit call ended`);
  }

  /**
   * Toggle microphone mute.
   */
  async toggleMute(): Promise<boolean> {
    if (!this.room) return false;
    const enabled = this.room.localParticipant.isMicrophoneEnabled;
    await this.room.localParticipant.setMicrophoneEnabled(!enabled);
    return !enabled;
  }

  /**
   * Toggle speaker/earpiece.
   */
  async toggleSpeaker(): Promise<void> {
    // LiveKit handles audio routing via native iOS APIs
    // Use InCallManager.setSpeakerphoneOn() for explicit control
  }

  /**
   * Toggle camera (video calls).
   */
  async toggleCamera(): Promise<boolean> {
    if (!this.room) return false;
    const enabled = this.room.localParticipant.isCameraEnabled;
    await this.room.localParticipant.setCameraEnabled(!enabled);
    return !enabled;
  }

  /**
   * Switch front/back camera.
   */
  async switchCamera(): Promise<void> {
    if (!this.room) return;
    const cameraPub = this.room.localParticipant.getTrackPublication(Track.Source.Camera);
    if (cameraPub?.track) {
      // @ts-ignore — switchCamera exists on video tracks
      await cameraPub.track.switchCamera();
    }
  }

  // ---- Callbacks ----
  onRemoteTrack(cb: (track: Track) => void) { this.onRemoteTrackCb = cb; }
  onConnected(cb: () => void) { this.onConnectedCb = cb; }
  onDisconnected(cb: (reason: string) => void) { this.onDisconnectedCb = cb; }

  // ---- Internal ----
  private setupRoomListeners() {
    if (!this.room) return;

    this.room.on(RoomEvent.Connected, () => {
      Log.info(LogCategory.CALL, 'LiveKit room connected');
      this.onConnectedCb?.();
    });

    this.room.on(RoomEvent.Disconnected, (reason) => {
      Log.info(LogCategory.CALL, `LiveKit room disconnected: ${reason}`);
      this.onDisconnectedCb?.(reason || 'unknown');
    });

    this.room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
      Log.info(LogCategory.CALL, `Remote track subscribed: ${track.kind}`);
      this.onRemoteTrackCb?.(track);
    });

    this.room.on(RoomEvent.TrackUnsubscribed, (track) => {
      Log.info(LogCategory.CALL, `Remote track unsubscribed: ${track.kind}`);
    });
  }

  private requestCallToken(contactId: string, contactName: string, isVideo: boolean): Promise<{token: string, roomName: string, livekitUrl: string}> {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('Token request timeout')), 10000);

      const handler = (msg: any) => {
        if (msg.type === 'call-token') {
          clearTimeout(timeout);
          SignalingClient.off('call-token', handler);
          resolve({ token: msg.token, roomName: msg.roomName, livekitUrl: msg.livekitUrl });
        }
      };
      SignalingClient.on('call-token', handler);

      SignalingClient.send({
        type: 'request-call-token',
        targetUserId: contactId,
        callerName: contactName,
        isVideo: isVideo,
      });
    });
  }

  // ---- Getters ----
  get isConnected(): boolean { return this.room?.state === 'connected'; }
  get localParticipant() { return this.room?.localParticipant; }
  get remoteParticipants() { return this.room?.remoteParticipants; }
}

export default new LiveKitCallService();
```

#### 1.2 VoIP Push cu LiveKit Room Info
**Fișier:** `server/push.js` — modifică `sendVoIPPush`
- Adaugă `roomName` în payload-ul VoIP push (pe lângă callerName, isVideo)
- NU mai trimite SDP în push (LiveKit nu folosește SDP manual)
- NU mai trimite TURN servers (LiveKit gestionează intern)
- Payload VoIP devine minimal: `{ type: 'incoming-call', from, callerName, isVideo, roomName }`

#### 1.3 AppDelegate — VoIP Push cu LiveKit
**Fișier:** `ios/QRChat/AppDelegate.swift`
- `didReceiveIncomingPushWith`: parsează `roomName` din payload
- Stochează `roomName` în `PendingVoIPCall` UserDefaults (pe lângă from, callerName, isVideo)
- `reportNewIncomingCall` rămâne la fel (CallKit nativ)
- **Elimină**: SDP parsing, TURN servers storage din push handler

**Rezultat:** Scrie raport în `agent-runtime/outputs/network-livekit-service-report.md`

---

### Agent: security-engineer

#### 1.4 Simplificare ColdStartCoordinator
**Fișier:** `src/services/ColdStartCoordinator.ts`
- Elimină cele 3 path-uri de SDP retrieval (PATH A, PATH B, PATH C) — LiveKit nu folosește SDP manual
- Păstrează:
  - `setAnswerUUID` / `consumeAnswerUUID` (CallKit answer tracking)
  - `setDeclineUUID` / `consumeDeclineUUID` (CallKit decline tracking)
  - `setAudioSessionActivated` (audio lifecycle)
  - `setCallData` (roomName + token din VoIP push)
  - `reset()`
- Noul `run()`:
  1. Citește `PendingVoIPCall` din UserDefaults → extrage `roomName`
  2. Solicită token de la server: `request-call-token` cu `roomName`
  3. Navighează la CallScreen cu `{ roomName, token, livekitUrl }`
  4. CallScreen se conectează la LiveKit Room
- **Reduce** de la 421 linii la ~100 linii

#### 1.5 Simplificare index.js
**Fișier:** `index.js`
- Elimină: `onAnswerCall`, `onEndCall` handlers cu `isActive` guard
- Păstrează: `didLoadWithEvents` (pentru CallKit events), `onDidActivateAudioSession`, `onDidDeactivateAudioSession`
- LiveKit SDK gestionează audio session intern, dar event listeners rămân pentru logging/diagnostics

#### 1.6 Elimină RTCAudioBridge
**Fișier:** `ios/QRChat/RTCAudioBridge.swift`, `ios/QRChat/RTCAudioBridge.m`
- **Șterge ambele fișiere** — LiveKit gestionează audio session
- **Elimină**: referințele din Xcode project (remove from Build Phases)
- **Elimină**: `NativeModules.RTCAudioBridge` din toate fișierele JS/TS

**Rezultat:** Scrie raport în `agent-runtime/outputs/security-livekit-simplification-report.md`

---

### CHECKPOINT FAZA 1
- [ ] `npx tsc --noEmit` — zero erori
- [ ] `LiveKitCallService.ts` compilează și exportă corect
- [ ] ColdStartCoordinator simplificat (<150 linii)
- [ ] index.js fără answerCall/endCall handlers
- [ ] RTCAudioBridge.swift șters
- [ ] VoIP push payload nu mai conține SDP/TURN

---

## FAZA 2 — CALLSCREEN REWRITE (frontend-engineer + network-engineer — PARALEL)

### Agent: frontend-engineer

#### 2.1 CallScreen NOU cu LiveKit
**Fișier:** `src/screens/CallScreen.tsx` — **rescrie complet** (1179 linii → ~400 linii)

Noul CallScreen:
```typescript
import React, { useEffect, useState, useRef } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { VideoView } from '@livekit/react-native';
import LiveKitCallService from '../services/LiveKitCallService';
import CallKitService from '../services/CallKitService';

const CallScreen = ({ route, navigation }) => {
  const { contactId, contactName, isVideo, isIncoming, token, livekitUrl, roomName } = route.params;
  const [callState, setCallState] = useState<'connecting' | 'connected' | 'ended'>('connecting');
  const [isMuted, setIsMuted] = useState(false);
  const [isSpeaker, setIsSpeaker] = useState(false);
  const [remoteVideoTrack, setRemoteVideoTrack] = useState(null);
  const [callDuration, setCallDuration] = useState(0);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // Setup callbacks
    LiveKitCallService.onConnected(() => {
      setCallState('connected');
      timerRef.current = setInterval(() => setCallDuration(d => d + 1), 1000);
    });
    LiveKitCallService.onDisconnected((reason) => {
      setCallState('ended');
      finishAndGoBack();
    });
    LiveKitCallService.onRemoteTrack((track) => {
      if (track.kind === 'video') setRemoteVideoTrack(track);
    });

    // Connect
    if (isIncoming) {
      LiveKitCallService.acceptCall(token, livekitUrl, isVideo);
    } else {
      LiveKitCallService.startCall(contactId, contactName, isVideo);
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      LiveKitCallService.endCall();
      CallKitService.endActiveCall(contactId);
    };
  }, []);

  const finishAndGoBack = () => {
    // Save call log
    // Navigate back
    navigation.goBack();
  };

  // ... UI rendering (butoane mute, speaker, hangup, video view)
};
```

**Diferențe față de vechiul CallScreen:**
- NU mai are: WebRTCManager, SignalingClient, SDP handling, ICE candidates, audio session management, InCallManager, ColdStartCoordinator path logic, reconnect logic, TURN credential fetching
- ARE: LiveKit Room connection, track subscription, simple state management
- **Reducere**: 1179 linii → ~400 linii (66% mai puțin cod)

#### 2.2 IncomingCallOverlay update
**Fișier:** `src/components/IncomingCallOverlay.tsx`
- Acceptare apel: primește `token`, `livekitUrl`, `roomName` din server
- Navigare la CallScreen cu parametrii LiveKit
- NU mai primește `offer` (SDP) — LiveKit nu are nevoie

#### 2.3 App.tsx — Incoming Call Handler
**Fișier:** `App.tsx`
- Handler `incoming-livekit-call` (de la server): afișează IncomingCallOverlay cu roomName + token
- Elimină: cold start SDP handling, offer parsing, TURN caching
- Păstrează: CallKit reporting, ColdStartCoordinator answer/decline tracking

#### 2.4 Call Log Screen Update
**Fișier:** `src/screens/CallLogScreen.tsx`
- Fără modificări funcționale — call log se salvează la fel
- Durata se calculează din LiveKit room connection time

**Rezultat:** Scrie raport în `agent-runtime/outputs/frontend-callscreen-report.md`

---

### Agent: network-engineer (continuă)

#### 2.5 Separare WebRTCManager — Data Channel Only
**Fișier:** `src/network/WebRTCManager.ts`
- **Elimină**: `startCall`, `acceptCall`, `endCall`, `onCallConnected`, `onCallDisconnected`, `onRemoteStream`, `getCallStats`
- **Elimină**: tot ce ține de media tracks, audio, video
- **Păstrează**: `connectToPeer`, `sendMessage`, `onMessage`, `isPeerConnected`, chunking, ICE restart pentru data channel
- **Redenumește** (opțional): `P2PDataChannel.ts` — mai clar ce face
- **Actualizează** imports în `MessagingService.ts` dacă redenumești

#### 2.6 SignalingClient — Adaugă LiveKit Events
**Fișier:** `src/network/SignalingClient.ts`
- Adaugă handler pentru `incoming-livekit-call` event
- Adaugă handler pentru `call-token` response
- Păstrează toți handlerii existenți (mesaje, status, etc.)
- **Elimină**: `get-call-state` request (nu mai e nevoie de SDP retrieval)

**Rezultat:** Scrie raport în `agent-runtime/outputs/network-webrtc-separation-report.md`

---

### CHECKPOINT FAZA 2
- [ ] `npx tsc --noEmit` — zero erori
- [ ] CallScreen nou funcționează cu LiveKit (pe simulator)
- [ ] WebRTCManager conține DOAR data channel (fără call methods)
- [ ] IncomingCallOverlay primește LiveKit params
- [ ] App.tsx handler `incoming-livekit-call` funcționează
- [ ] Mesajele text merg prin P2P data channel (NU afectate)

---

## FAZA 3 — CLEANUP + iOS NATIVE (backend-engineer + security-engineer — PARALEL)

### Agent: backend-engineer

#### 3.1 Server Cleanup — Elimină Call Signaling Vechi
**Fișier:** `server/index.js`
- **Elimină** handlerele: `offer` (cu isCall), `answer`, `ice-candidate`, `call-ended`, `call-accepted-pending`, `get-call-state`
- **Elimină**: `activeCalls` Map, `recentCallOffers` Map
- **Păstrează**: `request-call-token` (nou), toți handlerii de mesaje/chat
- **Elimină** din `push.js`:
  - SDP embedding în VoIP push payload
  - TURN servers embedding
  - SDP minification logic
  - `getCachedTurnServers()` call chain
- **Simplificare** VoIP push: payload = `{ type, from, callerName, isVideo, roomName }`

#### 3.2 Server Cleanup — Elimină TURN Credential Management
**Fișier:** `server/index.js`
- **Elimină**: `getCachedTurnServers()`, `turnCredentialCache`, Metered API calls
- LiveKit gestionează TURN/STUN intern
- **Elimină** env vars: `TURN_USERNAME`, `TURN_CREDENTIAL`, `METERED_API_KEY`
- **Adaugă** env vars: `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `LIVEKIT_URL`

**Rezultat:** Scrie raport în `agent-runtime/outputs/backend-server-cleanup-report.md`

---

### Agent: security-engineer

#### 3.3 Elimină Dependințe npm Nefolosite
**Fișier:** `package.json`
- **Elimină**: `react-native-incall-manager` (nu mai e folosit — doar setKeepScreenOn/setSpeakerphoneOn, care se pot face nativ)
- **Păstrează**: `react-native-callkeep` (CallKit integration pe care LiveKit o folosește)
- **Păstrează**: `react-native-webrtc` (data channel — sau verifică dacă `@livekit/react-native-webrtc` îl înlocuiește)
- Rulează `npm install` după modificări
- iOS: `cd ios && pod install`

#### 3.4 AppDelegate Final Cleanup
**Fișier:** `ios/QRChat/AppDelegate.swift`
- **Elimină**: `useManualAudio` / `isAudioEnabled` management (LiveKit face asta)
- **Elimină**: `AVAudioSession.interruptionNotification` observer (LiveKit gestionează)
- **Păstrează**: PKPushRegistry (class property), VoIP push handler, `reportNewIncomingCall`
- **Simplificare** `didReceiveIncomingPushWith`:
  - Parsează: `from`, `callerName`, `isVideo`, `roomName`
  - Stochează în UserDefaults: `PendingVoIPCall` cu `roomName` (fără SDP/TURN)
  - `reportNewIncomingCall` — la fel ca acum

#### 3.5 Verificare E2E Mesaje Neatinse
- Trimite mesaj text de pe un dispozitiv pe altul
- Verifică: criptare, decriptare, padding (v2), hash chain — totul funcționează
- Confirmă: data channel P2P funcționează independent de LiveKit

**Rezultat:** Scrie raport în `agent-runtime/outputs/security-cleanup-report.md`

---

### CHECKPOINT FAZA 3
- [ ] `npx tsc --noEmit` — zero erori
- [ ] Server nu mai are handlere de signaling vechi
- [ ] VoIP push payload e minimal (fără SDP/TURN)
- [ ] InCallManager eliminat din package.json
- [ ] AppDelegate fără audio session management manual
- [ ] Mesaje text E2E funcționează (regression test)

---

## FAZA 4 — QA & BUILD 300 (qa-engineer + release-engineer)

### Agent: qa-engineer

#### 4.1 Teste Unitare
**Director:** `__tests__/`
- `LiveKitCallService.test.ts`:
  - Test: requestCallToken trimite mesaj corect pe SignalingClient
  - Test: startCall apelează Room.connect cu token
  - Test: endCall apelează Room.disconnect
  - Test: toggleMute schimbă starea
- `ColdStartCoordinator.test.ts`:
  - Test: run() citește PendingVoIPCall și navighează
  - Test: reset() curăță starea
  - Test: handleIncomingCallDuringColdStart returnează corect

#### 4.2 Teste de Integrare
- `CallFlow.test.ts`:
  - Outgoing: request token → connect room → publish tracks
  - Incoming: receive event → navigate → accept → connect room
  - Hangup: disconnect → save call log → navigate back
- `ChatUnaffected.test.ts`:
  - Mesaje text funcționează
  - P2P data channel funcționează
  - Push notifications mesaje funcționează

#### 4.3 Checklist Verificare Manuală
Scrie în `agent-runtime/outputs/qa-livekit-checklist.md`:
```
## Simulator
- [ ] Outgoing call → audio merge → hangup → revine la chat
- [ ] Incoming call → CallKit apare → Answer → audio merge
- [ ] Video call → camera funcționează → switch front/back
- [ ] Mute/unmute → funcționează
- [ ] Speaker toggle → funcționează
- [ ] Mesaj text → trimite/primește (neatins de migrare)
- [ ] P2P data channel → funcționează (neatins de migrare)

## iPhone fizic (TestFlight Build 300)
- [ ] Warm call (ambele app-uri deschise) → audio merge
- [ ] Background call (app în background) → CallKit apare → audio merge
- [ ] COLD START call (app killed) → CallKit apare → Answer → audio merge
- [ ] Cold start retry (fail → 15s → retry) → funcționează
- [ ] Call-ended propagare (16 pune receptorul → 11 se întrerupe)
- [ ] Mesaje text între telefoane → funcționează
- [ ] Push notifications mesaje → funcționează
```

**Rezultat:** Scrie raport în `agent-runtime/outputs/qa-livekit-report.md`

---

### Agent: release-engineer

#### 4.4 Changelog
**Fișier:** `CHANGELOG.md`
```markdown
## [Build 300] - 2026-03-30

### Call System — Complete Rewrite
- Replaced manual WebRTC call management with LiveKit SDK
- Cold start calls: fully handled by LiveKit + CallKit integration
- Audio session: managed by LiveKit (eliminates 3-system conflict)
- Signaling: LiveKit room-based (eliminates manual SDP/ICE)
- VoIP push: simplified payload (no SDP/TURN embedding)
- Outgoing calls: reported to CallKit via LiveKit
- Removed: RTCAudioBridge, InCallManager audio path, ColdStartCoordinator SDP retrieval
- Reduced call code: ~4400 lines → ~1500 lines (66% reduction)

### Unchanged
- E2E encrypted messaging (Double Ratchet + TweetNaCl)
- P2P data channel for direct message delivery
- Push notifications for text messages
- All chat UI screens
```

#### 4.5 Build Number
- Setează `CURRENT_PROJECT_VERSION = 300`
- **NU modifica** `APP_VERSION` (rămâne 4.3.0)

#### 4.6 Verificare Finală Automată
```bash
cd /Users/ruslanconstantinovici/QRChat
npx tsc --noEmit
npx jest --passWithNoTests
npx react-native bundle --platform ios --dev false --entry-file index.js --bundle-output /tmp/test-bundle.js
npx react-native bundle --platform android --dev false --entry-file index.js --bundle-output /tmp/test-bundle-android.js
```

**Rezultat:** Scrie raport final în `agent-runtime/outputs/release-livekit-report.md`

---

## DIAGRAMA DE DEPENDENȚE

```
FAZA 0 (SINGUR — architect):
  0.1 Install SDK → 0.2 Server setup → 0.3 Token service → 0.4 Server endpoint

FAZA 1 (PARALEL, după Faza 0):
  network-engineer (1.1 LiveKitCallService, 1.2 VoIP push update, 1.3 AppDelegate push)
  security-engineer (1.4 ColdStart simplify, 1.5 index.js cleanup, 1.6 RTCAudioBridge delete)

FAZA 2 (PARALEL, după Faza 1):
  frontend-engineer (2.1 CallScreen rewrite, 2.2 IncomingCallOverlay, 2.3 App.tsx, 2.4 CallLog)
  network-engineer (2.5 WebRTCManager separation, 2.6 SignalingClient events)

FAZA 3 (PARALEL, după Faza 2):
  backend-engineer (3.1 Server signaling cleanup, 3.2 TURN removal)
  security-engineer (3.3 npm cleanup, 3.4 AppDelegate cleanup, 3.5 E2E verification)

FAZA 4 (SECVENȚIAL, după Faza 3):
  qa-engineer (4.1 unit tests, 4.2 integration tests, 4.3 manual checklist)
  release-engineer (4.4 changelog, 4.5 build 300, 4.6 verification)
```

---

## FIȘIERE MODIFICATE — OWNERSHIP

| Fișier | Agent UNIC responsabil |
|--------|----------------------|
| `src/services/LiveKitCallService.ts` (NOU) | network-engineer |
| `src/screens/CallScreen.tsx` (RESCRIS) | frontend-engineer |
| `src/components/IncomingCallOverlay.tsx` | frontend-engineer |
| `App.tsx` | frontend-engineer (2.3) → security-engineer (3.4) SECVENȚIAL |
| `src/services/ColdStartCoordinator.ts` | security-engineer |
| `src/network/WebRTCManager.ts` | network-engineer |
| `src/network/SignalingClient.ts` | network-engineer |
| `server/index.js` | architect (0.4) → backend-engineer (3.1, 3.2) SECVENȚIAL |
| `server/push.js` | backend-engineer |
| `server/livekit.js` (NOU) | architect |
| `ios/QRChat/AppDelegate.swift` | security-engineer |
| `ios/QRChat/RTCAudioBridge.swift` (ȘTERS) | security-engineer |
| `ios/QRChat/RTCAudioBridge.m` (ȘTERS) | security-engineer |
| `index.js` | security-engineer |
| `package.json` | security-engineer |
| `__tests__/*` | qa-engineer |
| `CHANGELOG.md` | release-engineer |
| `ios/QRChat.xcodeproj/project.pbxproj` | release-engineer |
| `android/app/build.gradle` | release-engineer |
| `agent-runtime/state/status.md` | TOȚI |
| `agent-runtime/outputs/*` | TOȚI |

---

## FIȘIERE NEATINSE (verificare strictă)

Aceste fișiere NU trebuie modificate sub nicio formă:
- `src/crypto/DoubleRatchet.ts`
- `src/crypto/KeyManager.ts`
- `src/crypto/RatchetStore.ts`
- `src/crypto/InviteLinkCrypto.ts`
- `src/services/MessagingService.ts` (excepție: schimbare import dacă WebRTCManager se redenumește)
- `src/storage/Database.ts`
- `src/screens/ChatScreen.tsx`
- `src/screens/HomeScreen.tsx`
- `src/screens/ContactsScreen.tsx`
- `src/screens/SettingsScreen.tsx`
- `src/screens/QRGenerateScreen.tsx`
- `src/screens/QRScanScreen.tsx`
- `src/i18n/locales/*.json` (excepție: stringuri call noi)

**Dacă un agent trebuie să atingă un fișier din lista asta — STOP, scrie mesaj în `agent-runtime/messages/` și cere aprobarea lead-ului.**

---

## COMANDA DE LANSARE

```
Lansează echipa QRChat cu următorii agenți, în ordinea fazelor:

FAZA 0 (singur): architect
FAZA 1 (paralel, după Faza 0): network-engineer + security-engineer
FAZA 2 (paralel, după Faza 1): frontend-engineer + network-engineer
FAZA 3 (paralel, după Faza 2): backend-engineer + security-engineer
FAZA 4 (secvențial, după Faza 3): qa-engineer → release-engineer

Fiecare agent citește acest prompt complet și execută DOAR sarcinile sale.
După fiecare fază, se verifică checkpoint-ul înainte de a trece la următoarea.
La final, release-engineer rulează verificarea totală și raportează rezultatul.

TOATE modificările pe branch-ul feature/livekit-calls.
NU face push. NU modifica versiunea. Build number = 300 la final.
Fallback: git checkout main — Build 203 stabil.
```

---

## VERIFICARE FINALĂ

Lead-ul verifică:
1. `git diff main --stat` — doar fișierele din tabelul de ownership
2. `npx tsc --noEmit` — zero erori
3. `npx jest` — toate testele trec
4. Bundle iOS și Android OK
5. **Warm call** — ambele app-uri deschise → audio merge
6. **Cold start** — kill app → sună → CallKit apare → Answer → audio merge
7. **Mesaje text** — trimite/primește E2E criptat (neatins)
8. **P2P data channel** — funcționează independent de LiveKit
9. Call-ended propagare corectă
10. Call log salvat corect

**Dacă cold start NU merge:** `git checkout main` — Build 203 stabil.
**Dacă totul merge:** merge în main, Build 300, TestFlight.
