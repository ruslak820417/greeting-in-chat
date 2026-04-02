# PROMPT: Network Engineer — Fix Call System (WebRTC + Audio)

## Context

Citeste mai intai documentul de cercetare complet:
`/Users/ruslanconstantinovici/Projects/Agent Teams/agent-runtime/outputs/call-system-architecture.md`

Lucreaza pe codebase-ul QRChat: `/Users/ruslanconstantinovici/QRChat`

## Fisiere de modificat

- `src/screens/CallScreen.tsx` — ringback outgoing + cleanup
- `src/services/NotificationService.ts` — ringtone incoming guard
- `src/services/MessagingService.ts` — dedup offer guard imbunatatit
- `src/components/IncomingCallOverlay.tsx` — stop ringtone la accept/decline
- `src/network/WebRTCManager.ts` — glare detection pentru apeluri simultane
- `android/app/src/main/res/raw/` — fisier audio ringback custom

---

## TASK 1: Fix ringback pe Android (outgoing call)

### Problema
`InCallManager.startRingback('_DEFAULT_')` pe Android fie nu reda nimic, fie reda ringtone-ul system (melodia de apel incoming) in loc de ringback ("tuut...tuut..."). Cauza: Android nu expune un "system ringback tone" standard.

### Ce trebuie facut

1. **Creeaza fisierul audio ringback:**
   - Creeaza un fisier `incallmanager_ringback.mp3` cu tonul "tuut...tuut..." standard
   - Poate fi generat sau descarcat (425 Hz, pattern: 1s ton / 4s pauza)
   - Salveaza in `android/app/src/main/res/raw/incallmanager_ringback.mp3`
   - Pe iOS, adauga acelasi fisier in bundle Xcode (sau echivalent .caf)

2. **Modifica `CallScreen.tsx` (liniile 85-101):**

   Inlocuieste:
   ```javascript
   useEffect(() => {
     if (callStatus === 'ringing' && !isIncoming) {
       InCallManager.startRingback('_DEFAULT_');
       ringbackRef.current = true;
     } else if (ringbackRef.current) {
       InCallManager.stopRingback();
       ringbackRef.current = false;
     }
     return () => { ... };
   }, [callStatus]);
   ```

   Cu:
   ```javascript
   useEffect(() => {
     if (callStatus === 'ringing' && !isIncoming) {
       // Delay pe Android — permite WebRTC sa stabileasca audio mode
       // Previne bug-ul unde WebRTC preia audio session si opreste ringback-ul
       const delay = Platform.OS === 'android' ? 500 : 0;
       const timer = setTimeout(() => {
         // _BUNDLE_ foloseste fisierul custom din res/raw/ (Android) sau bundle (iOS)
         // _DEFAULT_ nu functioneaza pe Android — nu exista system ringback tone
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

   **IMPORTANT:** Adauga `Platform` in import-urile din react-native (daca nu exista deja).

3. **Verifica ca `InCallManager.start()` se apeleaza INAINTE de `startRingback()`:**
   In `startCall()`, `InCallManager.start({ media: ... })` este deja apelat la linia 183. OK.
   Dar ringback-ul porneste abia cand `callStatus` devine `'ringing'` (linia 203), ceea ce e DUPA `InCallManager.start()`. Flow-ul e corect.

---

## TASK 2: Fix ringtone overlap pe Android (incoming call)

### Problema
La incoming call pe Android, pot suna simultan:
1. Android notification sound (din Notifee `showCallNotification`)
2. `playRingtoneLoop()` interval (SystemSoundModule la fiecare 3s)
3. Duplicate daca offer-ul vine de doua ori (pending queue + direct)

### Ce trebuie facut

1. **In `NotificationService.ts` — adauga guard anti-overlap:**

   Adauga proprietate:
   ```typescript
   private isRingtoneActive = false;
   ```

   In `playRingtoneLoop()`:
   ```typescript
   playRingtoneLoop(soundId: string) {
     // Guard: o singura instanta de ringtone la un moment dat
     if (this.isRingtoneActive) {
       console.log('[NotificationService] Ringtone already active — skipping');
       return;
     }
     this.isRingtoneActive = true;
     // ... restul codului existent
   }
   ```

   In `stopCallRingtone()`:
   ```typescript
   stopCallRingtone() {
     this.isRingtoneActive = false;
     // ... restul codului existent
   }
   ```

2. **In `showCallNotification()` — suprima sunetul Android notification:**

   La linia unde se creeaza notificarea Android, asigura-te ca sunetul e suprimat:
   ```typescript
   android: {
     channelId: callChannelId,
     sound: undefined, // NU reda sunet prin notificare — playRingtoneLoop gestioneaza
     // ... restul config-ului
   }
   ```

   **De ce:** Notificarea Android si `playRingtoneLoop()` pot reda sunet simultan. Trebuie sa fie o singura sursa de sunet.

---

## TASK 3: Imbunatateste dedup-ul offer-urilor in MessagingService

### Problema
Guard-ul actual (`activeIncomingCallFrom`) se reseteaza la `call-ended`, dar offer-uri vechi din pending queue pot ajunge dupa reset. De asemenea, nu exista verificare pe timestamp.

### Ce trebuie facut

In `MessagingService.ts`, in handler-ul `SignalingClient.on('offer')`, DUPA guard-ul existent, adauga:

```javascript
// Guard NOU: Rejecteaza offer-uri mai vechi de 30 secunde
const callTimestamp = message.payload?.callTimestamp;
if (callTimestamp && Date.now() - callTimestamp > 30000) {
  console.log(`[MessagingService] Stale call offer (${Math.round((Date.now() - callTimestamp) / 1000)}s old) — ignoring`);
  return;
}
```

Pune acest guard IMEDIAT dupa guard-ul existent de duplicate (dupa `if (pendingCalls.has(message.from) || this.activeIncomingCallFrom === message.from)`).

Fa acelasi lucru si pe path-ul encrypted (in handler-ul de `data.isCall` din procesarea mesajelor decriptate):
```javascript
if (data.isCall) {
  if (this.activeIncomingCallFrom === contactId) { return; }
  // Guard NOU: timestamp stale
  if (data.callTimestamp && Date.now() - data.callTimestamp > 30000) {
    console.log('[MessagingService] Stale encrypted call offer — ignoring');
    return;
  }
  // ...
}
```

---

## TASK 4: Stop ringtone la Accept/Decline in IncomingCallOverlay

### Problema
`IncomingCallOverlay` nu opreste ringtone-ul direct — depinde de `CallScreen` sa faca cleanup. Dar intre momentul acceptului si navigarea la `CallScreen`, ringtone-ul continua sa sune.

### Ce trebuie facut

In componenta/logica care gestioneaza `onAccept` si `onDecline` (in App.tsx sau unde e montat IncomingCallOverlay), asigura-te ca:

```javascript
const handleAccept = () => {
  // INTAI opreste sunetul
  NotificationService.stopCallRingtone();
  NotificationService.cancelCallNotification();
  // APOI navigheaza la CallScreen
  navigation.navigate('Call', { contactId, contactName, isVideo, isIncoming: true, offer });
};

const handleDecline = () => {
  NotificationService.stopCallRingtone();
  NotificationService.cancelCallNotification();
  SignalingClient.sendCallEnded(contactId);
  // Reset state
  MessagingService.clearActiveIncomingCall();
};
```

---

## TASK 5: Glare detection pentru apeluri simultane (optional, prioritate mica)

Daca ambii utilizatori apasa "Call" in acelasi timp, ambii primesc offer de apel. Solutia:

In `MessagingService.ts`, cand primim un offer de apel:
```javascript
if (message.payload?.isCall) {
  // Verifica daca NOI suntem in curs de a apela acelasi contact
  if (WebRTCManager.hasActiveCallPeer(message.from)) {
    const isPolite = (localUserId || '') < message.from;
    if (isPolite) {
      // Cedam — anulam apelul nostru, acceptam al lor
      WebRTCManager.endCall(message.from, false);
      // Procesam offer-ul incoming normal (continua mai jos)
    } else {
      // Ignoram offer-ul lor — apelul nostru are prioritate
      return;
    }
  }
  // ... procesare normala
}
```

**IMPORTANT:** Adauga metoda `hasActiveCallPeer(contactId)` in WebRTCManager:
```typescript
hasActiveCallPeer(contactId: string): boolean {
  return this.callStreams.has(contactId);
}
```

---

## Ordinea de executie

1. **TASK 1** (ringback) — cel mai vizibil bug, fix rapid
2. **TASK 2** (ringtone overlap) — fix critic pe Android
3. **TASK 3** (dedup offers) — previne root cause-ul
4. **TASK 4** (stop ringtone la accept/decline) — previne gap intre UI transitions
5. **TASK 5** (glare) — edge case, prioritate mica

## Dupa fiecare modificare

- Build si deploy pe simulator iOS + Android
- Deploy pe dispozitiv fizic (iPhone)
- Testeaza: apel outgoing (verifica ringback), apel incoming (verifica ringtone), decline, timeout
- Testeaza: doua apeluri rapid consecutive de la acelasi contact
