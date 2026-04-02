# Audit QA — QRChat v4.0.0
Data: 2026-03-21

## Rezumat
- Teste: **9/9 PASS** (3 suites, 0 failures, 0 skipped)
- npm audit (root): **7 vulnerabilitati** (6 moderate, 1 high) — toate dev-only (CLI)
- npm audit (server): **0 vulnerabilitati**
- TypeScript: **0 erori** (tsc --noEmit clean)
- Coverage: **6.29% statements / 7.03% lines** — critic de scazut
- Empty catch blocks: **~12 truly empty** din 187 total catch blocks
- Console cleanup: babel-plugin-transform-remove-console configurat pentru productie

---

## Test Results

| Suite | Fisier | Tests | Pass | Fail | Skip |
|-------|--------|-------|------|------|------|
| push-server | `__tests__/push-server.test.js` | 5 | 5 | 0 | 0 |
| PushTokenService | `__tests__/PushTokenService.test.ts` | 3 | 3 | 0 | 0 |
| App render | `__tests__/App.test.tsx` | 1 | 1 | 0 | 0 |
| **TOTAL** | | **9** | **9** | **0** | **0** |

**Timp executie:** ~9s

### Warnings in Test Output

| # | Tip | Descriere | Severitate |
|---|-----|-----------|------------|
| 1 | act() warning | SplashScreen state update not wrapped in act() (`App.test.tsx`) | Medium |
| 2 | ReferenceError | `import` after Jest environment torn down — SplashScreen Animated.Value | Medium |
| 3 | TypeError | `window.dispatchEvent is not a function` — react-test-renderer error handling | Low |
| 4 | Worker leak | Worker process force exited — active timers/handles not cleaned up | Medium |
| 5 | Watchman | Recrawled 11 times — watchman needs `watch-del` + `watch-project` reset | Low |

---

## npm Audit — Root

| Pachet | Severitate | Tip | Fix |
|--------|-----------|-----|-----|
| fast-xml-parser 4.0.0-beta.3 - 5.5.6 | **HIGH** | Entity expansion bypass (GHSA-jp2q-39xq-3w4g) | `npm audit fix --force` → @react-native-community/cli@20.1.2 |
| fast-xml-parser (same) | MODERATE | Numeric entity expansion bypass (GHSA-8gc5-j5rx-235r) | Same fix |
| @react-native-community/cli-config-android | MODERATE | Depends on vulnerable fast-xml-parser | Transitive |
| @react-native-community/cli-platform-android | MODERATE | Transitive | Transitive |
| @react-native-community/cli-platform-apple | MODERATE | Transitive | Transitive |
| @react-native-community/cli-platform-ios | MODERATE | Transitive | Transitive |
| @react-native-community/cli-doctor | MODERATE | Transitive | Transitive |

**Total:** 7 vulnerabilitati (6 moderate, 1 high)
**Toate sunt dev-only** — afecteaza doar CLI-ul React Native, NU runtime-ul aplicatiei.
**socket.io-client:** Nu exista in package.json (corect eliminat).

## npm Audit — Server

**0 vulnerabilitati.** Server dependencies sunt curate.

---

## TypeScript Errors

**Zero errors.** `npx tsc --noEmit` ruleaza clean fara nicio eroare.

---

## Test Coverage Gaps

**Coverage total: 6.29% statements / 1.3% branches / 2.11% functions / 7.03% lines**

| Fisier | % Stmts | % Lines | Testat? | Prioritate |
|--------|---------|---------|---------|-----------|
| `src/crypto/DoubleRatchet.ts` | ~0% | ~0% | NU | **CRITICA** |
| `src/crypto/KeyManager.ts` | ~0% | ~0% | NU | **CRITICA** |
| `src/crypto/RatchetStore.ts` | ~0% | ~0% | NU | **CRITICA** |
| `src/storage/Database.ts` | 3.05% | 3.38% | Minimal | **CRITICA** |
| `src/services/MessagingService.ts` | 1.29% | 1.42% | Minimal | **CRITICA** |
| `src/network/WebRTCManager.ts` | 4.86% | 5.17% | Minimal | HIGH |
| `src/network/SignalingClient.ts` | 6.45% | 7.60% | Minimal | HIGH |
| `src/network/DHTManager.ts` | 5.66% | 6.59% | Minimal | HIGH |
| `src/network/GossipProtocol.ts` | 10% | 10.86% | Minimal | MEDIUM |
| `src/services/NotificationService.ts` | 8.10% | 9.37% | Minimal | MEDIUM |
| `src/services/CallKitService.ts` | 12.5% | 15.38% | Minimal | MEDIUM |
| `src/services/PushTokenService.ts` | 69.56% | 69.56% | **DA** | LOW |
| `src/screens/ChatScreen.tsx` | 1.10% | 1.36% | NU | MEDIUM |
| `src/screens/HomeScreen.tsx` | 0.90% | 0.99% | NU | MEDIUM |
| `src/utils/helpers.ts` | 1.66% | 2.08% | NU | LOW |

**Nota:** Doar `PushTokenService.ts` (69.56%), `soundOptions.ts` (100%), si `version.ts` (100%) au coverage semnificativ. Restul codebase-ului este practic netestat.

---

## Empty Catch Blocks

### Truly Empty (fara logging — problematice)

| # | Fisier | Linia | Cod | Risc |
|---|--------|-------|-----|------|
| 1 | `WebRTCManager.ts` | 414 | `catch (e) {}` — peer connection close | Medium |
| 2 | `SignalingClient.ts` | 245 | `.catch(() => {})` — reconnect attempt | Medium |
| 3 | `SignalingClient.ts` | 257 | `.catch(() => {})` — reconnect attempt | Medium |
| 4 | `SignalingClient.ts` | 479 | `.catch(() => {})` — reconnect attempt | Medium |
| 5 | `ContactProfileScreen.tsx` | 122 | `catch (_) {}` — RNFS.unlink | Low |
| 6 | `ContactProfileScreen.tsx` | 137 | `catch (_) {}` — RNFS.unlink | Low |
| 7 | `ContactProfileScreen.tsx` | 175 | `catch (_) {}` — RNFS.unlink | Low |
| 8 | `ContactProfileScreen.tsx` | 194 | `.catch(() => {})` — Linking.openURL | Low |
| 9 | `NotificationBanner.tsx` | 34 | `catch(e) {}` — Vibration.vibrate | Low |
| 10 | `SupportScreen.tsx` | 19,31,37,43 | `.catch(() => {})` — Linking.openURL (x4) | Low |
| 11 | `CallKitService.ts` | 107 | `catch (e) {}` — RNCallKeep.endCall | Medium |
| 12 | `NotificationService.ts` | 173 | `catch (e) { /* ignore */ }` — SystemSoundModule | Low |
| 13 | `HomeScreen.tsx` | 346,360 | `catch (e) { /* vibration */ }` — Vibration | Low |

### With Logging (acceptabile) — ~38 catch blocks au `console.warn`/`console.error`

**Total catch blocks:** 187 in `src/`
**Truly empty:** ~15 (8% din total)
**Cu logging:** ~172 (92% din total) — acceptabil

---

## Probleme Gasite

| # | Tip | Descriere | Severitate |
|---|-----|-----------|------------|
| 1 | Coverage | Coverage total 6.29% — niciun modul critic (crypto, DB, messaging) nu are teste dedicate | **CRITICA** |
| 2 | Missing Tests | DoubleRatchet.ts, KeyManager.ts, RatchetStore.ts — modulele crypto au ZERO teste | **CRITICA** |
| 3 | Missing Tests | Database.ts (1404 linii) — 3.05% coverage, fara test suite dedicat | **CRITICA** |
| 4 | Missing Tests | MessagingService.ts (2226 linii) — 1.29% coverage, cel mai mare fisier din proiect | **HIGH** |
| 5 | Test Leak | Worker process force exited — timere active neoprite in App.test.tsx (SplashScreen) | **HIGH** |
| 6 | act() Warning | State update in SplashScreen not wrapped in act() — test instabil | MEDIUM |
| 7 | Timer Mismatch | 63 setTimeout/setInterval vs 52 clearTimeout/clearInterval — 11 potential leaks | MEDIUM |
| 8 | Empty Catches | ~15 catch blocks complet goale — pot ascunde erori in networking/calls | MEDIUM |
| 9 | npm Vuln | fast-xml-parser HIGH vulnerability — dev-only dar trebuie actualizat | LOW |
| 10 | Watchman | Recrawled 11x — performanta watchman degradata | LOW |

---

## Jest Config — Analiza

| Verificare | Status |
|-----------|--------|
| Preset: `react-native` | OK |
| `transformIgnorePatterns` include module native | OK (22 module listate) |
| `jest.setup.js` mock RNFS | OK |
| `jest.setup.js` mock Keychain | OK |
| `jest.setup.js` mock WebRTC | OK |
| `jest.setup.js` mock op-sqlite | OK |
| `jest.setup.js` mock Notifee | OK |
| `jest.setup.js` mock CameraKit | OK |
| `jest.setup.js` mock Contacts | OK |
| `jest.setup.js` mock InCallManager | OK |
| `jest.setup.js` mock CallKeep | OK |
| Mock-uri realiste (date valide) | OK — mock-urile returneaza date realiste |

---

## iOS Build Artifacts

| Verificare | Status | Detalii |
|-----------|--------|---------|
| `main.jsbundle` exista | OK | 3.0MB, Mar 19 16:32 |
| Simulatoare disponibile | OK | iPhone 16e (Booted), iPhone 17 Pro, iPhone Air |
| `Podfile.lock` exista | OK | 76KB, Mar 18 17:11 |

---

## Dependente

| Verificare | Status |
|-----------|--------|
| Toate instalate corect | OK — npm ls --depth=0 fara erori |
| React Native 0.84.0 | OK — stable release |
| React 19.2.3 | OK — stable |
| TypeScript 5.9.3 | OK |
| socket.io-client eliminat | OK — nu exista in package.json |
| UNMET PEER DEPENDENCY | Niciuna |

---

## Console.log in Productie

| Verificare | Status |
|-----------|--------|
| `babel-plugin-transform-remove-console` | OK — configurat in babel.config.js env.production |
| Console statements in src/ | 309 total (log+warn+error) — eliminate automat in production build |

---

## Substring Null Safety

Majoritatea `.substring()` calls folosesc optional chaining (`?.substring(0, 8)`) sau sunt apelate pe variabile known-string (hexKey, base64Data, locale). Cateva apelari directe pe `item.content.substring()` si `name.substring()` exista in screens dar sunt protejate prin context (item.content e string din DB, name e din contact). **Risc rezidual: LOW.**

---

## Recomandari

### Prioritate CRITICA
1. **Adauga teste pentru crypto modules** — DoubleRatchet.ts, KeyManager.ts, RatchetStore.ts sunt fundamentul securitatii si nu au NICIUN test
2. **Adauga test suite pentru Database.ts** — 1404 linii, 25+ metode, migrari complexe, 3% coverage
3. **Adauga test suite pentru MessagingService.ts** — 2226 linii, logica critica de mesagerie, 1.29% coverage

### Prioritate HIGH
4. **Fix test leak in App.test.tsx** — wrap SplashScreen render in act(), cleanup timers with `jest.useFakeTimers()` + `jest.runAllTimers()` + `jest.useRealTimers()`
5. **Adauga teste WebRTC/Signaling** — WebRTCManager si SignalingClient sunt critice pentru apeluri
6. **Audit timer cleanup** — 11 setTimeout/setInterval fara clear corespunzator (potential memory leaks)

### Prioritate MEDIUM
7. **Adauga `console.warn` in catch blocks goale** din SignalingClient reconnect si CallKitService — ajuta la debugging in dezvoltare
8. **Run `npm audit fix --force`** pentru fast-xml-parser — dev-only dar buna practica
9. **Fix watchman**: `watchman watch-del '/Users/ruslanconstantinovici/QRChat' ; watchman watch-project '/Users/ruslanconstantinovici/QRChat'`

### Target Coverage Recomandat
- **Faza 1:** Crypto modules la >80% coverage
- **Faza 2:** Database + MessagingService la >50% coverage
- **Faza 3:** Network modules la >40% coverage
- **Target global:** >30% (de la 6.29% actual)
