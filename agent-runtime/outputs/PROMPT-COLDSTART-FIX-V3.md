# QRChat-Audio — Cold Start Fix V3 (DEFINITIV)

**Codebase:** `/Users/ruslanconstantinovici/QRChat-Audio`
**Checkpoint:** `45384ab1` (revert daca ceva se strica)
**Warm calls:** FUNCTIONEAZA PERFECT — NU LE ATINGE

---

## ANALIZA ROOT CAUSE

Cold start esueaza din cauza a 3 probleme independente care se combina:

### Problema 1: PATH A esueaza mereu
SDP-ul e prea mare (7875B > 4800B limita VoIP push) din cauza video transceiver pre-negotiated pe OUTGOING call (startCall adauga `addTransceiver('video', {direction: 'inactive'})` care mareste SDP-ul de la ~2KB la ~7KB). VoIP push se trimite FARA SDP. UserDefaults are `callInfo` dar fara `sdp` → PATH A returneaza FAIL.

### Problema 2: PATH C e blocat de guard-ul anti-duplicate
In App.tsx linia 182, guard-ul `ColdStartCoordinator.isActive` blocheaza TOATE `incoming-call` events cand cold start e activ. Dar PATH C depinde de exact aceste events! Pending queue flush livreaza offer-ul prin `incoming-call` EventBus, dar guard-ul il blocheaza.

### Problema 3: PATH B nu primeste raspuns
`ColdStartCoordinator.run()` se apeleaza DUPA `isSetupComplete` (care depinde de `MessagingService.initialize()`). Dar `MessagingService.initialize()` conecteaza WebSocket-ul care triggereaza server flush de pending messages INAINTE ca `run()` sa se apeleze. Cand `run()` ajunge la PATH B si trimite `get-call-state`, serverul a STERS deja offer-ul din activeCalls (dupa ce l-a livrat prin pending flush).

### Problema 4: SDP prea mare pe startCall (outgoing)
`startCall()` adauga video transceiver pre-negotiated. Aceasta mareste SDP offer-ul la 7.8KB. Pe warm call nu conteaza (se trimite direct prin WebSocket). Pe cold start PATH A, nu incape in VoIP push.

---

## SOLUTIA (4 fix-uri)

### FIX 1 — CRITICAL: Schimba ordinea — ruleaza ColdStartCoordinator.run() INAINTE de MessagingService.initialize()

**Fisier:** `App.tsx`

**Logica:** In `checkSetup()`, apeleaza `ColdStartCoordinator.run()` INAINTE de `MessagingService.initialize()`. Asa, PATH A se incearca inainte de orice. Daca PATH A esueaza, `run()` face `initializeFastPath()` singur (deja are acest cod) si trimite `get-call-state` INAINTE ca pending flush sa ajunga.

**Ce sa faci:**

1. In useEffect-ul cold start coordinator (liniile ~317-350), MUTA apelul `ColdStartCoordinator.run()` sa se faca INAINTE de `isSetupComplete`. Inlocuieste INTREGUL useEffect cu:

```typescript
// COLD START CALL COORDINATOR
useEffect(() => {
    if (ColdStartCoordinator.isHandled) return;
    if (!ColdStartCoordinator.isActive) return;
    if (!ColdStartCoordinator.hasAnswer) return; // user hasn't answered yet on CallKit

    // Run coordinator IMMEDIATELY — don't wait for isSetupComplete.
    // ColdStartCoordinator.run() calls initializeFastPath() internally if WebSocket not connected.
    // This ensures PATH B (get-call-state) runs BEFORE MessagingService.initialize() flushes pending queue.
    ColdStartCoordinator.run();
}, []); // Empty deps — run on mount if cold start with answer
```

2. STERGE complet polling-ul `checkPending` din acest useEffect (liniile 324-346). Nu mai e necesar — userul deja a raspuns daca `hasAnswer` e true.

3. De asemenea, useEffect-ul depindea de `[isSetupComplete]`. Schimba la `[]` — sa ruleze la mount, nu cand setup se finalizeaza. ColdStartCoordinator.run() are propriul `initializeFastPath()` care conecteaza WebSocket-ul independent.

### FIX 2 — CRITICAL: Permite PATH C sa functioneze (fix guard-ul)

**Fisier:** `App.tsx`

**Problema:** Guard-ul de la linia 182 blocheaza TOATE incoming-call events cand `ColdStartCoordinator.isActive` e true. Dar PATH C are nevoie de aceste events.

**Ce sa faci:** Modifica guard-ul sa permita PATH C. Inlocuieste:

```typescript
// INAINTE (blocheaza PATH C):
if (ColdStartCoordinator.isHandled || ColdStartCoordinator.isColdStartIncomingCall || ColdStartCoordinator.isActive) {
    console.log('[App] incoming-call ignored — cold start active/handled, VoIP push already showed CallKit');
    return;
}
```

Cu:

```typescript
// DUPA (permite PATH C, blocheaza doar duplicate):
if (ColdStartCoordinator.isHandled) {
    console.log('[App] incoming-call ignored — cold start already handled');
    return;
}

// Delegate cold start PATH C: if user answered on CallKit, navigate to CallScreen
if (ColdStartCoordinator.handleIncomingCallDuringColdStart(data)) {
    incomingCallRef.current = null;
    return;
}

// If cold start is active but not yet handled, don't show duplicate CallKit
if (ColdStartCoordinator.isActive) {
    console.log('[App] incoming-call during cold start — waiting for coordinator to handle');
    return;
}
```

ATENTIE: `handleIncomingCallDuringColdStart` se apela deja la linia 188. STERGE acel apel duplicat (liniile 187-189) daca exista, ca sa nu fie apelat de 2 ori. Practic, reorganizeaza handler-ul `incoming-call` asa:

```typescript
const handler = (data: any) => {
    // 1. Already handled — ignore completely
    if (ColdStartCoordinator.isHandled) {
        console.log('[App] incoming-call ignored — cold start already handled');
        return;
    }

    // 2. Cold start PATH C: delegate to coordinator (handles answer + decline)
    if (ColdStartCoordinator.handleIncomingCallDuringColdStart(data)) {
        incomingCallRef.current = null;
        return;
    }

    // 3. Cold start active but not answered yet — don't show duplicate CallKit/overlay
    if (ColdStartCoordinator.isActive) {
        console.log('[App] incoming-call during active cold start — skipping overlay');
        return;
    }

    // 4. Normal warm call flow (existing code below)
    if (incomingCallRef.current !== null) {
        console.log('[App] Ignoring duplicate incoming-call');
        return;
    }
    incomingCallRef.current = data.contactId;
    // ... rest of existing warm call code (setIncomingCall, CallKit report, etc.)
};
```

### FIX 3 — HIGH: Skip video transceiver pe startCall (outgoing) pentru a pastra SDP mic

**Fisier:** `src/network/WebRTCManager.ts`

**Problema:** `startCall()` (outgoing) adauga `addTransceiver('video', {direction: 'inactive'})` pentru audio calls. Aceasta mareste SDP offer de la ~2KB la ~7.8KB. SDP-ul nu incape in VoIP push si PATH A esueaza mereu.

**Ce sa faci:** In `startCall()`, STERGE video transceiver pre-negotiated. Cauta:

```typescript
if (!isVideo) {
    pc.addTransceiver('video', { direction: 'inactive' });
}
```

STERGE aceste linii din `startCall()`. Video toggle va folosi `addTrack()` cu renegotiere (mai lent dar functional). Nu strica warm calls — video toggle mid-call e o functionalitate secundara, cold start call e critica.

NOTA: In `answerCall()`, video transceiver e deja conditionat de `!isColdStart` — aceasta e corect, las-o asa.

### FIX 4 — MEDIUM: Serverul sa NU stearga activeCall la pending flush

**Fisier:** `server/index.js`

**Problema:** Cand serverul flush-uieste pending messages la registration, daca include call offer-ul, serverul NU trebuie sa stearga din `activeCalls`. `get-call-state` (PATH B) depinde de `activeCalls` — daca e sters, PATH B returneaza null.

**Ce sa faci:** Verifica daca in codul de flush (sau oriunde dupa flush) exista ceva care sterge `activeCalls.get(userId)` dupa ce offer-ul e livrat. Daca da, STERGE acea linie. `activeCalls` trebuie sa ramana pana la:
- `call-ended` primit
- `answer` primit (callee a raspuns cu SDP)
- Timeout 120s (auto-cleanup)

NU sterge `activeCalls` la flush.

---

## ORDINEA DE APLICARE

```
1. FIX 3 — Sterge video transceiver din startCall (SDP mic → PATH A poate functiona)
2. FIX 1 — Run coordinator inainte de MessagingService (timing fix)
3. FIX 2 — Fix guard incoming-call (PATH C debloca)
4. FIX 4 — Server activeCall persistence (PATH B funcional)
```

## DUPA TOATE FIX-URILE

1. `npx tsc --noEmit` — zero erori noi
2. NU face build — asteapta confirmare
3. NU modifica alte fisiere decat: App.tsx, WebRTCManager.ts, server/index.js
4. NU atinge: index.js, CallScreen.tsx, ColdStartCoordinator.ts, AppDelegate.swift, CallKitService.ts

## REGULI

- Daca esti nesigur la orice fix — OPRESTE-TE si arata ce ai facut
- Dupa FIECARE fix, verifica tsc
- Arata TOATE modificarile facute la fiecare fix
