# PROMPT 2 — Android Testing

**Agent tinta:** qa-engineer
**Proiect:** `/Users/ruslanconstantinovici/qrchatAndroid`
**Obiectiv:** Testeaza build-ul Android pe emulator, ruleaza teste Jest, verifica TypeScript

---

## Context

QRChat Android a fost build-uit de release-engineer. Acum trebuie testat complet pe emulator inainte de submit pe Google Play.

Configuratia masinii:
- **macOS Apple Silicon** (M-series)
- **AVD disponibil:** `Medium_Phone_API_36.1`
- **Emulator binary:** `~/Library/Android/sdk/emulator/emulator`
- **ADB:** `~/Library/Android/sdk/platform-tools/adb`
- **Package name:** `com.qrchat`

Teste existente (3 fisiere):
- `__tests__/App.test.tsx` — render basic
- `__tests__/push-server.test.js` — APNs push (5 teste)
- `__tests__/PushTokenService.test.ts` — mailbox ID (3 teste)

Jest config: `jest.config.js` cu preset `react-native`, setup in `jest.setup.js` (mock-uri pentru RNFS, Keychain, WebRTC, SQLite, Notifee, etc.)

---

## Sarcini — pas cu pas

### Pas 1 — Porneste emulatorul Android

```bash
# Porneste emulatorul in background
~/Library/Android/sdk/emulator/emulator -avd Medium_Phone_API_36.1 -no-snapshot-load -gpu host &

# Asteapta sa fie ready
~/Library/Android/sdk/platform-tools/adb wait-for-device
~/Library/Android/sdk/platform-tools/adb shell getprop sys.boot_completed
# Trebuie sa returneze "1"
```

Daca emulatorul NU porneste:
- Verifica: `~/Library/Android/sdk/emulator/emulator -list-avds` — trebuie sa apara `Medium_Phone_API_36.1`
- Pe Apple Silicon, emulatorul foloseste ARM images nativ (NU Rosetta) — nu e nevoie de HAXM
- Daca da eroare "emulator: ERROR: x86_64 emulation requires hardware acceleration", ai un system image gresit — trebuie `arm64-v8a`, nu `x86_64`

### Pas 2 — Instaleaza si porneste aplicatia

```bash
cd /Users/ruslanconstantinovici/qrchatAndroid

# Varianta A: Instaleaza APK-ul pre-build (daca release-engineer l-a generat)
~/Library/Android/sdk/platform-tools/adb install android/app/build/outputs/apk/release/app-release.apk

# Varianta B: Build + install direct pe emulator (daca nu exista APK)
npx react-native run-android --mode=release

# Porneste aplicatia manual (daca nu se deschide automat)
~/Library/Android/sdk/platform-tools/adb shell am start -n com.qrchat/.MainActivity
```

### Pas 3 — Testare manuala pe emulator

Verifica urmatoarele scenarii, bifand fiecare:

#### 3.1 — Pornire si navigare
- [ ] Aplicatia porneste fara crash
- [ ] Splash screen apare (daca exista)
- [ ] Ecranul principal (chat list) se incarca
- [ ] Navigare intre tab-uri functioneaza (Chats, Settings, etc.)
- [ ] Back button Android functioneaza corect (nu inchide app-ul din ecranul principal)

#### 3.2 — Setari si teme
- [ ] Settings screen se deschide
- [ ] Schimbare tema Light/Dark functioneaza
- [ ] Tema Dark: culori teal (#00A884), fundal inchis
- [ ] Tema Light: culori orange, fundal deschis
- [ ] Schimbare limba (en/ro/ru/fr) — textele se actualizeaza

#### 3.3 — QR Code
- [ ] Ecranul QR code se deschide
- [ ] QR code se genereaza si se afiseaza
- [ ] Camera scanner se deschide (poate cere permisiuni pe emulator)

#### 3.4 — Chat
- [ ] Deschide o conversatie (daca exista contacte)
- [ ] Input field functioneaza — se poate tasta text
- [ ] Keyboard-ul Android apare/dispare corect
- [ ] Scroll in conversatie functioneaza

#### 3.5 — Accessibility
- [ ] Toate butoanele au labels vizibile
- [ ] Font size se adapteaza la system settings
- [ ] Contrast suficient in ambele teme

### Pas 4 — Capturi de ecran

```bash
# Screenshot ecran principal
~/Library/Android/sdk/platform-tools/adb exec-out screencap -p > /Users/ruslanconstantinovici/qrchatAndroid/screenshots/android-main.png

# Screenshot settings
~/Library/Android/sdk/platform-tools/adb exec-out screencap -p > /Users/ruslanconstantinovici/qrchatAndroid/screenshots/android-settings.png

# Screenshot dark theme
~/Library/Android/sdk/platform-tools/adb exec-out screencap -p > /Users/ruslanconstantinovici/qrchatAndroid/screenshots/android-dark.png
```

Creaza directorul `screenshots/` daca nu exista:
```bash
mkdir -p /Users/ruslanconstantinovici/qrchatAndroid/screenshots
```

### Pas 5 — Verifica loguri pentru erori

```bash
# Loguri React Native (filtrate)
~/Library/Android/sdk/platform-tools/adb logcat -s ReactNativeJS:V ReactNative:V

# Sau toate erorile
~/Library/Android/sdk/platform-tools/adb logcat *:E | head -100

# Crash logs
~/Library/Android/sdk/platform-tools/adb logcat -b crash
```

Cauta in loguri:
- `FATAL EXCEPTION` — crash nativ
- `RED BOX` sau `Yellow Box` — erori/warnings React Native
- `Error:` sau `Exception` — erori generale
- `OOM` — out of memory

### Pas 6 — Ruleaza teste Jest

```bash
cd /Users/ruslanconstantinovici/qrchatAndroid

# Ruleaza toate testele
npx jest --verbose

# Daca esueaza, ruleaza individual:
npx jest __tests__/App.test.tsx --verbose
npx jest __tests__/push-server.test.js --verbose
npx jest __tests__/PushTokenService.test.ts --verbose
```

**Rezultat asteptat:** Toate 9+ testele PASS.

Daca testele esueaza:
- Verifica `jest.setup.js` — mock-urile sunt complete?
- Erori de import? Verifica `transformIgnorePatterns` in `jest.config.js`
- Erori TypeScript? Ruleaza `npx tsc --noEmit` separat

### Pas 7 — Verifica TypeScript

```bash
cd /Users/ruslanconstantinovici/qrchatAndroid

# Verifica tipuri TypeScript (fara a genera fisiere)
npx tsc --noEmit

# Daca nu exista tsconfig.json, verifica:
ls tsconfig.json
```

**Rezultat asteptat:** 0 erori TypeScript. Daca sunt erori, noteaza-le in raportul de testare.

### Pas 8 — Verifica npm audit

```bash
cd /Users/ruslanconstantinovici/qrchatAndroid

# Verifica vulnerabilitati
npm audit

# Rezumat rapid
npm audit --omit=dev
```

Noteaza orice vulnerabilitate `high` sau `critical`.

---

## Fisiere de verificat/creat

| Fisier | Actiune |
|--------|---------|
| `__tests__/App.test.tsx` | Ruleaza, verifica PASS |
| `__tests__/push-server.test.js` | Ruleaza, verifica PASS |
| `__tests__/PushTokenService.test.ts` | Ruleaza, verifica PASS |
| `jest.config.js` | Citeste, verifica configuratia |
| `jest.setup.js` | Citeste, verifica mock-urile |
| `screenshots/` | Creaza directorul, salveaza capturi |
| `agent-runtime/outputs/final-qa-report.md` | Scrie raportul final |

---

## Criterii de succes

1. Emulatorul porneste si app-ul se instaleaza fara erori
2. App-ul porneste, nu are crash-uri la navigare basic
3. Tema Light si Dark functioneaza
4. Schimbarea limbii functioneaza
5. Toate testele Jest trec (9+ PASS)
6. `npx tsc --noEmit` — 0 erori (sau numar documentat)
7. Capturi de ecran salvate in `screenshots/`
8. Raport scris in `agent-runtime/outputs/final-qa-report.md`

---

## Capcane de evitat

- **NU instala pe dispozitiv fizic Android** — deocamdata testam doar pe emulator
- **NU modifica codul sursa** — rolul tau e doar de testare; daca gasesti bug-uri, documenteaza-le in raport
- **Emulatorul pe Apple Silicon:** Foloseste ARM system images, NU x86_64. Daca emulatorul nu porneste, verifica ca AVD-ul are system image `arm64-v8a`
- **ADB not found:** PATH-ul poate sa nu includa Android SDK. Foloseste calea completa: `~/Library/Android/sdk/platform-tools/adb`
- **Metro bundler:** Daca folosesti `run-android`, Metro trebuie sa ruleze. Daca da eroare "Could not connect to development server", porneste Metro manual: `npx react-native start`
- **Emulator GPU:** Pe Apple Silicon, `-gpu host` e recomandat. Daca da erori grafice, incearca `-gpu swiftshader_indirect`
- **Jest timeout:** Daca testele dau timeout, creste cu `--testTimeout=30000`
