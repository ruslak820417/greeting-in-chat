# QRChat Call System — CORECTII POST-AUDIT

**Dupa implementarea celor 12 task-uri, au fost gasite urmatoarele probleme prin audit profund. Toate trebuie reparate INAINTE de build.**

**Codebase:** `/Users/ruslanconstantinovici/QRChat-Audio`

---

## FIX 1 — CRITICAL: TURN servers pierdute pe cold start PATH A

**Fisier:** `ios/QRChat/AppDelegate.swift`
**Problema:** Server-ul trimite TURN servers cu key-ul `"turn"` (compact: `{u, n, c}`), dar AppDelegate.swift NU stocheaza acest camp in UserDefaults. De asemenea, linia de diagnostic check cauta `"turnServers"` (key vechi), nu `"turn"` (key nou).

**Rezultat:** Pe cold start PATH A, TURN servers sunt pierdute complet. ICE negotiation foloseste doar STUN, care ESUEAZA pe NAT-uri simetrice. Apelurile incoming din cold start NU functioneaza corect pe multe retele mobile.

**Fix necesar:** In `pushRegistry(_:didReceiveIncomingPushWith:for:completion:)`, adauga TURN data in `callInfo` dictionary inainte de scrierea in UserDefaults:

```swift
// Dupa linia unde se seteaza callInfo["sdp"]:
if let sdp = payloadDict["sdp"] {
    callInfo["sdp"] = sdp
}
// ADAUGA ACEASTA:
if let turn = payloadDict["turn"] {
    callInfo["turn"] = turn
}

// SI fixeaza diagnostic check-ul:
// INAINTE:
let hasTurnServers = payloadDict["turnServers"] != nil
// DUPA:
let hasTurnServers = payloadDict["turn"] != nil
```

---

## FIX 2 — CRITICAL: Video transceiver pre-negotiated LIPSESTE

**Fisier:** `src/network/WebRTCManager.ts`
**Problema:** Prompt-ul cerea adaugarea unui video transceiver pre-negotiated cu `direction: 'inactive'` in `startCall()` si `answerCall()`. Aceasta NU a fost implementata. Fara ea:
- `toggleVideo()` nu gaseste video sender si apeleaza `addTrack()` care triggereaza SDP renegotiation
- Dupa toggle off (replaceTrack(null)) si toggle on din nou, sender lookup esueaza (track e null)
- Toggling video ON/OFF repetat adauga transceivers noi de fiecare data

**Fix necesar:** In `startCall()`, DUPA `localStream.getTracks().forEach(...)`, adauga:

```typescript
// Pre-negotiate video transceiver (even for audio-only calls)
// This allows toggleVideo() to use replaceTrack() without SDP renegotiation
if (!isVideo) {
  pc.addTransceiver('video', { direction: 'inactive' });
}
```

In `answerCall()`, DUPA `localStream.getTracks().forEach(...)`, la fel:

```typescript
if (!isVideo) {
  peerConnection.addTransceiver('video', { direction: 'inactive' });
}
```

SI repara sender lookup in `toggleVideo()` — inlocuieste:
```typescript
// INAINTE (gresit — nu gaseste sender cand track e null):
const videoSender = senders.find(s => s.track?.kind === 'video');
```
Cu:
```typescript
// DUPA (corect — gaseste transceiver-ul video indiferent de starea track-ului):
const videoTransceiver = peer.connection.getTransceivers()
  .find(t => t.mid !== null && (
    t.sender.track?.kind === 'video' ||
    t.receiver.track?.kind === 'video' ||
    // Fallback: transceiver added as 'video' type
    t.sender.track === null && t.receiver.track?.kind === 'video'
  ));
const videoSender = videoTransceiver?.sender;
```

Scoate complet fallback-ul `addTrack()` din `toggleVideo()` — daca transceiver-ul nu exista, returneaza false (nu addTrack).

SI adauga direction management:
```typescript
if (enable) {
  await videoSender.replaceTrack(videoTrack);
  if (videoTransceiver) videoTransceiver.direction = 'sendrecv';
} else {
  videoSender.track?.stop();
  await videoSender.replaceTrack(null);
  if (videoTransceiver) videoTransceiver.direction = 'inactive';
}
```

Aceeasi reparatie pentru `flipCamera()` — foloseste `getTransceivers()` in loc de `getSenders()`.

---

## FIX 3 — HIGH: Duplicate CallKit reports in warm background

**Fisier:** `App.tsx`
**Problema:** Cand app e in warm background (nu killed), VoIP push handler in AppDelegate raporteaza la CallKit, APOI cand JS primeste incoming-call event, App.tsx raporteaza DIN NOU la CallKit. Rezultat: **double ring pe Apple Watch/AirPods/CarPlay.**

**Fix necesar:** Inainte de `CallKitService.reportIncomingCall()` in App.tsx, verifica daca CallKit deja a fost notificat:

```typescript
// In handleIncomingCall, INAINTE de CallKitService.reportIncomingCall():
const alreadyReportedByNative = CallKitService.hasActiveCallFrom(data.contactId);
if (!alreadyReportedByNative) {
  CallKitService.reportIncomingCall(
    data.contactId,
    data.contactName,
    data.isVideo,
    data.offer,
  );
}
```

Daca `CallKitService` nu are deja metoda `hasActiveCallFrom()`, adaug-o — verifica in `activeCalls` Map daca exista deja un call de la acel contactId.

---

## FIX 4 — HIGH: toggleVideo() race condition

**Fisier:** `src/network/WebRTCManager.ts`
**Problema:** Daca userul apasa butonul video rapid de 2 ori, doua apeluri `toggleVideo()` ruleaza concurent. Ambele cer camera, ambele inlocuiesc track-ul, prima track e pierduta (camera leak).

**Fix necesar:** Adauga guard:
```typescript
private videoToggleInProgress = false;

async toggleVideo(contactId: string, enable: boolean): Promise<boolean> {
  if (this.videoToggleInProgress) return false;
  this.videoToggleInProgress = true;
  try {
    // ... logica existenta ...
  } finally {
    this.videoToggleInProgress = false;
  }
}
```

---

## FIX 5 — HIGH: saveCallLog nu e awaited inainte de endCall

**Fisier:** `src/screens/CallScreen.tsx`
**Problema:** In `finishAndGoBack()`, `saveCallLog()` e async dar NU e awaited. Imediat dupa, `WebRTCManager.endCall()` distruge peer connection. Cand `saveCallLog()` apeleaza `WebRTCManager.getCallStats()`, peer-ul e deja distrus — stats vor fi null.

**Fix necesar:**
```typescript
// INAINTE:
saveCallLog(duration);
WebRTCManager.endCall(contactId, notifyRemote);

// DUPA:
await saveCallLog(duration);
WebRTCManager.endCall(contactId, notifyRemote);
```
Sau, alternativ, captureaza stats INAINTE:
```typescript
const stats = WebRTCManager.getCallStats(contactId);
WebRTCManager.endCall(contactId, notifyRemote);
saveCallLog(duration, stats); // pass stats direct
```

---

## FIX 6 — MEDIUM: SDP minification omite a=rtcp-mux

**Fisier:** `server/push.js`
**Problema:** Filtrul de SDP minification NU pastreaza linia `a=rtcp-mux`. Aceasta linie este necesara pentru WebRTC — spune peer-ului sa multiplexeze RTP si RTCP pe acelasi port. Fara ea, unele implementari WebRTC deschid porturi separate pe TURN.

**Fix necesar:** Adauga in filtru:
```javascript
if (l.startsWith('a=rtcp-mux')) return true;
```

---

## FIX 7 — MEDIUM: NetInfo listener fara debounce

**Fisier:** `src/network/WebRTCManager.ts`
**Problema:** NetInfo emite MULTIPLE events la schimbarea retelei (WiFi off → Cellular on → etc). Fiecare event triggereaza ICE restart, consumand bugetul MAX_ICE_RESTARTS pe stari intermediare.

**Fix necesar:**
```typescript
private netInfoDebounceTimer: any = null;

// In NetInfo listener:
this.netInfoUnsubscribe = NetInfo.addEventListener(state => {
  if (this.hasActiveCall() && state.isConnected) {
    // Debounce 2s — asteapta stabilizarea retelei
    clearTimeout(this.netInfoDebounceTimer);
    this.netInfoDebounceTimer = setTimeout(() => {
      for (const [contactId, peer] of this.peers) {
        if (peer.isConnected && peer.connection.connectionState === 'connected') {
          this.attemptIceRestart(contactId);
        }
      }
    }, 2000);
  }
});
```

---

## FIX 8 — MEDIUM: CallStateMachine reset() nu notifica listeners

**Fisier:** `src/services/CallStateMachine.ts`
**Problema:** `reset()` seteaza state la 'idle' FARA sa notifice listeners. UI-ul poate ramane pe 'connected' desi state-ul intern e 'idle'.

**Fix necesar:**
```typescript
reset(): void {
  const prev = this.state;
  this.state = 'idle';
  if (prev !== 'idle') {
    this.listeners.forEach(fn => fn('idle', prev, 'timeout' as CallEvent));
  }
}
```

---

## FIX 9 — MEDIUM: flipCamera fara error handling

**Fisier:** `src/screens/CallScreen.tsx`
**Problema:** `handleFlipCamera` nu are try/catch. Daca getUserMedia esueaza, `isFrontCamera` se desyncronizeaza.

**Fix necesar:**
```typescript
const handleFlipCamera = async () => {
  try {
    await WebRTCManager.flipCamera(contactId);
    setIsFrontCamera(!isFrontCamera);
  } catch (e) {
    console.warn('[CallScreen] flipCamera failed:', e);
  }
};
```

---

## FIX 10 — LOW: "Reconnecting..." nu e i18n-izat

**Fisier:** `src/screens/CallScreen.tsx`
**Problema:** Textul "Reconnecting..." e hardcodat in engleza. Toate celelalte status strings folosesc `t('call.xxx')`.

**Fix necesar:**
```typescript
// INAINTE:
<Text style={styles.reconnectingText}>Reconnecting...</Text>
// DUPA:
<Text style={styles.reconnectingText}>{t('call.reconnecting')}</Text>
```

Si adauga in fisierele i18n (en.json, ro.json, ru.json etc.):
```json
"call": {
  "reconnecting": "Reconnecting..."
}
```

---

## FIX 11 — LOW: Animations restart in reconnecting state

**Fisier:** `src/screens/CallScreen.tsx`
**Problema:** Ripple si breathing animations se restarteaza cand callStatus devine 'reconnecting' — cade in branch-ul default. Ar trebui sa ramana in starea 'connected' vizual.

**Fix necesar:** In useEffect-ul de animatii, adauga 'reconnecting' alaturi de 'connected':
```typescript
// INAINTE:
if (callStatus === 'connected' || callStatus === 'ended') {
// DUPA:
if (callStatus === 'connected' || callStatus === 'reconnecting' || callStatus === 'ended') {
```

---

## ORDINEA DE APLICARE

```
1. FIX 1 (CRITICAL) — AppDelegate TURN storage
2. FIX 2 (CRITICAL) — Pre-negotiated video transceiver + sender lookup
3. FIX 3 (HIGH) — Duplicate CallKit dedup
4. FIX 4 (HIGH) — toggleVideo race guard
5. FIX 5 (HIGH) — saveCallLog await
6. FIX 6 (MEDIUM) — rtcp-mux in SDP filter
7. FIX 7 (MEDIUM) — NetInfo debounce
8. FIX 8 (MEDIUM) — reset() notifica listeners
9. FIX 9 (MEDIUM) — flipCamera error handling
10. FIX 10 (LOW) — i18n reconnecting
11. FIX 11 (LOW) — animations reconnecting state
```

**Dupa aplicarea tuturor fix-urilor, ruleaza `npx tsc --noEmit` pentru verificare TypeScript.**
