# QRChat — Migrare Call System la LiveKit · Build 300

## Ce vrem

Inlocuieste sistemul manual de apeluri cu LiveKit SDK. Tot ce tine de mesaje text, criptare, chat ramane neatins.

## Starea curenta

- **Branch:** main, commit `75b9eff0` (Build 203)
- **Versiune:** 4.3.0, React Native 0.84.0
- **WebRTC:** react-native-webrtc 124.0.7
- **Calls acum:** ~3100 linii de call management manual cu 6 buguri critice
- **Cercetare completata:** `agent-runtime/outputs/livekit-research-report.md`

## Constatari din cercetare — CE TREBUIE STIUT

Cercetarea a stabilit urmatoarele fapte. Agentii TREBUIE sa le respecte:

1. **react-native-webrtc si @livekit/react-native-webrtc NU POT COEXISTA.** Trebuie swap complet. QRChat foloseste react-native-webrtc si pentru P2P data channels (mesaje chat). Dupa swap, data channels TREBUIE sa functioneze cu @livekit/react-native-webrtc (e fork, aceleasi API-uri).

2. **LiveKit NU gestioneaza CallKit, PushKit, sau cold start.** Toata infrastructura CallKit/PushKit/ColdStartCoordinator RAMANE. Fix-urile din Build 203 (PKPushRegistry retained, useManualAudio, RTCAudioBridge, nav queue) se PASTREAZA.

3. **LiveKit necesita SFU server.** Folosim LiveKit Cloud free tier (5000 min/luna). Token generation se adauga pe serverul Node.js existent.

4. **SFU vede media daca nu activam E2EE.** Activam LiveKit E2EE (RNE2EEManager) pentru apeluri.

5. **Cold start cu LiveKit:** In loc de SDP in VoIP push, trimitem roomName + token pre-generat. Token-ul se genereaza pe server LA MOMENTUL PUSH-ULUI si se include in payload. Asta elimina round-trip-ul extra.

6. **Latenta:** SFU adauga ~50ms. Acceptabil pentru reliability imbunatatita (zero probleme NAT/TURN).

## Reguli

1. Toate modificarile pe branch `feature/livekit-calls` — main ramane la Build 203
2. Nu face push, build, sau deploy fara aprobarea mea
3. Nu atinge fisierele de chat/crypto (lista mai jos)
4. Dupa fiecare commit: ruleaza scriptul de verificare
5. Dupa fiecare faza: git tag `checkpoint/faza-N`
6. Daca o faza esueaza: `git reset --hard` la checkpoint-ul anterior
7. Secvential — un singur agent per faza
8. Comentarii si commit messages in engleza, refera documentatia LiveKit

## Auto-gate

**Dupa fiecare faza:** ruleaza scriptul de verificare.
- TOATE trec → `git tag` → **continua automat**
- ORICARE esueaza → **STOP, raporteaza, asteapta instructiuni**

**STOP OBLIGATORIU (3 momente):**
- **Dupa Faza 0** — lead confirma ca swap-ul WebRTC nu a spart mesajele P2P
- **Dupa Faza 2** — lead testeaza apeluri pe simulator
- **Dupa Faza 4** — lead testeaza pe telefoane fizice

## Fisiere INTERZISE

```
src/crypto/DoubleRatchet.ts
src/crypto/KeyManager.ts
src/crypto/RatchetStore.ts
src/crypto/InviteLinkCrypto.ts
src/storage/Database.ts
src/screens/ChatScreen.tsx
src/screens/HomeScreen.tsx
src/screens/ContactsScreen.tsx
src/screens/SettingsScreen.tsx
src/screens/QRGenerateScreen.tsx
src/screens/QRScanScreen.tsx
src/screens/CreateInviteScreen.tsx
src/screens/ShareInviteScreen.tsx
src/screens/InviteAcceptScreen.tsx
src/screens/InviteManagementScreen.tsx
src/screens/ProfileScreen.tsx
src/screens/GroupInfoScreen.tsx
src/screens/CreateGroupScreen.tsx
```

## Script de verificare (dupa FIECARE commit)

```bash
#!/bin/bash
set -e
cd /Users/ruslanconstantinovici/QRChat
echo "=== TypeScript ==="
npx tsc --noEmit
echo "=== Tests ==="
npx jest --passWithNoTests 2>/dev/null || true
echo "=== iOS Bundle ==="
npx react-native bundle --platform ios --dev false --entry-file index.js --bundle-output /tmp/test-bundle.js 2>/dev/null
echo "=== Forbidden files ==="
FORBIDDEN=$(git diff main -- src/crypto/ src/storage/Database.ts src/screens/ChatScreen.tsx src/screens/HomeScreen.tsx src/screens/ContactsScreen.tsx src/screens/SettingsScreen.tsx)
if [ -n "$FORBIDDEN" ]; then echo "EROARE: Fisiere interzise modificate!"; exit 1; fi
echo "=== ALL PASSED ==="
```

---

## FAZA 0 — SWAP WEBRTC + POC (un singur agent)

**Agent:** network-engineer
**Aceasta e faza cu cel mai mare risc. Daca esueaza, STOP total — LiveKit nu e viabil.**

### Ce face:

1. Creeaza branch: `git checkout -b feature/livekit-calls`

2. **SWAP react-native-webrtc PRIMUL (inainte de orice LiveKit):**
   - `npm uninstall react-native-webrtc`
   - `npm install @livekit/react-native-webrtc`
   - In TOATE fisierele care importa din `react-native-webrtc`, schimba importul la `@livekit/react-native-webrtc`:
     - `src/network/WebRTCManager.ts`
     - `src/screens/CallScreen.tsx`
     - `src/services/ColdStartCoordinator.ts` (daca importa RTCAudioSession)
     - `index.js` (daca importa RTCAudioSession)
     - Orice alt fisier gasit cu `grep -rn "react-native-webrtc" src/`
   - `cd ios && pod install`
   - `npx tsc --noEmit` — zero erori

3. **TESTEAZA P2P DATA CHANNELS (CRITIC):**
   - Build pe simulator
   - Deschide app-ul
   - Trimite mesaj text la un contact
   - Verifica ca mesajul ajunge (P2P sau server relay)
   - Verifica ca `WebRTCManager.connectToPeer()` functioneaza
   - Verifica ca `WebRTCManager.sendMessage()` functioneaza
   - **Daca mesajele NU merg → STOP TOTAL. git reset --hard main. LiveKit nu e viabil.**

4. **Instaleaza LiveKit SDK:**
   - `npm install @livekit/react-native livekit-client`
   - `cd ios && pod install`
   - Adauga in `index.js` (la inceputul fisierului, inainte de orice altceva):
     ```
     import { registerGlobals } from '@livekit/react-native';
     registerGlobals();
     ```
   - Adauga in AppDelegate.swift (inainte de startReactNative):
     - Importul si setup-ul LiveKit conform documentatiei oficiale

5. **POC — test conectare Room:**
   - Setup LiveKit Cloud: creeaza cont pe cloud.livekit.io, obtine API key/secret/URL
   - Creeaza `server/livekit.js` cu functie `generateCallToken(userId, roomName)`
   - Adauga pe server handler `request-call-token` care genereaza si returneaza token
   - Test: din app, solicita token → conecteaza Room → log "connected"

### Checkpoint Faza 0:
- [ ] `npx tsc --noEmit` — zero erori
- [ ] Pod install OK
- [ ] **MESAJE TEXT functioneaza** (P2P data channel cu noul WebRTC fork)
- [ ] Room.connect() reusit (log)
- [ ] App porneste pe simulator fara crash
- [ ] `git tag checkpoint/faza-0-poc`

**STOP OBLIGATORIU. Lead-ul verifica ca mesajele P2P functioneaza.**

---

## FAZA 1 — LIVEKIT CALL SERVICE (un singur agent)

**Agent:** network-engineer

### Ce face:

1. Creeaza `src/services/LiveKitCallService.ts`:
   - `startCall(contactId, contactName, isVideo)` — solicita token, conecteaza Room, publica tracks
   - `acceptCall(token, livekitUrl, isVideo)` — conecteaza Room cu token primit
   - `endCall()` — disconnect Room
   - `toggleMute()`, `toggleCamera()`, `switchCamera()`
   - Callbacks: `onConnected`, `onDisconnected`, `onRemoteTrack`
   - Activeaza E2EE cu `RNE2EEManager` daca LiveKit o suporta pe React Native

2. Server handler `request-call-token` (deja creat in Faza 0):
   - La apel catre callee OFFLINE: genereaza token SI pentru callee, il include in VoIP push payload
   - VoIP push payload NOU: `{ type: 'incoming-call', from, callerName, isVideo, roomName, token, livekitUrl }`
   - Asta elimina round-trip-ul la cold start — callee are token-ul direct din push

3. Adauga in SignalingClient handler pentru `call-token` si `incoming-livekit-call`

4. Server: cand callee e ONLINE, trimite `incoming-livekit-call` pe WebSocket cu token-ul callee

### Checkpoint Faza 1:
- [ ] `npx tsc --noEmit` — zero erori
- [ ] LiveKitCallService compilat
- [ ] Server genereaza token-uri si le trimite
- [ ] VoIP push contine token pre-generat
- [ ] Script verificare trece
- [ ] `git tag checkpoint/faza-1-service`
- [ ] Mesaje text functioneaza (regression)

**AUTO-GATE: daca script trece → continua.**

---

## FAZA 2 — CALLSCREEN SI COLD START (un singur agent)

**Agent:** frontend-engineer

### Ce face:

1. Rescrie `src/screens/CallScreen.tsx`:
   - Foloseste `LiveKitCallService` in loc de `WebRTCManager` pentru calls
   - Pastreaza UI: butoane mute/speaker/video/hangup, timer, contact name
   - Incoming: primeste `token`, `livekitUrl`, `roomName` din route params
   - Outgoing: apeleaza `LiveKitCallService.startCall()`
   - Pastreaza: call log save, duration timer, CallKitService.endActiveCall la hangup
   - Elimina: SDP handling, ICE candidates, TURN credential fetching, reconnect manual

2. Actualizeaza `src/components/IncomingCallOverlay.tsx`:
   - Accept navigheaza la CallScreen cu `{ token, livekitUrl, roomName }` in loc de `{ offer }`

3. Actualizeaza `App.tsx`:
   - Handler `incoming-livekit-call` (de la WebSocket): afiseaza overlay cu roomName + token
   - CallKit: reportIncomingCall ramane la fel (nu se schimba)

4. Actualizeaza `src/services/ColdStartCoordinator.ts`:
   - Noul `run()`: citeste PendingVoIPCall → extrage `roomName` + `token` (pre-generat, din VoIP push) → navigheaza la CallScreen
   - Elimina PATH A/B/C (SDP retrieval) — token-ul vine direct din push
   - Pastreaza: answer/decline UUID tracking, reset(), handleIncomingCallDuringColdStart

5. Actualizeaza `ios/QRChat/AppDelegate.swift` — `didReceiveIncomingPushWith`:
   - Parseaza: `from`, `callerName`, `isVideo`, `roomName`, `token`, `livekitUrl`
   - Stocheaza in PendingVoIPCall UserDefaults
   - reportNewIncomingCall — NESCHIMBAT
   - Duplicate check (appState == .active) — NESCHIMBAT
   - PKPushRegistry retained ca class property — NESCHIMBAT (fix din Build 203)

### Checkpoint Faza 2:
- [ ] `npx tsc --noEmit` — zero erori
- [ ] Outgoing call pe simulator → audio merge → hangup
- [ ] Incoming call warm (ambele app-uri deschise) → audio merge
- [ ] Call log se salveaza
- [ ] Script verificare trece
- [ ] `git tag checkpoint/faza-2-callscreen`
- [ ] Mesaje text functioneaza (regression)

**STOP OBLIGATORIU. Lead-ul testeaza pe simulator.**

---

## FAZA 3 — CLEANUP COD VECHI (un singur agent)

**Agent:** security-engineer

### Ce face:

1. `src/network/WebRTCManager.ts`:
   - Elimina: `startCall`, `endCall`, `onCallConnected`, `onCallDisconnected`, `onRemoteStream`, `getCallStats`, media track management
   - Pastreaza: `connectToPeer`, `sendMessage`, `onMessage`, `isPeerConnected`, chunking, ICE restart — data channel

2. `server/index.js`:
   - Elimina handlere call vechi: `offer` (cu isCall), `answer`, `ice-candidate`, `call-ended`, `call-accepted-pending`, `get-call-state`
   - Elimina: `activeCalls` Map, `recentCallOffers` Map, `getCachedTurnServers()`
   - Pastreaza: `request-call-token` (nou), handleri chat/mesaje, push mesaje

3. `server/push.js`:
   - VoIP push payload simplificat: `{ type, from, callerName, isVideo, roomName, token, livekitUrl }`
   - Elimina: SDP embedding, TURN embedding, SDP minification

4. `index.js`:
   - Elimina: `onAnswerCall`, `onEndCall` handlers cu isActive guard (LiveKit nu mai are nevoie)
   - Pastreaza: `didLoadWithEvents`, audio session listeners

5. Elimina `ios/QRChat/RTCAudioBridge.swift` si `RTCAudioBridge.m` (LiveKit gestioneaza audio)

6. `package.json`: elimina `react-native-incall-manager` daca nu mai e folosit

7. `cd ios && pod install`

### Checkpoint Faza 3:
- [ ] `npx tsc --noEmit` — zero erori
- [ ] Mesaje text functioneaza (CRITIC)
- [ ] P2P data channel functioneaza
- [ ] Apeluri pe simulator functioneaza
- [ ] Server porneste: `node -e "require('./server/index.js')"`
- [ ] Script verificare trece
- [ ] `git tag checkpoint/faza-3-cleanup`

**AUTO-GATE: daca script trece → continua.**

---

## FAZA 4 — QA + BUILD 300 (secvential)

**Agent:** qa-engineer, apoi release-engineer

### QA:

1. Teste unitare LiveKitCallService
2. Checklist manual:

```
## Simulator
- [ ] Outgoing audio → audio merge → hangup
- [ ] Outgoing video → camera → switch front/back
- [ ] Mute/unmute, speaker toggle
- [ ] Mesaj text trimis/primit (regression)

## iPhone fizic
- [ ] Warm call → audio merge
- [ ] Background call → CallKit → Answer → audio
- [ ] COLD START (kill app → suna → CallKit → Answer → audio)
- [ ] Call-ended propagare
- [ ] Mesaje text (regression)
- [ ] Push notifications mesaje (regression)
- [ ] Reinstalare → cold start → merge
```

### Release:

1. CHANGELOG.md — Build 300
2. `CURRENT_PROJECT_VERSION = 300`
3. Script verificare complet
4. **NU face build fara aprobarea mea**

**STOP OBLIGATORIU. Lead-ul testeaza pe telefoane, da OK pentru TestFlight.**

---

## Ordinea de executie

```
FAZA  0: network-engineer (swap WebRTC + POC)   → STOP OBLIGATORIU (P2P data channel OK?)
FAZA  1: network-engineer (LiveKitCallService)   → AUTO
FAZA  2: frontend-engineer (CallScreen + cold)   → STOP OBLIGATORIU (test simulator)
FAZA  3: security-engineer (cleanup)             → AUTO
FAZA  4: qa + release (test + build 300)         → STOP OBLIGATORIU (test telefoane)
```

**Un singur agent activ la un moment dat.**
**Faza 0 e decisiva: daca P2P data channels se strica dupa swap → STOP TOTAL, revert, abandon LiveKit.**
**Dupa fiecare faza: git tag checkpoint.**
**Fallback: git checkout main — Build 203 stabil.**
