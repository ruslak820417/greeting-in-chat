# Prompt: QA Audit Complet — qa-engineer

**Rol:** Esti qa-engineer pentru QRChat, un messenger criptat end-to-end React Native.
**Proiect:** `/Users/ruslanconstantinovici/QRChat`
**Tech:** Jest 29, React Native 0.84, TypeScript 5.8

---

## SARCINA

Executa un audit complet de calitate al aplicatiei QRChat. Ruleaza TOATE testele, verifica npm audit, analizeaza test coverage, si testeaza pe simulator. Scrie un raport cu starea calitatii.

---

## VERIFICARI (executa pe rand)

### 1. Ruleaza testele Jest

```bash
cd /Users/ruslanconstantinovici/QRChat && npx jest --verbose --no-cache 2>&1
```

Verifica:
- [ ] Toate testele PASS (51/51 conform PROJECT_STATUS)
- [ ] Zero failures
- [ ] Zero skipped
- [ ] Timpul total de executie
- [ ] Niciun warning critic in output

### 2. Test Suites — Inventar

Citeste fisierele de test:

| # | Test Suite | Fisier | Teste | Ce testeaza |
|---|-----------|--------|-------|-------------|
| 1 | App render | `__tests__/App.test.tsx` | 1 | App renders |
| 2 | PushTokenService | `__tests__/PushTokenService.test.ts` | ~10 | Mailbox ID, push token |
| 3 | Push server | `__tests__/push-server.test.js` | ~15 | Server push module |

Verifica:
- [ ] Exista si alte teste? (cauta in `__mocks__/`, subdirectoare)
- [ ] Teste suplimentare mentionate in PROJECT_STATUS: DoubleRatchet, KeyManager, Database — unde sunt?
- [ ] Exista `jest.config.js` corect configurat

```bash
# Cauta toate fisierele de test
find /Users/ruslanconstantinovici/QRChat -name "*.test.*" -o -name "*.spec.*" | grep -v node_modules
```

### 3. Jest Config — Analiza

Citeste: `jest.config.js` si `jest.setup.js`

Verifica:
- [ ] Preset: `react-native`
- [ ] `transformIgnorePatterns` include TOATE modulele native necesare
- [ ] `jest.setup.js` mock-uieste: RNFS, Keychain, WebRTC, op-sqlite, Notifee, CameraKit, Contacts
- [ ] Mock-urile sunt realiste (returneaza date valide)

### 4. npm audit — Vulnerabilitati

```bash
cd /Users/ruslanconstantinovici/QRChat && npm audit 2>&1
```

Verifica:
- [ ] Cate vulnerabilitati totale?
- [ ] Cate sunt in productie vs dev-only?
- [ ] Severitate: critical / high / moderate / low
- [ ] `socket.io-client` sters (era nefolosit)?

```bash
# Verifica daca socket.io-client mai exista
grep -r "socket.io" /Users/ruslanconstantinovici/QRChat/package.json
```

### 5. npm audit — Server

```bash
cd /Users/ruslanconstantinovici/QRChat/server && npm audit 2>&1
```

Verifica:
- [ ] Dependente server: express, ws, tweetnacl, @parse/node-apn
- [ ] Vulnerabilitati server

### 6. TypeScript — Erori de compilare

```bash
cd /Users/ruslanconstantinovici/QRChat && npx tsc --noEmit 2>&1 | head -50
```

Verifica:
- [ ] Zero TypeScript errors (conform PROJECT_STATUS: 38 -> 0)
- [ ] Daca apar erori, listeaza-le pe toate

### 7. Empty Catch Blocks

```bash
grep -rn "catch\s*(" /Users/ruslanconstantinovici/QRChat/src/ | grep -v "console\.\|// " | head -20
```

Verifica:
- [ ] Toate catch blocks au `console.warn` sau `console.error` (conform PROJECT_STATUS: 24 -> 0)
- [ ] Nu exista catch blocks goale (silentiaza erorile)

### 8. Test Coverage — Evaluare

Ruleaza testele cu coverage:
```bash
cd /Users/ruslanconstantinovici/QRChat && npx jest --coverage --no-cache 2>&1 | tail -30
```

Verifica:
- [ ] Coverage total: X%
- [ ] Fisiere critice fara teste:
  - `src/crypto/DoubleRatchet.ts` — are teste?
  - `src/crypto/KeyManager.ts` — are teste?
  - `src/storage/Database.ts` — are teste?
  - `src/services/MessagingService.ts` — are teste?
  - `src/network/WebRTCManager.ts` — are teste?
  - `src/network/SignalingClient.ts` — are teste?

### 9. Build iOS Simulator — Test

Verifica daca aplicatia compileaza si ruleaza:
```bash
# Verifica daca simulatorul exista
xcrun simctl list devices available | grep -E "iPhone 16e|iPhone 17 Pro"

# Verifica daca bundle-ul JS exista
ls -la /Users/ruslanconstantinovici/QRChat/ios/main.jsbundle
```

Nota: Nu rula build complet (dureaza mult), dar verifica:
- [ ] `main.jsbundle` exista si e recent (3MB+)
- [ ] Simulatoare disponibile
- [ ] `Podfile.lock` exista si e consistent

### 10. Dependente — Analiza

```bash
cd /Users/ruslanconstantinovici/QRChat && npm ls --depth=0 2>&1 | tail -30
```

Verifica:
- [ ] Toate dependentele instalate corect (fara UNMET PEER DEPENDENCY)
- [ ] React Native 0.84 compatibil cu toate modulele native
- [ ] `react` 19.2.3 si `react-native` 0.84.0 — sunt versiuni stable?

### 11. Potential Race Conditions

Cauta in codebase:
```bash
grep -rn "setTimeout\|setInterval" /Users/ruslanconstantinovici/QRChat/src/ | wc -l
```

Verifica:
- [ ] Toate `setTimeout`/`setInterval` au cleanup (clearTimeout/clearInterval)
- [ ] Nu exista accesari de state dupa unmount (memory leaks)
- [ ] `useEffect` cleanup functions prezente pentru subscriptii

### 12. Console.log in Productie

```bash
grep -rn "console\.log\|console\.warn\|console\.error" /Users/ruslanconstantinovici/QRChat/src/ | wc -l
```

Verifica:
- [ ] `babel-plugin-transform-remove-console` configurat in `babel.config.js`?
- [ ] Sau `console.log` ramane in productie? (potential leak de informatii)

```bash
cat /Users/ruslanconstantinovici/QRChat/babel.config.js
```

### 13. Substring Null Safety

Verifica fix-ul mentionat in PROJECT_STATUS:
```bash
grep -rn "\.substring\b" /Users/ruslanconstantinovici/QRChat/src/ | grep -v "?\.substring\|?\.\substring" | head -10
```

- [ ] Toate `.substring()` au optional chaining (`?.substring`) sau null check

---

## FISIERE DE CITIT (lista completa)

| Fisier | Ce verifici |
|--------|------------|
| `__tests__/App.test.tsx` | Test render |
| `__tests__/PushTokenService.test.ts` | Push tests |
| `__tests__/push-server.test.js` | Server push tests |
| `__mocks__/` | Mock files |
| `jest.config.js` | Jest config |
| `jest.setup.js` | Mock setup |
| `babel.config.js` | Babel config |
| `package.json` | Dependente, scripts |
| `tsconfig.json` | TypeScript config |

---

## COMANDA DE VERIFICARE

Ai terminat cand:
1. Ai rulat `npx jest --verbose` si ai rezultatul complet
2. Ai rulat `npm audit` pe ambele (root + server)
3. Ai rulat `npx tsc --noEmit`
4. Ai o lista de fisiere fara test coverage
5. Ai un scor: X/51 teste pass, Y vulnerabilitati, Z TypeScript errors

---

## UNDE SCRII RAPORTUL

Scrie rezultatul in:
```
/Users/ruslanconstantinovici/Projects/Agent Teams/agent-runtime/outputs/audit-qa.md
```

Format:
```markdown
# Audit QA — QRChat v4.0.0
Data: [data curenta]

## Rezumat
- Teste: XX/XX PASS
- npm audit: XX vulnerabilitati (YY productie)
- TypeScript: XX erori
- Coverage: XX%

## Test Results
| Suite | Tests | Pass | Fail | Skip |
|-------|-------|------|------|------|

## npm Audit
| Pachet | Severitate | Tip | Fix |
|--------|-----------|-----|-----|

## TypeScript Errors
[lista sau "Zero errors"]

## Test Coverage Gaps
| Fisier | Linii | Testat? | Prioritate |
|--------|-------|---------|-----------|

## Probleme Gasite
| # | Tip | Descriere | Severitate |
|---|-----|-----------|------------|

## Recomandari
1. ...
```
