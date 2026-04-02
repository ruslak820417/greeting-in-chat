# FIX: Audio pentru outgoing calls — CallKit startCall cu UUID valid

## PROBLEMA

Cu `useManualAudio = true` in AppDelegate, `isAudioEnabled` se seteaza pe `true` DOAR cand CallKit apeleaza `didActivateAudioSession`. Asta functioneaza pentru **incoming calls** (VoIP push → reportNewIncomingCall → CallKit → didActivateAudioSession → isAudioEnabled = true).

Dar **outgoing calls** NU trec prin CallKit deloc — `RNCallKeep.startCall()` a fost eliminat din cauza unui crash. Crash-ul era cauzat de un UUID invalid: `generateId()` genera `'mndfyb6o'` (8 caractere random), dar CallKit cere format UUID standard: `'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'`.

**Rezultat:** outgoing calls nu au audio — `isAudioEnabled` ramane `false`.

**Solutia:** readauga `RNCallKeep.startCall()` dar cu UUID generat de `CallKitService.generateUUID()` (care produce formatul corect). CallKit va activa audio session → AppDelegate observer seteaza `isAudioEnabled = true` → audio functioneaza.

## CE TREBUIE FACUT (3 modificari, zero fisiere noi)

### 1. CallScreen.tsx — adauga RNCallKeep.startCall() pentru outgoing

**Fisier:** `src/screens/CallScreen.tsx`
**Unde:** in blocul `else` (outgoing call), INAINTE de `LiveKitCallService.startCall()` (linia ~268)

**Cod curent (linia 253-275):**
```typescript
} else {
  const handleCallToken = async (data: ...) => { ... };
  EventBus.on('call-token', handleCallToken);

  Log.info(..., `startCall (outgoing) starting...`);
  try {
    await LiveKitCallService.startCall(contactId, contactName, isVideo);
  } catch ...
}
```

**Ce trebuie adaugat — INAINTE de EventBus.on:**
```typescript
} else {
  // Report outgoing call to CallKit FIRST — this triggers didActivateAudioSession
  // which sets isAudioEnabled=true via AppDelegate observer.
  // UUID MUST be standard format (xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx).
  // generateId() produces 'mndfyb6o' which crashes CallKit — use CallKitService.generateUUID().
  const outgoingUUID = CallKitService.generateUUID();
  Log.info(LogCategory.CALL, `[+${diagMs()}ms] Outgoing: reporting to CallKit UUID=${outgoingUUID.substring(0, 8)}`);
  try {
    const RNCallKeep = require('react-native-callkeep').default;
    RNCallKeep.startCall(outgoingUUID, contactId, contactName, 'generic', isVideo);
    CallKitService.trackOutgoingCall(contactId, contactName, isVideo, outgoingUUID);
  } catch (e) {
    Log.warn(LogCategory.CALL, `[+${diagMs()}ms] CallKit startCall failed: ${e}`);
  }

  const handleCallToken = async (data: ...) => { ... };
  // ... restul codului ramine la fel
```

### 2. CallKitService.ts — expune generateUUID ca metoda publica

**Fisier:** `src/services/CallKitService.ts`
**Unde:** linia 222 — metoda `generateUUID()` e `private`. Schimba in `public`.

**Curent:**
```typescript
private generateUUID(): string {
```

**Nou:**
```typescript
generateUUID(): string {
```

Atat. O singura linie.

### 3. LiveKitCallService.ts — ELIMINA activarea manuala a audio session

**Fisier:** `src/services/LiveKitCallService.ts`
**Unde:** liniile 120-129 — blocul care apeleaza `RTCAudioSession.audioSessionDidActivate()` manual.

**Sterge acest bloc complet:**
```typescript
// THEN activate audio session — with useManualAudio=true, isAudioEnabled must be set.
// For incoming calls, CallKit's didActivateAudioSession in AppDelegate handles this.
// For outgoing calls (no CXStartCallAction), we notify WebRTC manually here.
try {
  const { RTCAudioSession: RTCAudio } = require('@livekit/react-native-webrtc');
  RTCAudio.audioSessionDidActivate();
  Log.info(LogCategory.CALL, '[LiveKit] RTCAudioSession.audioSessionDidActivate() called (post-tracks)');
} catch (e) {
  Log.warn(LogCategory.CALL, `[LiveKit] RTCAudioSession activation failed: ${e}`);
}
```

**De ce:** CallKit acum gestioneaza audio pentru AMBELE directii:
- Incoming: VoIP push → reportNewIncomingCall → didActivateAudioSession → isAudioEnabled = true
- Outgoing: startCall() → didActivateAudioSession → isAudioEnabled = true

LiveKitCallService NU trebuie sa faca nimic cu audio session.

## CE NU TREBUIE ATINS

- `AppDelegate.swift` — NEATINS. useManualAudio + observer sunt corecte.
- `index.js` — NEATINS. didActivateAudioSession handler e corect.
- `server/` — NEATINS.
- RTCAudioBridge — NU readuce. Nu e necesar.

## FLOW-UL FINAL (un singur sistem de audio)

```
OUTGOING:
  CallScreen → RNCallKeep.startCall(validUUID) → iOS CallKit
    → CXStartCallAction → CXProvider.didActivateAudioSession
    → AppDelegate observer → isAudioEnabled = true
    → WebRTC/LiveKit audio functioneaza

INCOMING:
  VoIP push → AppDelegate.reportNewIncomingCall → iOS CallKit
    → User apasa Answer → CXAnswerCallAction → CXProvider.didActivateAudioSession
    → AppDelegate observer → isAudioEnabled = true
    → WebRTC/LiveKit audio functioneaza

COLD START:
  VoIP push → reportNewIncomingCall → CallKit UI pe lock screen
    → User apasa Answer → didActivateAudioSession (buffered in didLoadWithEvents)
    → index.js observer → isAudioEnabled = true
    → WebRTC/LiveKit audio functioneaza
```

**Un singur flow. CallKit gestioneaza audio. Zero cod manual.**

## VERIFICARE

Dupa modificari:
1. `npx tsc --noEmit` — zero erori
2. Build pe simulator — app porneste
3. Outgoing call — apare UI CallKit pentru outgoing? Audio?
4. Incoming call — audio functioneaza ca inainte?
5. Hangup — CallKit se inchide corect?

## COMMIT

```
git add src/screens/CallScreen.tsx src/services/CallKitService.ts src/services/LiveKitCallService.ts
git commit -m "Unify audio: report outgoing calls to CallKit for didActivateAudioSession"
```

Apoi Build 303 + TestFlight.
