# PROMPT 6 — Testare pe multiple simulatoare + Screenshots (qa-engineer)

**Agent:** qa-engineer
**Proiect:** `/Users/ruslanconstantinovici/QRChat`
**Prioritate:** CRITICA — trebuie verificat ca app-ul nu craseaza pe niciun device

---

## Context

QRChat v3.0.6 se pregateste pentru App Store submission. Trebuie testat pe cel putin 2 simulatoare cu dimensiuni de ecran diferite si trebuie facute screenshots in limba engleza pentru App Store Connect.

### Simulatoare disponibile (iOS 26.3):
| Device | UDID | Ecran | Status |
|--------|------|-------|--------|
| iPhone 16e | CFBAFE20-79FB-44EB-9011-CD7671CBE9BA | 4.7" — cel mai mic | Shutdown |
| iPhone Air | F7672D2E-95DF-4ABA-BA9A-BF3555461B29 | 6.3" — ecran mare | Shutdown |

---

## Sarcina 1 — Boot si testeaza pe iPhone 16e (cel mai mic ecran)

### Pas 1: Boot simulator
```bash
xcrun simctl boot CFBAFE20-79FB-44EB-9011-CD7671CBE9BA
```

### Pas 2: Seteaza limba pe English (EN) inainte de a lansa app-ul

Metoda: modifica .GlobalPreferences.plist al simulatorului.

```bash
# Gaseste path-ul plist
PLIST_PATH=~/Library/Developer/CoreSimulator/Devices/CFBAFE20-79FB-44EB-9011-CD7671CBE9BA/data/Library/Preferences/.GlobalPreferences.plist

# Seteaza limba pe English
plutil -replace AppleLanguages -json '["en"]' "$PLIST_PATH"
plutil -replace AppleLocale -string "en_US" "$PLIST_PATH"

# Reboot simulator pentru a aplica schimbarile
xcrun simctl shutdown CFBAFE20-79FB-44EB-9011-CD7671CBE9BA
xcrun simctl boot CFBAFE20-79FB-44EB-9011-CD7671CBE9BA
```

**Verificare:** Dupa boot, deschide Settings.app in simulator si confirma ca limba este English.

### Pas 3: Build si instaleaza app-ul pe simulator
```bash
cd /Users/ruslanconstantinovici/QRChat
npx react-native run-ios --simulator="iPhone 16e"
```

### Pas 4: Testeaza fluxurile critice

Parcurge aceste fluxuri si noteaza orice crash, eroare vizuala sau comportament neasteptat:

1. **Welcome Screen** — Se afiseaza corect? Text-ul incape pe ecran?
2. **Setup Screen** — Introducere nume, generare chei. Tastatura nu acopera input-ul?
3. **Home Screen (Conversations)** — Lista goala arata mesajul "no conversations"?
4. **QR Generate** — QR code-ul se genereaza si se afiseaza complet pe ecranul mic?
5. **QR Scan** — Camera permission dialog apare? (nu poti testa camera in simulator, dar dialogul trebuie sa apara)
6. **Settings** — Toate sectiunile vizibile? Scroll functioneaza pana jos?
7. **Theme Selector** — Toate temele se afiseaza in grid? Nu sunt taiate?
8. **Upgrade Screen** — Text-ul incape? Butonul de promo code e accesibil?

**Atentie la ecranul mic:** iPhone 16e are cel mai mic ecran din lineup-ul actual. Probleme frecvente:
- Text trunchiat sau suprapus
- Butoane prea mici pentru touch target (minim 44x44pt)
- Tastatura acopera input fields
- Scroll nu ajunge pana la ultimul element

### Pas 5: Fa screenshots pentru App Store (iPhone 16e NU e necesar pentru Store, dar e util ca dovada de testare)
```bash
# Creeaza directorul pentru screenshots
mkdir -p /Users/ruslanconstantinovici/QRChat/screenshots/iphone-16e

# Screenshot dupa fiecare ecran testat
xcrun simctl io CFBAFE20-79FB-44EB-9011-CD7671CBE9BA screenshot /Users/ruslanconstantinovici/QRChat/screenshots/iphone-16e/01-welcome.png
xcrun simctl io CFBAFE20-79FB-44EB-9011-CD7671CBE9BA screenshot /Users/ruslanconstantinovici/QRChat/screenshots/iphone-16e/02-setup.png
xcrun simctl io CFBAFE20-79FB-44EB-9011-CD7671CBE9BA screenshot /Users/ruslanconstantinovici/QRChat/screenshots/iphone-16e/03-home.png
# ... etc pentru fiecare ecran
```

---

## Sarcina 2 — Boot si testeaza pe iPhone Air (ecran mare)

### Pas 1: Boot simulator
```bash
xcrun simctl boot F7672D2E-95DF-4ABA-BA9A-BF3555461B29
```

### Pas 2: Seteaza limba pe English
```bash
PLIST_PATH=~/Library/Developer/CoreSimulator/Devices/F7672D2E-95DF-4ABA-BA9A-BF3555461B29/data/Library/Preferences/.GlobalPreferences.plist

plutil -replace AppleLanguages -json '["en"]' "$PLIST_PATH"
plutil -replace AppleLocale -string "en_US" "$PLIST_PATH"

xcrun simctl shutdown F7672D2E-95DF-4ABA-BA9A-BF3555461B29
xcrun simctl boot F7672D2E-95DF-4ABA-BA9A-BF3555461B29
```

### Pas 3: Build si instaleaza
```bash
cd /Users/ruslanconstantinovici/QRChat
npx react-native run-ios --simulator="iPhone Air"
```

### Pas 4: Testeaza aceleasi fluxuri ca la iPhone 16e
(vezi lista de la Sarcina 1, Pas 4)

**Atentie la ecranul mare:** iPhone Air are Dynamic Island si ecran mai inalt. Probleme frecvente:
- Safe area insets nu sunt respectate (continut sub Dynamic Island)
- Prea mult spatiu gol pe ecranele simple
- Font size prea mic relativ la ecran

### Pas 5: Screenshots OFICIALE pentru App Store (iPhone Air — 6.7" class)

Acestea sunt screenshots-urile care vor fi uploadate in App Store Connect. Trebuie sa fie:
- In limba **ENGLEZA**
- Curate (fara debug overlay, fara yellow box warnings)
- Representative pentru app

```bash
mkdir -p /Users/ruslanconstantinovici/QRChat/screenshots/iphone-air

# Screenshots in ordinea in care apar in App Store:
xcrun simctl io F7672D2E-95DF-4ABA-BA9A-BF3555461B29 screenshot /Users/ruslanconstantinovici/QRChat/screenshots/iphone-air/01-welcome.png
xcrun simctl io F7672D2E-95DF-4ABA-BA9A-BF3555461B29 screenshot /Users/ruslanconstantinovici/QRChat/screenshots/iphone-air/02-chat.png
xcrun simctl io F7672D2E-95DF-4ABA-BA9A-BF3555461B29 screenshot /Users/ruslanconstantinovici/QRChat/screenshots/iphone-air/03-qr-code.png
xcrun simctl io F7672D2E-95DF-4ABA-BA9A-BF3555461B29 screenshot /Users/ruslanconstantinovici/QRChat/screenshots/iphone-air/04-settings.png
xcrun simctl io F7672D2E-95DF-4ABA-BA9A-BF3555461B29 screenshot /Users/ruslanconstantinovici/QRChat/screenshots/iphone-air/05-themes.png
```

**App Store Connect necesita minim 3 screenshots, maxim 10.** Recomandare: 5-6 screenshots care arata:
1. Welcome / prima impresie
2. O conversatie (cu mesaje demo daca e posibil)
3. QR code generation (USP-ul app-ului)
4. Settings cu teme
5. Ecranul de securitate / encryption info

---

## Sarcina 3 — Verifica ca app-ul nu craseaza pe niciunul

Dupa testare, raporteaza:

### Checklist de crash:
- [ ] iPhone 16e — app porneste fara crash
- [ ] iPhone 16e — navigare intre toate ecranele fara crash
- [ ] iPhone 16e — rotate (daca e permis) nu cauzeaza crash
- [ ] iPhone Air — app porneste fara crash
- [ ] iPhone Air — navigare intre toate ecranele fara crash
- [ ] iPhone Air — rotate (daca e permis) nu cauzeaza crash

### Daca app-ul craseaza:
1. Verifica logurile: `xcrun simctl spawn booted log stream --level=error --predicate 'process == "QRChat"'`
2. Noteaza ecranul exact si actiunea care a cauzat crash-ul
3. Scrie un mesaj catre agentul responsabil (frontend-engineer sau architect) in `agent-runtime/messages/`

---

## Sarcina 4 — (Bonus) Testeaza si in alte limbi

App-ul suporta 4 limbi: en, ro, ru, fr (din CFBundleLocalizations in Info.plist).

Daca ai timp, schimba limba simulatorului pe romana:
```bash
plutil -replace AppleLanguages -json '["ro"]' "$PLIST_PATH"
plutil -replace AppleLocale -string "ro_RO" "$PLIST_PATH"
xcrun simctl shutdown <UDID> && xcrun simctl boot <UDID>
```

Verifica ca:
- Textele sunt traduse (nu apar chei de traducere ca "settings.title")
- Textele lungi in romana nu sunt taiate
- Butoanele inca au spatiu pentru text mai lung

---

## Dupa finalizare

1. Scrie raportul de testare in `agent-runtime/outputs/simulator-test-report.md`
2. Lista de screenshots salvate cu path-urile
3. Lista de bug-uri gasite (daca exista)
4. Actualizeaza `agent-runtime/state/status.md`
