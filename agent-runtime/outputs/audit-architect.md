# Audit Arhitectura — QRChat v4.0.0
Data: 21 martie 2026

## Scor Modularitate: 4/10
## Scor Code Quality: 6/10

---

## Structura Proiect

**54 fisiere TypeScript/TSX, ~19.161 linii cod in `src/`**

```
QRChat/
  App.tsx                     (369 linii) — Root, ErrorBoundary, global handlers
  src/
    screens/       (19 fisiere, ~10.688 linii) — UI screens
    components/    (8 fisiere)    — Shared: ErrorBoundary, NotificationBanner, IncomingCallOverlay, SplashScreen
    services/      (7 fisiere)    — MessagingService, Notification, CallKit, PushToken, Licensing, Navigation
    network/       (5 fisiere, 1.832 linii) — WebRTCManager, SignalingClient, Gossip, DHT, Bootstrap
    crypto/        (3 fisiere, 535 linii) — DoubleRatchet, KeyManager, RatchetStore
    storage/       (1 fisier, 1.408 linii) — Database (SQLite + Keychain)
    utils/         (8 fisiere)    — EventBus, types, helpers, constants, ThemeContext, ActiveChatTracker
    i18n/          (5 fisiere)    — en/ro/ru/fr translations
    navigation/    (1 fisier)     — AppNavigator (Stack)
    assets/                       — Logo, images
  server/          (3 fisiere, 1.406 linii) — Node.js signaling server
  __tests__/       (2 fisiere, 105 linii) — Jest tests (VERY LOW)
```

**Verdict:** Structura e logica si consistenta. Fiecare director are responsabilitate clara. Nu exista fisiere rogue la root level. Directoarele `crypto/` si `network/` sunt bine izolate.

---

## God Objects

| Fisier | Linii | Responsabilitati | Refactorizare recomandata |
|--------|-------|-----------------|--------------------------|
| `src/screens/ChatScreen.tsx` | **3133** | UI rendering, message sending, file transfer, album grouping, photo viewer, swipe-to-reply, multi-select, reactions, reply-to, audio recording, link detection | Extrage: `useChatMessages` hook, `AlbumGroup` component, `FileTransferManager`, `MessageActions` component, `AudioRecorder` component |
| `src/services/MessagingService.ts` | **2230** | 8 callback types, send/receive text/file/audio/image, encryption, chunking, delivery tracking, reactions, contact requests, call signaling | Port refactorizarea din qrchatAndroid: facade 198 linii + 6 module (MessageSender, MessageReceiver, ChunkManager, ReactionService, DeliveryTracker, CryptoUtils) |
| `src/storage/Database.ts` | **1408** | Profile CRUD, contacts CRUD, messages CRUD, settings, keys (Keychain), groups, contact requests, migration, SQLCipher, cleanup | Split in: `ProfileStore`, `ContactStore`, `MessageStore`, `KeyStore`, `SettingsStore` |
| `src/screens/HomeScreen.tsx` | **1114** | Conversations list, swipe actions (pin/archive/block), search, multi-select, unread counts, typing indicators | Extrage: `ConversationItem` component, `useConversations` hook |
| `server/index.js` | **936** | WebSocket handling, REST endpoints, pending messages, relay, admin endpoints, rate limiting | Split in: `wsHandlers.js`, `routes.js`, `pendingStore.js` |
| `src/network/WebRTCManager.ts` | **879** | Peer connections, data channels, media streams, ICE, chunking, Perfect Negotiation | Acceptabil pentru complexitatea WebRTC, dar chunk handling se suprapune cu MessagingService |
| `src/screens/SettingsScreen.tsx` | **720** | Theme, language, notifications, privacy, self-destruct, account delete, upgrade | Extrage: `PrivacySettings`, `NotificationSettings` sectiuni |
| `src/screens/ContactProfileScreen.tsx` | **709** | Contact details, per-contact settings, media gallery, blocking, muting | Extrage: `ContactMediaGallery`, `ContactSettings` components |

### MessagingService — Analiza Detaliata

- **8 callback types:** NewMessage, Typing, Delivery, Read, Connection, DeleteMessage, EditMessage, Reaction
- **Singleton:** `export default new MessagingService()` — da
- **Double-init guard:** `this.initialized` flag — OK
- **Handler registration guard:** `this.handlersRegistered` — OK
- **File chunk buffers:** cleanup timers cu 300s TTL — OK
- **Duplicate detection:** `processingIds` Set — curatata per-mesaj dupa procesare
- **Destroy cleanup:** curata callbacks, timere, buffers, ratchet cache — OK

**Comparatie cu qrchatAndroid:**
- `qrchatAndroid/src/services/MessagingService.ts` = 198 linii (facade)
- `qrchatAndroid/src/services/messaging/` = 6 module (2126 linii total)
- **QRChat ramane monolitic la 2230 linii** — refactorizarea NU a fost portata

---

## TypeScript Quality

- **Erori compilare:** 0 (confirmat in PROJECT_STATUS; tsc --noEmit clean)
- **tsconfig:** Extends `@react-native/typescript-config` cu `strict: true` — OK
- **Types:** `["jest", "node"]` configurat — OK
- **Strict mode:** Da (din base config) — OK

### `any` Type Usage

| Metric | Count |
|--------|-------|
| `: any` instances | **161** (32 fisiere) |
| `as any` casts | **50** (11 fisiere) |
| **Total `any` usage** | **~211 instante** |

**Top offenders (`: any`):**

| Fisier | Count | Note |
|--------|-------|------|
| `screens/ChatScreen.tsx` | 30 | Event handlers, navigation params |
| `network/WebRTCManager.ts` | 25 | DataChannel, streams, SDP |
| `storage/Database.ts` | 23 | SQLite results, Keychain |
| `services/MessagingService.ts` | 18 | Payloads, encrypted data |
| `network/SignalingClient.ts` | 15 | Message handlers, WS messages |
| `screens/PhoneContactsScreen.tsx` | 6 | Contact permissions |
| `screens/CallScreen.tsx` | 6 | WebRTC streams |

**Nota pozitiva:** `crypto/` module are **0 `any`** — cod criptografic curat.

**Recomandare:** Defineste interfete pentru: `SignalingPayload`, `EncryptedEnvelope`, `FileChunkPayload`, `RelayMessage`, `WebRTCMessage`. Ar reduce ~80% din `any`.

---

## Singleton-uri (14 instante)

| # | Singleton | Fisier | Linii | Dependente |
|---|-----------|--------|-------|------------|
| 1 | Database | storage/Database.ts | 1408 | AsyncStorage, op-sqlite, Keychain |
| 2 | KeyManager | crypto/KeyManager.ts | 218 | — (standalone) |
| 3 | RatchetStore | crypto/RatchetStore.ts | 62 | Keychain |
| 4 | MessagingService | services/MessagingService.ts | 2230 | WebRTCManager, SignalingClient, KeyManager, Database, EventBus, NotificationService, DoubleRatchet, RatchetStore |
| 5 | NotificationService | services/NotificationService.ts | 257 | Notifee |
| 6 | CallKitService | services/CallKitService.ts | 163 | RNCallKeep, EventBus |
| 7 | PushTokenService | services/PushTokenService.ts | 87 | SignalingClient |
| 8 | LicensingService | services/LicensingService.ts | 130 | — |
| 9 | EventBus | utils/EventBus.ts | 32 | — |
| 10 | SignalingClient | network/SignalingClient.ts | 484 | BootstrapManager, KeyManager |
| 11 | WebRTCManager | network/WebRTCManager.ts | 879 | SignalingClient, GossipProtocol, DHTManager, Database |
| 12 | GossipProtocol | network/GossipProtocol.ts | 142 | SignalingClient |
| 13 | DHTManager | network/DHTManager.ts | 246 | SignalingClient |
| 14 | BootstrapManager | network/BootstrapManager.ts | 81 | — |

**Dependente circulare:** NU exista — verificat. network/ si storage/ nu importa MessagingService.

**Ordine de initializare obligatorie:**
```
KeyManager → Database → SignalingClient → WebRTCManager → MessagingService
```
Aceasta ordine e implicita (nu e documentata/enforced) — risc de race conditions la startup.

**Verdict:** 14 singletons e mult pentru o app mobila. Solutia ideala: React Context + provider pattern pentru servicii care depind de UI lifecycle. Singleton-urile standalone (KeyManager, EventBus, RatchetStore) sunt acceptabile.

---

## EventBus — Event-Driven Architecture

**Pattern:** Pub/sub simplu, untyped, cu error handling in emit.

**API:**
- `on(event, listener)` — returneaza functie de unsubscribe — OK
- `off(event, listener)` — remove by reference — OK
- `emit(event, ...args)` — try/catch per listener — OK

**Distinct events emise (~15):**
| Event | Emitter | Consumer(s) |
|-------|---------|-------------|
| `new-message` | MessagingService | HomeScreen, NotificationBanner, ChatScreen |
| `conversations-updated` | MessagingService, PendingApprovalScreen | HomeScreen |
| `incoming-call` | MessagingService | IncomingCallOverlay |
| `contact-accepted` | MessagingService | HomeScreen, PendingApprovalScreen |
| `contact-rejected` | MessagingService | PendingApprovalScreen |
| `file-transfer-progress` | MessagingService | ChatScreen |
| `call-log-saved` | MessagingService, CallScreen | CallLogScreen, ChatScreen |
| `callkit-answer` | CallKitService | App.tsx |
| `callkit-decline` | CallKitService | App.tsx |
| `contact-key-rotated` | MessagingService | (no visible consumer) |
| `cancel-file-download` | ChatScreen | MessagingService |

**Probleme:**
1. **Events NOT typed** — toate parametrele sunt `any`. Typo in event name = silent fail
2. **No event catalog** — events descoperite doar prin grep
3. **`contact-key-rotated` emis dar nu consumat** — dead event

**Recomandare:** Defineste `EventMap` interface cu typed events:
```typescript
interface EventMap {
  'new-message': [Message];
  'conversations-updated': [];
  'file-transfer-progress': [{ messageId: string; direction: 'send'|'receive'; percent: number; done?: boolean }];
  // etc.
}
```

---

## Error Handling Strategy

- [x] **ErrorBoundary** in App.tsx wraps totul — OK, cu retry button
- [x] **Global error handler** pentru unhandled exceptions (ErrorUtils) — OK
- [x] **Empty catch blocks:** 0 — toate au `console.warn` — OK (confirmat in PROJECT_STATUS)
- [ ] **Crash reporting:** NU exista (Sentry/Bugsnag) — planificat dar neimplementat
- [x] **LogBox ignoreLogs** configurat pentru dev warnings — OK

**Verdict:** Error handling e corect dar lipseste telemetria. In productie, crash-urile raman invizibile.

---

## Dependency Graph

```
App.tsx
  ├─ ErrorBoundary
  ├─ ThemeProvider (Context)
  ├─ IncomingCallOverlay → CallKitService, EventBus, WebRTCManager
  ├─ NotificationBanner → EventBus
  ├─ SplashScreen
  └─ AppNavigator
       └─ 19 Screens → MessagingService, Database, KeyManager, WebRTCManager
                        (import direct, fara DI/Context)

MessagingService (HUB — 8 dependente)
  ├─ WebRTCManager → SignalingClient → BootstrapManager, KeyManager
  │                 → GossipProtocol → SignalingClient
  │                 → DHTManager → SignalingClient
  │                 → Database
  ├─ SignalingClient (shared cu WebRTCManager)
  ├─ KeyManager (standalone)
  ├─ Database → AsyncStorage, op-sqlite, Keychain
  ├─ EventBus (standalone)
  ├─ NotificationService → Notifee
  ├─ DoubleRatchet (standalone)
  └─ RatchetStore → Keychain
```

**Observatii:**
- **MessagingService este hub-ul central** — 8 dependente directe
- **No circular dependencies** — verified
- **Screens importa servicii direct** (nu prin Context/DI) — tight coupling
- **SignalingClient** shared intre WebRTCManager, GossipProtocol, DHTManager — potential concurrency issues

---

## Server Architecture

| Fisier | Linii | Rol |
|--------|-------|-----|
| `index.js` | 936 | WS handling, REST endpoints, pending messages, relay, admin |
| `push.js` | 208 | Push notification delivery (APNs) |
| `licensing.js` | 262 | Promo codes, device licensing |
| **Total** | **1406** | |

**Probleme:**
1. **JSON file persistence** (`qrchat_pending_messages.json`) — fragil, nu scalabil, risc de data loss la crash
2. **Monolitic:** `index.js` (936 linii) amesteca WS handlers, REST routes, pending store, relay logic
3. **No middleware pattern** — doar admin rate limiting
4. **No TypeScript** — serverul e JavaScript pur
5. **No tests** — 0 teste pentru server

---

## React Patterns

| Metric | Count | Verdict |
|--------|-------|---------|
| Inline `onPress={() =>}` in screens | **99** | Problematic in FlatList/ScrollView — cauzeaza re-renders |
| `useCallback` usage in screens | **14** | Foarte putin — ar trebui ~50+ |
| `useMemo` usage | Neverificat | Probabil similar de scazut |
| `.push/.splice` in screens | ~10 | Pe arrays locale, nu pe state — OK |

**Probleme majore:**
1. **99 inline handlers vs 14 useCallback** — raport 7:1 invers fata de best practice
2. **FlatList renderItem** in ChatScreen si HomeScreen probabil nu e memoizat
3. **Missing React.memo** pe componente frecvent re-rendered

---

## Test Coverage

| Fisier | Linii | Ce testeaza |
|--------|-------|-------------|
| `App.test.tsx` | 13 | Smoke test (renders without crash) |
| `PushTokenService.test.ts` | 92 | Push token logic |
| **Total** | **105 linii** | **< 1% coverage** |

**Verdict:** Coverage e aproape inexistenta. Modurile critice (crypto, messaging, database) nu au teste.

---

## Technical Debt — Prioritized

| # | Problema | Severity | Fisiere | Efort | Impact |
|---|---------|----------|---------|-------|--------|
| 1 | MessagingService nefactorizat (2230 linii) — refactorizarea exista in qrchatAndroid | **CRITICAL** | services/MessagingService.ts | 4h (port) | Maintainability, bug isolation |
| 2 | ChatScreen monolitic (3133 linii) | **CRITICAL** | screens/ChatScreen.tsx | 6h | Maintainability, performance |
| 3 | Test coverage ~0% | **HIGH** | __tests__/ | 16h | Regressions, confidence |
| 4 | 211 `any` type instances | **HIGH** | 32 fisiere | 4h | Type safety, bug prevention |
| 5 | Database monolitic (1408 linii) | **MEDIUM** | storage/Database.ts | 3h | Maintainability |
| 6 | 14 singletons fara DI | **MEDIUM** | global | 8h | Testing, lifecycle |
| 7 | Untyped EventBus (15 events) | **MEDIUM** | utils/EventBus.ts | 2h | Silent failures |
| 8 | No crash reporting (Sentry) | **MEDIUM** | — | 2h | Observability |
| 9 | Server JSON persistence | **MEDIUM** | server/index.js | 4h | Data durability |
| 10 | 99 inline handlers, 14 useCallback | **LOW** | screens/ | 3h | Performance |
| 11 | Server fara TypeScript | **LOW** | server/ | 6h | Type safety |
| 12 | Missing DI/IoC | **LOW** | global | 8h | Testability |

---

## Recomandari Architecturale

### Prioritate 1 — Quick Wins (< 1 saptamana)
1. **Port MessagingService refactorizarea** din qrchatAndroid → QRChat. Codul exista deja (198 facade + 6 module). Efort: ~4h.
2. **Typed EventBus** — defineste `EventMap` interface. Elimina riscul de typos in event names. Efort: 2h.
3. **Reduce `any`** in MessagingService si SignalingClient (top offenders). Defineste 5 interfete (EncryptedEnvelope, FileChunkPayload, RelayMessage, etc.). Efort: 3h.

### Prioritate 2 — Stabilizare (1-2 saptamani)
4. **Split ChatScreen** in: `ChatScreen` (orchestrator) + `useChatMessages` hook + `MessageBubble` component + `AlbumGroup` + `FileTransferUI` + `AudioRecorder`.
5. **Split Database** in module per-domeniu: `ProfileStore`, `ContactStore`, `MessageStore`, `KeyStore`.
6. **Adauga teste** pentru: DoubleRatchet (crypto correctness), MessagingService (message flow), Database (CRUD operations).

### Prioritate 3 — Architectural (2+ saptamani)
7. **Integreaza Sentry/Bugsnag** pentru crash reporting in productie.
8. **Server: migreaza** de la JSON files la SQLite/Redis pentru pending messages.
9. **React Context** pentru servicii cu UI lifecycle (MessagingService, NotificationService) — elimina importurile directe din screens.
10. **Memoizare** — adauga `useCallback` pe handlere in FlatList, `React.memo` pe componente repetitive.

---

## Sumar

QRChat are o **fundatie solida** (crypto curat, strict TS, ErrorBoundary, no circular deps) dar sufera de **god object syndrome** — 3 fisiere monopolizeaza ~7000 linii de cod. Refactorizarea din qrchatAndroid demonstreaza ca pattern-ul corect este cunoscut dar neaplicat in proiectul principal. Prioritatea #1 este portarea acelei refactorizari, urmata de split-ul ChatScreen si cresterea test coverage de la ~0% la minimum 30% pe modulele critice.
