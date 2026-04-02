# QRChat-Audio — Cold Start Fix V2

**Codebase:** `/Users/ruslanconstantinovici/QRChat-Audio`
**Checkpoint:** `45384ab1` (Build 309 — revert aici daca ceva se strica)
**Warm calls:** FUNCTIONEAZA PERFECT — NU LE ATINGE

---

## CONTEXT — Ce se intampla acum pe cold start

1. VoIP push ajunge, CallKit apare, userul apasa Answer
2. Dar audio NU functioneaza — ecranul de apel merge, timer-ul numara, dar zero sunet
3. Caller-ul pica — primeste un `call-ended` vechi din coada de mesaje pending
4. Video call face CRASH pe cold start

---

## FIX 1 — CRITICAL: isAudioEnabled = true in AppDelegate (nativ)

**Fisier:** `ios/QRChat/AppDelegate.swift`

**Problema:** Cu `useManualAudio = true`, WebRTC nu reda audio pana cand `isAudioEnabled = true`. In observer-ul `AVAudioSession.interruptionNotification` (cand CallKit activeaza audio), se apeleaza `audioSessionDidActivate()` dar NU se seteaza `isAudioEnabled = true`. JS-ul il seteaza mai tarziu prin `RTCAudioBridge`, dar pe cold start JS-ul poate sa nu fie gata inca.

**Fix:** In observer-ul de interruption notification, cand type == .ended, adauga `session.isAudioEnabled = true` IMEDIAT dupa `audioSessionDidActivate`:

Cauta acest bloc (in jurul liniei 56-61):
```swift
if type == .ended {
    // Audio session activated by CallKit — notify WebRTC
    session.audioSessionDidActivate(AVAudioSession.sharedInstance())
    LogService.logNative(1, category: "CALL", message: "Audio interruption ended — notified WebRTC via audioSessionDidActivate")
}
```

Inlocuieste cu:
```swift
if type == .ended {
    // Audio session activated by CallKit — notify WebRTC + enable audio
    session.audioSessionDidActivate(AVAudioSession.sharedInstance())
    session.isAudioEnabled = true  // CRITICAL: without this, useManualAudio blocks all audio
    LogService.logNative(1, category: "CALL", message: "Audio interruption ended — audioSessionDidActivate + isAudioEnabled=true")
}
```

Si pentru deactivare (type == .began), adauga `isAudioEnabled = false`:
```swift
} else if type == .began {
    // Audio interrupted (e.g., phone call, Siri)
    session.isAudioEnabled = false
    session.audioSessionDidDeactivate(AVAudioSession.sharedInstance())
    LogService.logNative(2, category: "CALL", message: "Audio interruption began — isAudioEnabled=false + didDeactivate")
}
```

---

## FIX 2 — CRITICAL: Curata mesaje call-ended vechi din coada

**Fisier:** `server/index.js`

**Problema:** Cand callee-ul se conecteaza dupa cold start, serverul flush-uieste TOATE mesajele pending. Printre ele sunt `call-ended` de la incercari de apel ANTERIOARE (care au esuat). Aceste mesaje vechi ajung la caller si ii spun ca callee-ul a inchis — caller-ul termina apelul.

**Fix:** In handler-ul de `register` (cand callee se inregistreaza si are un apel activ), STERGE mesajele de tip `call-ended` din pending queue INAINTE de flush. Pastreaza doar mesajele care sunt mai noi decat apelul activ.

Cauta in functia de flush pending messages (in zona `case 'register'`), locul unde se itereaza `pendingMessages.get(userId)`. INAINTE de flush, adauga:

```javascript
// Clean stale call signals from pending queue when an active call exists
// Old call-ended from previous failed attempts confuse the current call
const activeCall = activeCalls.get(userId);
if (activeCall && pending.length > 0) {
    const activeCallTimestamp = activeCall.timestamp;
    const beforeClean = pending.length;
    const cleaned = pending.filter(msg => {
        // Remove call-ended messages older than current active call
        if (msg.data.type === 'call-ended' && msg.timestamp < activeCallTimestamp) {
            return false;
        }
        // Remove old call offers that are NOT the current active call
        if (msg.data.type === 'offer' && msg.data.payload?.isCall &&
            msg.data.from !== activeCall.from && msg.timestamp < activeCallTimestamp) {
            return false;
        }
        return true;
    });
    if (cleaned.length !== beforeClean) {
        pendingMessages.set(userId, cleaned);
        console.log(`[Q] Cleaned ${beforeClean - cleaned.length} stale call signals for ${userId.substring(0, 8)}... (active call from ${activeCall.from.substring(0, 8)}...)`);
    }
}
```

Gaseste exact locul unde se face flush-ul pending messages dupa registration si pune acest cod INAINTE de bucla de flush.

---

## FIX 3 — HIGH: Skip video transceiver pe cold start incoming

**Fisier:** `src/network/WebRTCManager.ts`

**Problema:** `pc.addTransceiver('video', { direction: 'inactive' })` se adauga in `answerCall()` pentru TOATE apelurile audio. Pe cold start incoming, aceasta cauzeaza crash (video transceiver creat cand PeerConnection nu e stabil). De asemenea, mareste SDP-ul la 7.8KB (de aceea PATH A esueaza mereu — SDP nu incape in VoIP push 5KB).

**Fix:** In `answerCall()`, adauga video transceiver DOAR daca NU e cold start incoming:

Cauta in answerCall (in jurul zonei unde se adauga video transceiver):
```typescript
if (!isVideo) {
    peerConnection.addTransceiver('video', { direction: 'inactive' });
}
```

Inlocuieste cu:
```typescript
// Pre-negotiate video transceiver for warm calls only.
// On cold start, skip to keep SDP small enough for VoIP push PATH A (~2KB vs 7.8KB)
// and avoid crash from transceiver creation during unstable PeerConnection state.
const isColdStart = ColdStartCoordinator.isColdStartIncomingCall;
if (!isVideo && !isColdStart) {
    peerConnection.addTransceiver('video', { direction: 'inactive' });
}
```

Asigura-te ca ColdStartCoordinator e importat la inceputul fisierului. Cauta daca exista deja un import; daca nu, adauga:
```typescript
import ColdStartCoordinator from '../services/ColdStartCoordinator';
```

ACEEASI modificare si in `startCall()` — dar acolo e mereu outgoing, deci nu e cold start. Verifica ca exista deja guard-ul doar in answerCall.

---

## ORDINEA DE APLICARE

```
1. FIX 1 — AppDelegate isAudioEnabled (cea mai importanta — cauza audio)
2. FIX 2 — Server cleanup stale messages (cauza caller drop)
3. FIX 3 — Skip video transceiver cold start (cauza crash + SDP size)
```

## DUPA TOATE FIX-URILE

1. Ruleaza `npx tsc --noEmit` — verifica ca nu sunt erori noi
2. NU face build — asteapta confirmare
3. NU modifica alte fisiere decat cele mentionate
4. NU atinge warm call flow

## CE NU TREBUIE ATINS

- index.js — NU modifica
- CallScreen.tsx — NU modifica (fix-urile anterioare sunt corecte)
- ColdStartCoordinator.ts — NU modifica
- CallKitService.ts — NU modifica
- Warm call path — NU modifica NIMIC
