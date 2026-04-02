# QRChat-Audio — Cold Start Call Fix

**Codebase:** `/Users/ruslanconstantinovici/QRChat-Audio`
**Problema:** Cold start incoming calls (app killed → VoIP push → CallKit → Answer) — audio nu functioneaza
**Cauza root:** 3 bug-uri care impreuna fac audio-ul sa nu porneasca pe cold start

---

## CONTEXT IMPORTANT — CITESTE INAINTE DE ORICE

Warm calls FUNCTIONEAZA PERFECT. NU modifica nimic din flow-ul warm call. Toate fix-urile de mai jos sunt DOAR pentru cold start path. Fiecare fix are un guard explicit care verifica daca e cold start.

**Pattern validat de Signal, LiveKit, GetStream, Wire, Jitsi, ConnectyCube:**
- `useManualAudio = true` la startup
- `isAudioEnabled = false` la startup
- `isAudioEnabled = true` DOAR cand CallKit activeaza audio session
- Re-notificare `audioSessionDidActivate()` DUPA ce PeerConnection exista
- NICIODATA `InCallManager.stop()` pe cold start
- NICIODATA `InCallManager.start()` pe iOS cu CallKit (CallKit gestioneaza audio)

---

## FIX A — CRITICA: Adauga `useManualAudio = true` in AppDelegate

**Fisier:** `ios/QRChat/AppDelegate.swift`
**Problema:** `useManualAudio` nu e setat — WebRTC default e `false`, asa ca WebRTC auto-configureaza AVAudioSession si CONFLICTEAZA cu CallKit.
**Sursa:** Signal, LiveKit, GetStream — TOATE folosesc `useManualAudio = true`.

**Ce sa faci:** Inlocuieste comentariul de la liniile 35-44 cu cod activ:

```swift
// STERGE tot comentariul vechi de la linia 35 pana la 44 (cel care spune "do NOT use useManualAudio")
// INLOCUIESTE cu:

// WebRTC manual audio — MANDATORY for CallKit integration.
// Pattern: Signal, LiveKit, GetStream, Wire, Jitsi, ConnectyCube.
// Without this, WebRTC fights CallKit for AVAudioSession control.
let rtcAudioSession = RTCAudioSession.sharedInstance()
rtcAudioSession.useManualAudio = true
rtcAudioSession.isAudioEnabled = false
LogService.logNative(1, category: "CALL", message: "useManualAudio=true, isAudioEnabled=false (startup)")
```

**De ce e safe pentru outgoing calls:** Outgoing calls activeaza audio prin `RTCAudioBridge.setAudioEnabled(true)` din CallScreen.tsx — nu depind de CallKit `didActivateAudioSession`. Dar DACA vrei si mai safe, adauga in CallScreen.tsx la outgoing call path (vezi FIX D).

---

## FIX B — CRITICA: Nu consuma answerUUID inainte ca CallScreen sa-l verifice

**Fisier:** `src/services/ColdStartCoordinator.ts`
**Problema:** `navigateToCall()` la linia 377 apeleaza `consumeAnswerUUID()` care seteaza `_answerUUID = null`. Cand CallScreen.tsx verifica `ColdStartCoordinator.hasAnswer` la linia 261, returneaza `false`. Rezultat: `InCallManager.stop()` se apeleaza pe cold start si DEZACTIVEAZA audio session.

**Ce sa faci:** In loc sa consumi UUID-ul in `navigateToCall()`, seteaza un flag separat care indica ca e cold start incoming call:

1. Adauga un nou camp privat in clasa `ColdStartCoordinator`:
```typescript
private _isColdStartIncomingCall: boolean = false;
```

2. Adauga getter:
```typescript
get isColdStartIncomingCall(): boolean {
  return this._isColdStartIncomingCall;
}
```

3. In `navigateToCall()`, INAINTE de `consumeAnswerUUID()`, seteaza flag-ul:
```typescript
// La linia 375, INAINTE de this.handled = true:
this._isColdStartIncomingCall = true;  // ADAUGA ACEASTA LINIE

// Restul ramane la fel:
this.handled = true;
const coldUUID = this.consumeAnswerUUID();
// ...
```

4. In `handleIncomingCallDuringColdStart()` (PATH C), la fel — INAINTE de `consumeAnswerUUID()`:
```typescript
// La linia 292, INAINTE de consumeAnswerUUID:
this._isColdStartIncomingCall = true;  // ADAUGA ACEASTA LINIE

const coldUUID = this.consumeAnswerUUID();
// ...
```

5. In `reset()`, reseteaza flag-ul:
```typescript
this._isColdStartIncomingCall = false;
```

---

## FIX C — CRITICA: CallScreen sa foloseasca noul flag

**Fisier:** `src/screens/CallScreen.tsx`
**Problema:** Linia 261 foloseste `ColdStartCoordinator.hasAnswer` care e deja `false` cand ajunge aici.

**Ce sa faci:** Inlocuieste verificarea de la linia 261:

```typescript
// INAINTE (gresit — hasAnswer e false pentru ca UUID-ul e deja consumat):
const isColdStartIncoming = isIncoming && ColdStartCoordinator.hasAnswer;

// DUPA (corect — foloseste flag-ul dedicat care NU se reseteaza la navigare):
const isColdStartIncoming = isIncoming && ColdStartCoordinator.isColdStartIncomingCall;
```

Aceasta e SINGURA modificare in CallScreen.tsx. Restul flow-ului (InCallManager.stop skip, re-notificare post-answerCall, RTCAudioBridge.setAudioEnabled) ramane EXACT la fel.

---

## FIX D — IMPORTANTA: Activeaza audio manual pentru outgoing calls

**Fisier:** `src/screens/CallScreen.tsx`
**Problema:** Cu `useManualAudio = true` (FIX A), outgoing calls nu vor avea audio daca `isAudioEnabled` nu e setat pe `true`. CallKit `didActivateAudioSession` NU se emite automat pe outgoing (doar pe incoming).

**Ce sa faci:** In `startCall()`, la sectiunea outgoing (linia 393-403), INAINTE de `WebRTCManager.startCall()`, adauga activare manuala a audio:

```typescript
// Cauta linia "startCall (outgoing) starting..." (in jurul liniei 394)
// INAINTE de await WebRTCManager.startCall(), adauga:

// Outgoing: manually activate audio session (CallKit doesn't fire didActivateAudioSession for outgoing)
Log.info(LogCategory.CALL, `[+${diagMs()}ms] Outgoing call: manually activating audio session`);
try {
  const { RTCAudioSession } = require('react-native-webrtc');
  RTCAudioSession.audioSessionDidActivate();
} catch (e) {}
try {
  const { NativeModules: NM } = require('react-native');
  NM.RTCAudioBridge?.setAudioEnabled(true);
} catch (e) {}
```

---

## FIX E — IMPORTANTA: Nu consuma UserDefaults in checkPending

**Fisier:** `App.tsx`
**Problema:** La linia 327, `getPendingVoIPCall()` e un DESTRUCTIVE READ — sterge datele din UserDefaults. Daca se apeleaza inainte de `ColdStartCoordinator.run()`, PATH A nu gaseste nimic.

**Ce sa faci:** Adauga o metoda non-destructiva in AppDelegate.swift SI foloseste-o in App.tsx:

1. In `ios/QRChat/AppDelegate.swift`, in clasa `APNsTokenModule`, adauga:

```swift
@objc func hasPendingVoIPCall(_ resolve: @escaping RCTPromiseResolveBlock, rejecter reject: @escaping RCTPromiseRejectBlock) {
    let data = UserDefaults.standard.string(forKey: "PendingVoIPCall")
    resolve(data != nil)
}
```

2. In `ios/QRChat/RTCAudioBridge.m` (sau unde e bridge-ul APNsTokenModule), NU trebuie modificat — `APNsTokenModule` e exportat din AppDelegate.swift cu `@objc(APNsTokenModule)`. Dar verifica daca exista un fisier `APNsTokenModule.m` separat cu extern methods. Daca da, adauga:

```objc
RCT_EXTERN_METHOD(hasPendingVoIPCall:(RCTPromiseResolveBlock)resolve rejecter:(RCTPromiseRejectBlock)reject)
```

Daca NU exista fisier `.m` separat pentru APNsTokenModule (metodele sunt declarate automat), cauta fisierul `.m` care face bridge-ul si adauga linia.

3. In `App.tsx`, modifica `checkPending()` (linia 324-330):

```typescript
// INAINTE (gresit — consuma datele destructiv):
const checkPending = async () => {
  try {
    const { NativeModules } = require('react-native');
    const json = await NativeModules.APNsTokenModule?.getPendingVoIPCall?.();
    return !!json;
  } catch { return false; }
};

// DUPA (corect — doar verifica, nu consuma):
const checkPending = async () => {
  try {
    const { NativeModules } = require('react-native');
    const has = await NativeModules.APNsTokenModule?.hasPendingVoIPCall?.();
    return !!has;
  } catch { return false; }
};
```

---

## FIX F — LOW: Adauga `activateAudioSession` si `deactivateAudioSession` in RTCAudioBridge

**Fisier:** `ios/QRChat/RTCAudioBridge.swift`
**Problema:** `index.js` apeleaza `RTCAudioBridge.activateAudioSession()` si `deactivateAudioSession()` dar aceste metode NU exista. Sunt silent no-ops.

**Ce sa faci:** Adauga cele 2 metode in `RTCAudioBridge.swift`:

```swift
/// Full audio session activation (didActivate + isAudioEnabled=true)
/// Called from JS on CallKit didActivateAudioSession event.
@objc func activateAudioSession() {
    let session = RTCAudioSession.sharedInstance()
    session.lockForConfiguration()
    session.audioSessionDidActivate(AVAudioSession.sharedInstance())
    session.isAudioEnabled = true
    session.unlockForConfiguration()
    LogService.logNative(1, category: "CALL", message: "RTCAudioBridge.activateAudioSession() — didActivate + isAudioEnabled=true")
}

/// Full audio session deactivation
@objc func deactivateAudioSession() {
    let session = RTCAudioSession.sharedInstance()
    session.lockForConfiguration()
    session.isAudioEnabled = false
    session.audioSessionDidDeactivate(AVAudioSession.sharedInstance())
    session.unlockForConfiguration()
    LogService.logNative(1, category: "CALL", message: "RTCAudioBridge.deactivateAudioSession() — isAudioEnabled=false + didDeactivate")
}
```

Si in `ios/QRChat/RTCAudioBridge.m`, adauga:
```objc
RCT_EXTERN_METHOD(activateAudioSession)
RCT_EXTERN_METHOD(deactivateAudioSession)
```

---

## ORDINEA DE APLICARE

```
1. FIX B (ColdStartCoordinator flag) — fundatia, nu afecteaza nimic existent
2. FIX C (CallScreen foloseste noul flag) — depinde de FIX B
3. FIX F (RTCAudioBridge metode noi) — pregatire pentru FIX A
4. FIX A (useManualAudio = true) — cea mai importanta, dar depinde de F
5. FIX D (outgoing audio activation) — protectie pentru FIX A
6. FIX E (hasPendingVoIPCall non-destructiv) — independent
```

---

## CE NU TREBUIE ATINS

- `index.js` — NU modifica nimic, flow-ul e corect
- `server/index.js` — NU modifica
- `server/push.js` — NU modifica
- `WebRTCManager.ts` — NU modifica
- `SignalingClient.ts` — NU modifica
- `MessagingService.ts` — NU modifica
- Flow-ul warm call — NU modifica nimic din warm call path
- Timeout-uri — NU modifica

## REGULI

- Dupa FIECARE fix, ruleaza `npx tsc --noEmit` si verifica ca nu sunt erori noi
- NU face build fara sa verific eu
- NU modifica alte fisiere decat cele mentionate
- Daca ai dubii la vreun fix, OPRESTE-TE si intreaba
