# Prompt: Frontend Audit Complet — frontend-engineer

**Rol:** Esti frontend-engineer pentru QRChat, un messenger criptat end-to-end React Native.
**Proiect:** `/Users/ruslanconstantinovici/QRChat`
**Tech:** React Native 0.84, TypeScript 5.8, react-navigation v7, react-native-gesture-handler, i18next

---

## SARCINA

Executa un audit complet al UI/UX al aplicatiei QRChat. Verifica toate ecranele, temele, i18n, accessibility, design consistency. Scrie un raport cu starea vizuala completa.

---

## VERIFICARI (executa pe rand)

### 1. Inventar Ecrane — Completitudine

Citeste: `src/navigation/AppNavigator.tsx`

Lista tuturor ecranelor inregistrate in navigator:

| # | Ecran | Fisier | Linii | Scop |
|---|-------|--------|-------|------|
| 1 | WelcomeScreen | `src/screens/WelcomeScreen.tsx` | 209 | Prima deschidere |
| 2 | SetupScreen | `src/screens/SetupScreen.tsx` | 372 | Setup profil + limba + tema |
| 3 | HomeScreen | `src/screens/HomeScreen.tsx` | 1114 | Lista conversatii |
| 4 | ChatScreen | `src/screens/ChatScreen.tsx` | 3133 | Chat UI principal |
| 5 | CallScreen | `src/screens/CallScreen.tsx` | 521 | Apel voce/video |
| 6 | QRGenerateScreen | `src/screens/QRGenerateScreen.tsx` | 320 | Genereaza QR |
| 7 | QRScanScreen | `src/screens/QRScanScreen.tsx` | 387 | Scaneaza QR |
| 8 | ProfileScreen | `src/screens/ProfileScreen.tsx` | 395 | Profil propriu |
| 9 | ContactsScreen | `src/screens/ContactsScreen.tsx` | 284 | Lista contacte |
| 10 | SettingsScreen | `src/screens/SettingsScreen.tsx` | 794 | Setari |
| 11 | CreateGroupScreen | `src/screens/CreateGroupScreen.tsx` | 188 | Creare grup |
| 12 | GroupInfoScreen | `src/screens/GroupInfoScreen.tsx` | 218 | Info grup |
| 13 | ContactProfileScreen | `src/screens/ContactProfileScreen.tsx` | 815 | Profil contact |
| 14 | PendingApprovalScreen | `src/screens/PendingApprovalScreen.tsx` | 398 | Aprobare contact |
| 15 | UpgradeScreen | `src/screens/UpgradeScreen.tsx` | 308 | Upgrade premium |
| 16 | ThemeEditorScreen | `src/screens/ThemeEditorScreen.tsx` | 315 | Editor teme |
| 17 | TermsScreen | `src/screens/TermsScreen.tsx` | 112 | Termeni de utilizare |
| 18 | SupportScreen | `src/screens/SupportScreen.tsx` | 155 | Suport/FAQ |
| 19 | CallLogScreen | `src/screens/CallLogScreen.tsx` | 366 | Jurnal apeluri |
| 20 | PhoneContactsScreen | `src/screens/PhoneContactsScreen.tsx` | 280 | Contacte telefon |

Verifica:
- [ ] Toate 20 ecranele sunt importate in AppNavigator
- [ ] Fiecare ecran are parametri corecti in `RootStackParamList`
- [ ] Nu exista ecrane orfane (importate dar nefolosite)
- [ ] CallLogScreen si PhoneContactsScreen — sunt accesibile din navigator? Sau sunt tab-uri?

### 2. Componente Shared

Citeste fiecare componenta din `src/components/`:

| Componenta | Fisier | Linii | Folosita in |
|-----------|--------|-------|-------------|
| ErrorBoundary | `ErrorBoundary.tsx` | 93 | App.tsx (wrap) |
| IncomingCallOverlay | `IncomingCallOverlay.tsx` | 225 | App.tsx (overlay) |
| Logo | `Logo.tsx` | 12 | ? |
| LogoNew | `LogoNew.tsx` | 379 | ? |
| NotificationBanner | `NotificationBanner.tsx` | 128 | App.tsx |
| SplashScreen | `SplashScreen.tsx` | 125 | App.tsx |
| StyledName | `StyledName.tsx` | 30 | ? |
| ThemedActionSheet | `ThemedActionSheet.tsx` | 115 | ? |

Verifica:
- [ ] Fiecare componenta e folosita cel putin o data in codebase
- [ ] `Logo.tsx` vs `LogoNew.tsx` — se mai foloseste Logo vechi?
- [ ] ErrorBoundary acopera intreaga aplicatie (in App.tsx)

### 3. Teme — Light + Dark

Citeste: `src/utils/ThemeContext.tsx` (intreaga)

Verifica:
- [ ] Doar 2 teme definite: `default` (Light orange) si `dark` (Dark teal)
- [ ] Temele vechi (Cipher, Vault, Ghost) sunt complet eliminate
- [ ] Migrare automata: daca tema salvata e veche, se seteaza `dark`
- [ ] Toate proprietatile ThemeColors sunt definite in ambele teme
- [ ] `statusBarStyle` corect: `dark-content` (Light), `light-content` (Dark)
- [ ] `messageSent` Light: `#D4915A` (portocaliu spalacit)
- [ ] `messageSent` Dark: `#005C4B` (teal WhatsApp)

### 4. Toate ecranele folosesc tema

Cauta in codebase:
```bash
grep -rn "useTheme" /Users/ruslanconstantinovici/QRChat/src/screens/ | wc -l
```

Verifica:
- [ ] Toate 20 ecranele importa si folosesc `useTheme()`
- [ ] Nu exista culori hardcodate care nu vin din tema (exceptie: culori specifice gen rosu hangup)
- [ ] Header-ul navigatorului respecta tema

### 5. i18n — Completitudine 4 limbi

Citeste: `src/i18n/index.ts` si `src/i18n/locales/`

Verifica completitudinea:
```bash
# Compara numarul de chei intre limbi
python3 -c "
import json
for lang in ['en', 'ro', 'ru', 'fr']:
    with open(f'/Users/ruslanconstantinovici/QRChat/src/i18n/locales/{lang}.json') as f:
        data = json.load(f)
    # Count all leaf keys recursively
    def count_keys(d, prefix=''):
        n = 0
        for k, v in d.items():
            if isinstance(v, dict):
                n += count_keys(v, f'{prefix}{k}.')
            else:
                n += 1
        return n
    print(f'{lang}: {count_keys(data)} keys, {len(json.dumps(data))} bytes')
"
```

- [ ] Toate 4 limbile au acelasi numar de chei
- [ ] Daca exista diferente, listeaza cheile lipsa
- [ ] Fallback language: `ro` (limba default)
- [ ] Device language detection functioneaza (iOS: AppleLocale, Android: I18nManager)
- [ ] `changeLanguage()` persista in AsyncStorage

### 6. Accessibility Labels

Cauta in fiecare ecran:
```bash
grep -rn "accessibilityLabel\|accessibilityRole\|accessibilityState\|accessibilityHint" /Users/ruslanconstantinovici/QRChat/src/screens/ | wc -l
```

Verifica:
- [ ] Toate butoanele interactive au `accessibilityLabel`
- [ ] Switch-uri au `accessibilityState` cu `checked`
- [ ] Tabs au `accessibilityRole="tab"` sau similar
- [ ] Text inputs au label-uri descriptive
- [ ] Imagini decorative au `accessible={false}` sau `accessibilityElementsHidden`

### 7. Chat UI — Design Audit

Citeste: `src/screens/ChatScreen.tsx` (3133 linii — cel mai mare ecran)

Verifica:
- [ ] Message bubbles: borderRadius 12, tail sus
- [ ] Bubble spacing: 1px same sender, 10px different
- [ ] Date separators: pill capsule
- [ ] Typing indicator: bouncing dots 6px
- [ ] Scroll-to-bottom: cerc flotant 40px cu badge
- [ ] Input bar: pill shape, emoji + camera + send buttons
- [ ] Swipe-to-reply: Swipeable (gesture-handler) — nu PanResponder
- [ ] Album grouping: grid 2/3/4/+N
- [ ] Phone number auto-detection (linkuri clickabile)
- [ ] Long press menu: Reply, Forward, Copy, Delete, Report

### 8. Home Screen — Design Audit

Citeste: `src/screens/HomeScreen.tsx` (1114 linii)

Verifica:
- [ ] Swipe actions: Pin/Archive/Block (cercuri, fara text)
- [ ] Multi-select toolbar: colturi rotunjite 16px
- [ ] Typing indicator in lista (bubble cu dots)
- [ ] Unread badge pe conversatii
- [ ] Avatar cu culoare random

### 9. Call Screen — Design Audit

Citeste: `src/screens/CallScreen.tsx` si `src/components/IncomingCallOverlay.tsx`

Verifica:
- [ ] Fundal gradient cu glow radial
- [ ] Avatar 130px cu pulse ring animat
- [ ] Butoane glassmorphism (semi-transparente)
- [ ] Hangup 72px rosu cu shadow glow
- [ ] Timer 36px mono-spaced
- [ ] IncomingCallOverlay redesigned identic

### 10. Setup & Welcome — Design Audit

Citeste: `src/screens/SetupScreen.tsx` si `src/screens/WelcomeScreen.tsx`

Verifica:
- [ ] Selector limba (EN/RO/RU/FR pills) pe setup
- [ ] Selector tema (Light/Dark cards) pe setup
- [ ] Se aplica instant
- [ ] Logo afisat corect

### 11. Settings Screen

Citeste: `src/screens/SettingsScreen.tsx` (794 linii)

Verifica:
- [ ] Limba selectabila
- [ ] Tema selectabila
- [ ] Privacy Policy link
- [ ] Terms of Service link
- [ ] Support link
- [ ] Account deletion functional
- [ ] Export data functional
- [ ] Toate optiunile sunt traduse in 4 limbi

---

## FISIERE DE CITIT (lista completa)

| Director | Fisiere |
|----------|---------|
| `src/screens/` | Toate 20 fisierele |
| `src/components/` | Toate 8 fisierele |
| `src/utils/ThemeContext.tsx` | Definitii teme |
| `src/i18n/` | `index.ts` + 4 locale |
| `src/navigation/AppNavigator.tsx` | Stack navigator |
| `App.tsx` | Root component |

---

## COMANDA DE VERIFICARE

Ai terminat cand:
1. Ai verificat fiecare ecran individual
2. Ai un tabel cu starea i18n (chei per limba)
3. Ai un scor accessibility (X/20 ecrane cu labels)
4. Ai o lista de inconsistente vizuale

---

## UNDE SCRII RAPORTUL

Scrie rezultatul in:
```
/Users/ruslanconstantinovici/Projects/Agent Teams/agent-runtime/outputs/audit-frontend.md
```

Format:
```markdown
# Audit Frontend — QRChat UI/UX v4.0.0
Data: [data curenta]

## Scor General: XX/100

## Ecrane: 20/20 inregistrate
| # | Ecran | Tema | i18n | A11y | Design | Status |
|---|-------|------|------|------|--------|--------|

## Teme: [OK / PROBLEME]
[detalii]

## i18n: XX chei per limba
| Limba | Chei | Status |
|-------|------|--------|

## Accessibility: XX/20 ecrane
[detalii]

## Inconsistente Vizuale
| # | Ecran | Problema | Severitate |
|---|-------|---------|------------|

## Recomandari
1. ...
```
