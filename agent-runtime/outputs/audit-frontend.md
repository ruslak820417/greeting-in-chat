# Audit Frontend — QRChat UI/UX v3.0.6
Data: 2026-03-21

## Scor General: 84/100

---

## Ecrane: 20/20 existente | 18 in navigator + 2 embedded

| # | Ecran | Tema | i18n | A11y | Design | Status |
|---|-------|------|------|------|--------|--------|
| 1 | WelcomeScreen | OK | OK | Low (2) | OK | OK |
| 2 | SetupScreen | OK | OK | Good (13) | OK | OK |
| 3 | HomeScreen | OK | OK | Good (27) | OK | OK |
| 4 | ChatScreen | OK | OK | Excelent (51) | OK | OK |
| 5 | CallScreen | OK | OK | Good (8) | OK | OK |
| 6 | QRGenerateScreen | OK | OK | Mod (6) | OK | OK |
| 7 | QRScanScreen | OK | OK | Low (2) | OK | OK |
| 8 | ProfileScreen | OK | OK | Good (15) | OK | OK |
| 9 | ContactsScreen | OK | OK | Good (10) | OK | OK |
| 10 | SettingsScreen | OK | OK | Excelent (30) | OK | Partial |
| 11 | CreateGroupScreen | OK | OK | Mod (7) | OK | OK |
| 12 | GroupInfoScreen | OK | OK | Low (3) | OK | OK |
| 13 | ContactProfileScreen | OK | OK | Good (15) | OK | OK |
| 14 | PendingApprovalScreen | OK | OK | Mod (6) | OK | OK |
| 15 | UpgradeScreen | OK | OK | Good (9) | OK | OK |
| 16 | ThemeEditorScreen | OK | OK | Mod (6) | OK | OK |
| 17 | TermsScreen | OK | OK | ZERO (0) | OK | Needs fix |
| 18 | SupportScreen | OK | OK | Low (3) | OK | OK |
| 19 | CallLogScreen | OK | OK | Good (10) | OK | Embedded |
| 20 | PhoneContactsScreen | OK | OK | ZERO (0) | OK | Embedded |

**Note:** CallLogScreen si PhoneContactsScreen NU sunt inregistrate in AppNavigator — sunt embedded ca tab-uri in HomeScreen. Aceasta e o decizie intentionala de design.

---

## Teme: OK

- **2 teme definite:** `default` (Light Orange) si `dark` (Dark Teal) — corect
- **Teme vechi eliminate:** `cipher`, `vault`, `ghost` — migrate automat la `dark` (ThemeContext.tsx:148-151)
- **Toate proprietatile ThemeColors** definite in ambele teme (26 proprietati + 1 optional `danger`)
- **statusBarStyle:** `dark-content` (Light) / `light-content` (Dark) — corect
- **messageSent Light:** `#D4915A` (portocaliu spalacit) — corect
- **messageSent Dark:** `#005C4B` (teal WhatsApp) — corect
- **Custom overrides:** Suportate prin ThemeEditor (persist in AsyncStorage)
- **Toate 20 ecranele** importa si folosesc `useTheme()` — 100% coverage

### Culori hardcodate notabile (minore)

| Fisier | Linia | Culoare | Ar trebui sa fie |
|--------|-------|---------|-----------------|
| HomeScreen.tsx | 273 | `#007AFF` | `C.primary` sau `C.accent` |
| HomeScreen.tsx | 283 | `#8E8E93` | `C.textMuted` |
| HomeScreen.tsx | 575, 579, 583 | `#FF6B00`, `#A0706F` | `C.primary` / tema |
| ContactsScreen.tsx | 116 | `#FF6B00` | `C.primary` |
| PhoneContactsScreen.tsx | 149, 152 | `#FF6B00` | `C.primary` |
| ChatScreen.tsx | 2150 | `#FF6B00` | `C.primary` |
| CallScreen.tsx | 247, 250 | `#0A0F1E` | `C.background` (dark-only) |

**Severitate:** Low — toate ecranele functioneaza corect cu ambele teme, dar aceste culori nu se vor adapta la theme overrides.

---

## i18n: 427 chei per limba — COMPLET

| Limba | Chei | Status |
|-------|------|--------|
| en (English) | 427 | Complet |
| ro (Romanian) | 427 | Complet |
| ru (Russian) | 427 | Complet |
| fr (French) | 427 | Complet |

- **Fallback language:** `ro` — corect
- **Device language detection:** iOS (AppleLocale/AppleLanguages) + Android (I18nManager) — corect
- **changeLanguage()** persista in AsyncStorage cu cheia `qrchat_language` — corect
- **Supported languages:** `['ro', 'en', 'ru', 'fr']` — corect

### Problema i18n

- **"QRCHAT UNLIMITED"** in SettingsScreen (linia ~370) — hardcodat in engleza, nu foloseste `t()`

---

## Accessibility: 18/20 ecrane cu atribute | 2 cu zero

### Coverage per ecran

| Nivel | Ecrane | Atribute |
|-------|--------|----------|
| Excelent (20+) | ChatScreen (51), SettingsScreen (30), HomeScreen (27) | 108 |
| Good (10-19) | ContactProfileScreen (15), ProfileScreen (15), SetupScreen (13), CallLogScreen (10), ContactsScreen (10) | 63 |
| Moderate (6-9) | UpgradeScreen (9), CallScreen (8), CreateGroupScreen (7), QRGenerateScreen (6), PendingApprovalScreen (6), ThemeEditorScreen (6) | 42 |
| Low (2-5) | SupportScreen (3), GroupInfoScreen (3), QRScanScreen (2), WelcomeScreen (2) | 10 |
| **ZERO** | **PhoneContactsScreen (0), TermsScreen (0)** | **0** |

**Total atribute:** ~223 in ecrane

### Ecrane cu zero accessibility (CRITIC)

1. **PhoneContactsScreen.tsx** — search input, invite button, permission request — toate fara labels
2. **TermsScreen.tsx** — back button fara label, continut legal fara structura semantica

### Best practices observate

- ChatScreen, HomeScreen, SettingsScreen: butoane cu `accessibilityLabel` + `accessibilityRole="button"`
- SetupScreen: radio buttons cu `accessibilityRole="radio"` + `accessibilityState={{ selected }}`
- SettingsScreen: switch-uri cu stare checked corecta

### Componente shared — accessibility lipsa

- ErrorBoundary, Logo, LogoNew, NotificationBanner, SplashScreen, StyledName — zero atribute accessibility
- IncomingCallOverlay: 4 atribute (Accept/Decline cu labels)
- ThemedActionSheet: 0 atribute proprii (butoanele primesc labels de la caller)

---

## Componente: 7/8 folosite | 1 dead code

| Componenta | Folosita | Unde |
|-----------|----------|------|
| ErrorBoundary | Da | App.tsx (wrap AppNavigator) |
| IncomingCallOverlay | Da | App.tsx (overlay conditionat) |
| Logo | Da | WelcomeScreen, ChatScreen, SettingsScreen, HomeScreen, SplashScreen |
| LogoNew | **NU** | **Dead code — nefolosit nicaieri** |
| NotificationBanner | Da | App.tsx (overlay) |
| SplashScreen | Da | App.tsx (initial load) |
| StyledName | Da | HomeScreen, CallLogScreen, PhoneContactsScreen |
| ThemedActionSheet | Da | ChatScreen, ContactsScreen, GroupInfoScreen, HomeScreen |

**Problema:** `LogoNew.tsx` (379 linii) este dead code. Logo.tsx (12 linii) este componenta activa.

---

## Design Audit — Ecrane Cheie

### ChatScreen (3133 linii) — 10/10

| # | Verificare | Status | Detalii |
|---|-----------|--------|---------|
| 1 | Message bubbles borderRadius 12 | OK | `borderRadius: 12`, tail: `borderTopRightRadius: 4` (sent), `borderTopLeftRadius: 4` (received) |
| 2 | Bubble spacing 1/10px | OK | `spacingTop = 1` (same sender), `spacingTop = 10` (different) |
| 3 | Date separators pill | OK | `borderRadius: 8`, `paddingHorizontal: 12`, semi-transparent bg |
| 4 | Typing dots 6px | OK | `width: 6, height: 6, borderRadius: 3`, bounce -6px, 250ms |
| 5 | Scroll-to-bottom 40px | OK | `width: 40, height: 40, borderRadius: 20`, badge `minWidth: 20` |
| 6 | Input bar pill | OK | `borderRadius: 24`, attach + send `38x38`, emoji/camera/mic |
| 7 | Swipe-to-reply Swipeable | OK | `react-native-gesture-handler` Swipeable, `leftThreshold: 40` |
| 8 | Album grid 2/3/4+N | OK | 2: row, 3: 2+1, 4+: 2x2 cu "+N" badge, `gap: 2` |
| 9 | Phone number detection | OK | Regex `/(\+?\d[\d\s\-]{6,}\d)/g`, `Linking.openURL(tel:)` |
| 10 | Long press menu | OK | Reply, Forward, Copy, Edit, Delete All, Delete Me, Select, Report + Emoji reactions |

### HomeScreen (1114 linii) — 3/5

| # | Verificare | Status | Detalii |
|---|-----------|--------|---------|
| 1 | Swipe circles | OK | `44x44, borderRadius: 22`, pin/archive/block cu icons, fara text |
| 2 | Multi-select toolbar 16px | **LIPSA** | Nu exista toolbar multi-select; doar long-press ActionSheet |
| 3 | Typing indicator in lista | **LIPSA** | Typing dots exista doar in ChatScreen, nu in conversation list |
| 4 | Unread badge | OK | `borderRadius: 12, minWidth: 24, height: 24`, C.primary bg |
| 5 | Avatar random color | OK | 8 culori, `56x56, borderRadius: 14`, fallback C.primary |

### CallScreen (521 linii) — 5/5

| # | Verificare | Status | Detalii |
|---|-----------|--------|---------|
| 1 | Gradient + glow | OK | `#0A0F1E` base, primary overlay 0.06, radial glow 300x300 |
| 2 | Avatar 130px + pulse | OK | `130x130, borderRadius: 65`, ring `170x170`, scale 1→1.4, 1200ms |
| 3 | Glassmorphism buttons | OK | `64x64`, `rgba(255,255,255,0.12)`, border `rgba(255,255,255,0.15)` |
| 4 | Hangup 72px red | OK | `72x72, borderRadius: 36`, TC.error, shadow glow radius 16 |
| 5 | Timer 36px mono | OK | `fontSize: 36`, `fontVariant: ['tabular-nums']`, letterSpacing 2 |

### IncomingCallOverlay — consistent cu CallScreen

### SetupScreen — OK

- Language pills (EN/RO/RU/FR): functionale, apply instant
- Theme cards (Light/Dark): functionale, apply instant
- Logo: nu e pe setup (foloseste person-outline icon)

### SettingsScreen — Partial (3 lipsuri)

| Verificare | Status |
|-----------|--------|
| Limba selectabila | OK — dropdown cu radio buttons |
| Tema selectabila | OK — grid 2 coloane cu preview |
| Privacy Policy link | OK — `Linking.openURL('https://qrchat.app/privacy')` |
| Terms of Service link | **LIPSA** — nu exista link in Settings |
| Support link | **LIPSA** — disponibil doar din ProfileScreen |
| Account deletion | OK — confirmare dialog + clear all |
| Export data | **LIPSA** — cheie i18n exista dar functia nu e implementata |
| Optiuni traduse | OK — toate folosesc `t()` (exceptie: "QRCHAT UNLIMITED") |

---

## Inconsistente Vizuale

| # | Ecran | Problema | Severitate |
|---|-------|---------|------------|
| 1 | HomeScreen | Multi-select toolbar lipseste (doar ActionSheet) | Medium |
| 2 | HomeScreen | Typing indicator lipsa in conversation list | Medium |
| 3 | SettingsScreen | Terms of Service link lipsa | High |
| 4 | SettingsScreen | Support link lipsa (doar in ProfileScreen) | Medium |
| 5 | SettingsScreen | Export data neimplementat | High |
| 6 | SettingsScreen | "QRCHAT UNLIMITED" hardcodat in engleza | Low |
| 7 | SetupScreen | Logo lipsa pe ecranul de setup (doar icon) | Low |
| 8 | Componente | LogoNew.tsx — 379 linii dead code | Low |
| 9 | 12 locuri | Culori hardcodate (#FF6B00, #007AFF, etc.) | Low |
| 10 | PhoneContactsScreen | Zero accessibility attributes | High |
| 11 | TermsScreen | Zero accessibility attributes | High |
| 12 | 7 componente | Componente shared fara accessibility labels | Medium |

---

## Recomandari

### Prioritate CRITICA
1. **Adauga accessibility** pe PhoneContactsScreen si TermsScreen (0 atribute)
2. **Implementeaza Export Data** in SettingsScreen (cheia i18n exista, functia nu)
3. **Adauga Terms of Service link** in SettingsScreen (ecranul TermsScreen exista deja)

### Prioritate MEDIE
4. **Adauga Support link** in SettingsScreen (ecranul SupportScreen exista deja)
5. **Typing indicator in conversation list** — arata "typing..." sub ultimul mesaj in HomeScreen
6. **Multi-select toolbar** in HomeScreen cu colturi rotunjite 16px
7. **Adauga accessibility** pe componentele shared (Logo, NotificationBanner, SplashScreen, StyledName)

### Prioritate LOW
8. **Sterge LogoNew.tsx** — dead code, 379 linii nefolosite
9. **Inlocuieste culori hardcodate** cu referinte la tema (12 locuri identificate)
10. **Traduce "QRCHAT UNLIMITED"** — adauga cheie i18n
11. **Adauga Logo pe SetupScreen** — in loc de person-outline icon

---

## Scor Detaliat

| Categorie | Scor | Max | Detalii |
|-----------|------|-----|---------|
| Ecrane completitudine | 20 | 20 | Toate 20 exista si sunt accesibile |
| Tema system | 15 | 15 | 2 teme, migrare vechi, override-uri custom |
| i18n completitudine | 14 | 15 | 427/427 chei x 4 limbi; -1 hardcoded string |
| Accessibility | 10 | 15 | 18/20 ecrane, 2 cu zero, componente lipsa |
| Design consistency | 13 | 15 | ChatScreen si CallScreen excelente; HomeScreen -2 features |
| Componente | 7 | 10 | 7/8 folosite, 1 dead code, accessibility lipsa |
| SettingsScreen | 5 | 10 | 3 functii lipsa (Terms, Support, Export) |
| **TOTAL** | **84** | **100** | |
