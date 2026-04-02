# Prompt: Architecture Audit Complet — architect

**Rol:** Esti architect pentru QRChat, un messenger criptat end-to-end React Native.
**Proiect:** `/Users/ruslanconstantinovici/QRChat`
**Tech:** React Native 0.84, TypeScript 5.8, Node.js server

---

## SARCINA

Executa un audit complet al arhitecturii QRChat. Analizeaza structura codului, TypeScript quality, modularitate, dependente intre module, technical debt, si potentialul de scalare. Scrie un raport cu starea tehnica.

---

## VERIFICARI (executa pe rand)

### 1. Structura Proiectului — Overview

```
QRChat/
  App.tsx                          — Root component (324 linii)
  src/
    screens/       (20 fisiere)    — UI screens
    components/    (8 fisiere)     — Shared components
    services/      (6 fisiere)     — Business logic
    network/       (5 fisiere)     — P2P networking
    crypto/        (3 fisiere)     — Cryptographic primitives
    storage/       (1 fisier)      — Database (SQLite + Keychain)
    utils/         (8 fisiere)     — Helpers, types, theme, events
    i18n/          (5 fisiere)     — Internationalization
    navigation/    (1 fisier)      — Stack navigator
    assets/                        — Logo, images
  server/          (4 fisiere)     — Node.js signaling server
  __tests__/       (3 fisiere)     — Jest tests
  ios/                             — Xcode project
  android/                         — Gradle project
```

Verifica:
- [ ] Structura este logica si consistenta
- [ ] Fiecare director are o responsabilitate clara
- [ ] Nu exista fisiere rogue la root level (in afara de App.tsx, configs)

### 2. God Objects — Fisiere Prea Mari

Inventar fisiere mari:

| Fisier | Linii | Problema |
|--------|-------|---------|
| `src/screens/ChatScreen.tsx` | 3133 | God screen |
| `src/services/MessagingService.ts` | 2230 | God service |
| `src/storage/Database.ts` | 1408 | God storage |
| `src/screens/HomeScreen.tsx` | 1114 | Large screen |
| `server/index.js` | 936 | Monolith server |
| `src/screens/SettingsScreen.tsx` | 794 | Large screen |
| `src/screens/ContactProfileScreen.tsx` | 815 | Large screen |

Verifica:
- [ ] `ChatScreen.tsx` (3133 linii) — ce responsabilitati are? Ce se poate extrage?
- [ ] `MessagingService.ts` (2230 linii) — PROJECT_STATUS zice ca e refactorizat in qrchatAndroid (198 + 6 module), dar in QRChat ramane monolitic. Confirma.
- [ ] `Database.ts` (1408 linii) — poate fi spart in module (MessageStore, ContactStore, KeyStore)?
- [ ] `server/index.js` (936 linii) — poate fi spart in routes + handlers?

### 3. MessagingService — Analiza Detaliata

Citeste: `src/services/MessagingService.ts` (primele 100 + ultimele 50 linii)

Verifica:
- [ ] Cate callback types are? (count: NewMessage, Typing, Delivery, Read, Connection, DeleteMessage, EditMessage, Reaction = 8 tipuri)
- [ ] Este un singleton? (`export default new MessagingService()`)
- [ ] Initializare: ce se intampla daca se apeleaza `initialize()` de 2 ori? (guard `this.initialized`)
- [ ] File chunk buffers: cleanup timers sunt setate?
- [ ] Duplicat detection: `processingIds` Set — cum se curata?

Compara cu refactorizarea din qrchatAndroid:
```bash
ls -la /Users/ruslanconstantinovici/qrchatAndroid/src/services/ 2>/dev/null || echo "qrchatAndroid not found at this path"
```

### 4. TypeScript Quality

```bash
cd /Users/ruslanconstantinovici/QRChat && npx tsc --noEmit 2>&1 | head -30
```

Verifica:
- [ ] Zero TypeScript errors
- [ ] `tsconfig.json` extinde `@react-native/typescript-config`
- [ ] `strict` mode activat? (verifica in base config)
- [ ] `types: ["jest", "node"]` configurat

Cauta `any` type usage:
```bash
grep -rn ": any" /Users/ruslanconstantinovici/QRChat/src/ | wc -l
grep -rn "as any" /Users/ruslanconstantinovici/QRChat/src/ | wc -l
```

- [ ] Cate `any` exista? Lista cele mai importante (in services, crypto, network)
- [ ] Exista alternative tipizate?

### 5. Type Definitions

Citeste: `src/utils/types.ts` (108 linii)

Verifica:
- [ ] `UserProfile` — complet? (id, displayName, publicKey, privateKeyEncrypted, fingerprint, createdAt, avatarColor, avatarUri)
- [ ] `Contact` — campuri per-contact privacy (privacyReadReceipts, etc.)
- [ ] `Message` — suporta toate content types (text, image, video, file, audio, call)
- [ ] `Message` — reactions, reply-to, forwarding sunt tipizate
- [ ] `QRPayload` — include signPub? (optional dar important)
- [ ] `ContactRequest` — status enum corect
- [ ] `SignalingMessage` — tipuri limitate (offer, answer, ice-candidate)
- [ ] Exista tipuri lipsa? (ex: Group message types? File transfer state?)

### 6. Singleton Pattern — Analiza

Cauta toate singleton-urile:
```bash
grep -rn "export default new " /Users/ruslanconstantinovici/QRChat/src/
```

Inventar:
| Singleton | Fisier | Problema potentiala |
|-----------|--------|-------------------|
| Database | `storage/Database.ts` | State global |
| KeyManager | `crypto/KeyManager.ts` | Keys in memory |
| MessagingService | `services/MessagingService.ts` | Multiple callbacks |
| SignalingClient | `network/SignalingClient.ts` | WS connection |
| WebRTCManager | `network/WebRTCManager.ts` | Peer connections |
| RatchetStore | `crypto/RatchetStore.ts` | Cache + Keychain |
| BootstrapManager | `network/BootstrapManager.ts` | Relay pool |
| NotificationService | `services/NotificationService.ts` | Notifications |
| PushTokenService | `services/PushTokenService.ts` | Push tokens |
| GossipProtocol | `network/GossipProtocol.ts` | Peer table |
| DHTManager | `network/DHTManager.ts` | DHT state |

- [ ] Sunt prea multe singleton-uri? (11+ in app)
- [ ] Dependente circulare intre singleton-uri?
- [ ] Ordine de initializare importanta? (KeyManager inainte de MessagingService)

### 7. EventBus — Event-Driven Architecture

Citeste: `src/utils/EventBus.ts` (825 bytes)

Verifica:
- [ ] Ce pattern foloseste? (pub/sub simplu?)
- [ ] Ce events sunt emise? Cauta:
```bash
grep -rn "EventBus.emit\|EventBus.on\|EventBus.off" /Users/ruslanconstantinovici/QRChat/src/ | head -20
```
- [ ] Events au tip-uri definite?
- [ ] Listeners sunt cleaned up corect? (unsubscribe in useEffect cleanup?)

### 8. Error Handling Strategy

Citeste: `src/components/ErrorBoundary.tsx` si `App.tsx` (liniile 49-57 — global error handler)

Verifica:
- [ ] ErrorBoundary in App.tsx wraps totul
- [ ] Global error handler captureaza unhandled Promise rejections
- [ ] Catch blocks in servicii: au `console.warn` (nu goale)
- [ ] Exista crash reporting? (Sentry, Bugsnag?) — PROJECT_STATUS: NU, planificat

### 9. Dependency Graph — Module Coupling

Analizeaza dependentele:

```
App.tsx
  └─ AppNavigator
       └─ Screens (20) → MessagingService, Database, KeyManager, WebRTCManager
  └─ ErrorBoundary
  └─ IncomingCallOverlay → CallKitService, EventBus
  └─ NotificationBanner → NotificationService

MessagingService
  └─ WebRTCManager → SignalingClient, GossipProtocol, DHTManager
  └─ SignalingClient → BootstrapManager, KeyManager
  └─ KeyManager → (standalone)
  └─ Database → AsyncStorage, op-sqlite, Keychain
  └─ NotificationService → Notifee
  └─ DoubleRatchet, RatchetStore
```

Verifica:
- [ ] Dependente circulare? (A importa B si B importa A)
```bash
grep -rn "from.*MessagingService" /Users/ruslanconstantinovici/QRChat/src/services/MessagingService.ts
grep -rn "MessagingService" /Users/ruslanconstantinovici/QRChat/src/network/ /Users/ruslanconstantinovici/QRChat/src/storage/
```
- [ ] Coupled too tight? (ex: screens importa direct servicii vs DI/context)

### 10. Server Architecture

Citeste: `server/index.js`, `server/push.js`, `server/licensing.js`

Verifica:
- [ ] Server e monolitic (1 fisier principal + 2 module)
- [ ] Separare: `push.js` si `licensing.js` sunt module separate — OK
- [ ] Persistent storage: JSON files pe disc — fragil, nu scalabil
- [ ] Nu exista middleware pattern (express middleware doar pentru admin rate limit)

### 11. React Patterns

Cauta anti-patterns:
```bash
# Inline functions in renders
grep -rn "onPress={() =>" /Users/ruslanconstantinovici/QRChat/src/screens/ | wc -l

# Direct state mutations
grep -rn "\.push\|\.splice" /Users/ruslanconstantinovici/QRChat/src/screens/ | head -10

# Missing useCallback
grep -rn "useCallback" /Users/ruslanconstantinovici/QRChat/src/screens/ | wc -l
```

Verifica:
- [ ] Inline functions in FlatList renderItem? (performance issue)
- [ ] `useMemo`/`useCallback` folosite unde trebuie?
- [ ] State mutations directe?

### 12. Technical Debt Summary

Inventar technical debt:

| # | Problema | Severity | Fisier | Efort |
|---|---------|----------|--------|-------|
| 1 | MessagingService nefactorizat (2230 linii) | High | services/ | 4h |
| 2 | ChatScreen monolitic (3133 linii) | High | screens/ | 6h |
| 3 | Database monolitic (1408 linii) | Medium | storage/ | 3h |
| 4 | Prea multe singleton-uri (11+) | Medium | global | 8h |
| 5 | No crash reporting (Sentry) | Medium | - | 2h |
| 6 | JSON file storage pe server | Medium | server/ | 4h |
| 7 | `any` type usage | Low | global | 2h |
| 8 | Missing DI/IoC container | Low | global | 8h |

---

## FISIERE DE CITIT (lista completa)

| Fisier | Prioritate | Ce verifici |
|--------|-----------|------------|
| `src/services/MessagingService.ts` | CRITIC | God object analysis |
| `src/screens/ChatScreen.tsx` | CRITIC | God screen analysis |
| `src/storage/Database.ts` | HIGH | Monolith storage |
| `src/utils/types.ts` | HIGH | Type completeness |
| `src/utils/EventBus.ts` | MEDIUM | Event architecture |
| `src/crypto/DoubleRatchet.ts` | MEDIUM | Crypto quality |
| `src/network/WebRTCManager.ts` | MEDIUM | Network module |
| `src/network/SignalingClient.ts` | MEDIUM | WS client |
| `App.tsx` | MEDIUM | Root structure |
| `tsconfig.json` | LOW | TS config |
| `server/index.js` | MEDIUM | Server arch |

---

## COMANDA DE VERIFICARE

Ai terminat cand:
1. Ai un inventar complet al god objects cu linii
2. Ai numarat `any` types in codebase
3. Ai analizat singleton dependency graph
4. Ai o lista de technical debt prioritizata
5. Ai un scor de modularitate (1-10)

---

## UNDE SCRII RAPORTUL

Scrie rezultatul in:
```
/Users/ruslanconstantinovici/Projects/Agent Teams/agent-runtime/outputs/audit-architect.md
```

Format:
```markdown
# Audit Arhitectura — QRChat v4.0.0
Data: [data curenta]

## Scor Modularitate: X/10
## Scor Code Quality: X/10

## Structura Proiect
[overview]

## God Objects
| Fisier | Linii | Responsabilitati | Refactorizare |
|--------|-------|-----------------|---------------|

## TypeScript Quality
- Erori: X
- `any` usage: X instante
- Strict mode: Da/Nu

## Singleton-uri (XX)
[lista cu dependente]

## Technical Debt
| # | Problema | Severity | Efort | Impact |
|---|---------|----------|-------|--------|

## Dependency Graph
[vizualizare text]

## Recomandari Architecturale
1. ...
```
