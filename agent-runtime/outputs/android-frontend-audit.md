# Android Frontend Audit — QRChat

**Data:** 2026-03-23
**Auditor:** frontend-engineer (audit mode)
**Scope:** 20 ecrane + 7 componente — verificare Android compatibility

---

## REZUMAT EXECUTIV

| Categorie | Status | Probleme |
|-----------|--------|----------|
| Platform.OS checks | PARTIAL | 5 probleme |
| Teme / useTheme() | BUN | 3 probleme minore |
| i18n / t() | BUN | 2 probleme |
| Accessibility | BUN | Acoperire buna |
| Safe Area | BUN | Folosit corect |
| Navigare | OK | Toate ecranele inregistrate |
| FlatList | OK | key props prezente |
| Imagini/Logo | OK | logo_new.png corect |
| iOS-only APIs | PARTIAL | 3 probleme |
| Stiluri/Shadows | CRITIC | 15+ locuri fara elevation |
| StatusBar | BUN | statusBarStyle din tema |
| Keyboard | OK | Platform.OS check prezent |
| Permisiuni runtime | CRITIC | PermissionsAndroid nefolosit |
| Linking URLs | CRITIC | sms: separator gresit |
| MediaFilesScreen | OK | Functioneaza pe Android |

**Total probleme gasite: 28**
- CRITICE: 6
- MEDII: 12
- MINORE: 10

---

## 1. PLATFORM.OS CHECKS

### Ecrane care folosesc Platform.OS:
- **CallScreen.tsx:254** — `Platform.OS === 'android'` pentru AudioManagerModule (CORECT)
- **SetupScreen.tsx:104** — KeyboardAvoidingView behavior (CORECT)
- **QRGenerateScreen.tsx:110-114** — Share diferit iOS/Android (CORECT)
- **QRGenerateScreen.tsx:313-314** — fontFamily per platform (CORECT)
- **i18n/index.ts:25-31** — Device language detection (CORECT)

### PROBLEME:
- **QRScanScreen.tsx:238** — StatusBar `translucent` setat fara verificare Android — OK, functioneaza pe ambele
- **QRGenerateScreen.tsx:138** — Header paddingTop hardcodat la 60 — NU foloseste `useSafeAreaInsets()` (MEDIE)
- **CreateGroupScreen.tsx:149** — Header paddingTop hardcodat la 60 (MEDIE)
- **GroupInfoScreen.tsx:169** — Header paddingTop hardcodat la 60 (MEDIE)
- **UpgradeScreen.tsx:320** — Header paddingTop hardcodat la 60 (MEDIE)

> **Impact:** Pe Android cu notch sau camera hole-punch, header-ul poate fi ascuns sub status bar.

---

## 2. TEME — useTheme()

### Toate ecranele folosesc useTheme(): DA
Verificat: toate 20 ecranele + ThemedActionSheet, IncomingCallOverlay, StyledName, Logo, NotificationBanner, SplashScreen — toate folosesc `useTheme()` sau nu au nevoie (Logo nu depinde de tema).

### Culori hardcodate gasite:
| Fisier | Linie | Culoare | Context |
|--------|-------|---------|---------|
| ContactsScreen.tsx | 116 | `#FF6B00` | StyledName primele 2 litere — brand color, intentionat dar nu trece prin tema |
| HomeScreen.tsx | 575 | `#FF6B00` | Logo text "QR" — brand color |
| ChatScreen.tsx | 2151 | `#FF6B00` | StyledName header |
| PhoneContactsScreen.tsx | 154,159 | `#FF6B00` | Invite button — ar trebui sa fie `C.primary` |
| CallScreen.tsx | 278,281,418 | `#0A0F1E` | Background call screen — dark mode intentionat |
| ThemedActionSheet.tsx | 96 | `rgba(0,0,0,0.55)` | Overlay — OK, e overlay standard |

### PROBLEME:
- **PhoneContactsScreen.tsx:154,159** — `#FF6B00` hardcodat in loc de `C.primary` sau `C.accent` (MINORA)
- **ContactsScreen.tsx:116** — `#FF6B00` hardcodat pentru StyledName — daca utilizatorul schimba tema, culorile "QR" din numele contactului raman portocalii (MINORA)

---

## 3. i18n — HARDCODED STRINGS

### Toate ecranele folosesc useTranslation(): DA
Limbi suportate: **ro, en, ru, fr** (cu fallback la ro)

### Device language detection:
- iOS: `NativeModules.SettingsManager` (CORECT)
- Android: `NativeModules.I18nManager.localeIdentifier` (CORECT)

### Hardcoded strings ramase:
| Fisier | Linie | String | Severitate |
|--------|-------|--------|-----------|
| UpgradeScreen.tsx | 63,87,117 | `'OK'` in Alert buttons | MINORA — ar trebui `t('common.ok')` |
| SettingsScreen.tsx | 568 | `'(c) 2026 Ruslan Constantinovici...'` | MINORA — copyright, nu necesita traducere |
| SettingsScreen.tsx | 504 | `'QRChat v${APP_VERSION} ...'` | MINORA — technical string |
| SupportScreen.tsx | 101 | `'(c) 2026 Ruslan Constantinovici'` | MINORA — copyright |

---

## 4. ACCESSIBILITY

### Status general: BUN
Majoritatea butoanelor, switch-urilor, input-urilor au `accessibilityLabel` si `accessibilityRole`.

### Exemple bune:
- SettingsScreen — toate switch-urile au `accessibilityRole="switch"` + label
- CallScreen — butoanele Mute/Speaker au `accessibilityState={{ selected }}`
- SetupScreen — checkbox Terms are `accessibilityRole="checkbox"` + `accessibilityState={{ checked }}`
- CreateGroupScreen — contacts au `accessibilityRole="checkbox"` + `accessibilityState={{ checked }}`
- MediaFilesScreen — tabs au `accessibilityRole="tab"` + `accessibilityState={{ selected }}`
- CallLogScreen — filter tabs au `accessibilityRole="tab"` + `accessibilityState={{ selected }}`

### PROBLEME:
- **ContactsScreen.tsx:179** — Empty state icon `color="#999"` hardcodat (MINORA)
- **ContactProfileScreen.tsx:223-321** — Sound selector items (radio buttons) lipseste accessibilityLabel pe unele TouchableOpacity-uri din renderSoundSelector (MINORA)
- **ThemeEditorScreen.tsx:147-153** — Preset color dots lipsesc accessibilityLabel (MINORA — sunt 30 dots, dificil de labuit)

---

## 5. SAFE AREA — useSafeAreaInsets()

### Ecrane care folosesc useSafeAreaInsets():
- CallScreen, SettingsScreen, ContactsScreen, ProfileScreen, MediaFilesScreen, ContactProfileScreen, ThemeEditorScreen, TermsScreen, SupportScreen, HomeScreen (10 ecrane)

### Ecrane care NU folosesc useSafeAreaInsets():
| Ecran | Risc |
|-------|------|
| QRGenerateScreen | MEDIE — header paddingTop: 60 hardcodat |
| CreateGroupScreen | MEDIE — header paddingTop: 60 hardcodat |
| GroupInfoScreen | MEDIE — header paddingTop: 60 hardcodat |
| UpgradeScreen | MEDIE — header paddingTop: 60 hardcodat |
| WelcomeScreen | SCAZUT — ecran centered, nu are header |
| SetupScreen | SCAZUT — ecran centered, nu are header |
| PendingApprovalScreen | SCAZUT — ecran centered |
| CallLogScreen | SCAZUT — sub-component in HomeScreen tabs |
| PhoneContactsScreen | SCAZUT — sub-component in HomeScreen tabs |

> **Impact:** Pe Android cu cutout/notch, header-urile cu paddingTop hardcodat la 60 pot fi sub status bar.

---

## 6. NAVIGARE

### Ecranele in AppNavigator (19 rute):
Welcome, Setup, Home, Chat, Call, QRGenerate, QRScan, Profile, Contacts, Settings, CreateGroup, GroupInfo, ContactProfile, MediaFiles, PendingApproval, Upgrade, ThemeEditor, Terms, Support

### Ecrane neregistrate ca rute independente:
- **CallLogScreen** — folosit ca tab in HomeScreen (OK, nu e ruta separata)
- **PhoneContactsScreen** — folosit ca tab in HomeScreen (OK, nu e ruta separata)

### Back navigation: CORECT
- Toate ecranele au buton back cu `navigation.goBack()`
- Chat + PendingApproval au `gestureEnabled: false` (intentionat — previne iesire accidentala)

---

## 7. FLATLIST

### FlatList usage — toate au keyExtractor:
| Ecran | keyExtractor | numColumns | ListEmptyComponent |
|-------|-------------|-----------|-------------------|
| HomeScreen | `item.contact.id` | 1 | DA |
| ContactsScreen | `item.id` | 1 | DA |
| CreateGroupScreen | `item.id` | 1 | DA |
| GroupInfoScreen | `item.id` | 1 | NU |
| MediaFilesScreen (grid) | `item.id` | 3 | DA (external) |
| MediaFilesScreen (list) | `item.id` | 1 | DA (external) |
| CallLogScreen | `item.id` | 1 | DA |
| PhoneContactsScreen | `item.id` | 1 | DA |

### PROBLEME:
- **GroupInfoScreen.tsx:141-145** — FlatList fara `ListEmptyComponent` (MINORA)

---

## 8. IMAGINI/LOGO

- **Logo.tsx:11** — `require('../assets/logo_new.png')` — CORECT
- Nu exista referinte la logo vechi in cod

---

## 9. COMPONENTE iOS-ONLY

### CallKitService.ts:
- **Linia 32:** `if (Platform.OS !== 'ios') return;` — CORECT, nu se initializeaza pe Android
- **RNCallKeep** — incapsulat in try/catch cu optional chaining

### ActionSheetIOS:
- **NU se foloseste.** Proiectul foloseste `ThemedActionSheet` custom — CROSS-PLATFORM (EXCELENT)

### CameraRoll:
- **NU se foloseste.** MediaFilesScreen foloseste Database.getMediaByContact() — CORECT

---

## 10. STILURI — SHADOWS (CRITIC)

Android NU suporta `shadowColor/shadowOffset/shadowOpacity/shadowRadius`. Trebuie `elevation`.

### Locuri cu shadow FARA elevation:
| Fisier | Linii | Descriere |
|--------|-------|-----------|
| **CallScreen.tsx** | 447-451 | localVideo shadow — lipseste `elevation` |
| **CallScreen.tsx** | 482-484 | avatarGlow shadow — lipseste `elevation` |
| **QRGenerateScreen.tsx** | 293-295 | qrContainer shadow — are elevation: 10 (OK) |
| **WelcomeScreen.tsx** | 228-230 | startButton — are elevation: 8 (OK) |
| **SetupScreen.tsx** | 353-355 | button shadow — are elevation: 6 (OK) |
| **HomeScreen.tsx** | 997-999 | scanButton shadow — lipseste `elevation` |
| **HomeScreen.tsx** | 1025-1027 | fab shadow — lipseste `elevation` |
| **UpgradeScreen.tsx** | 342-345 | featuresCard — are elevation: 2 (OK) |
| **NotificationBanner.tsx** | 87-90 | banner shadow — lipseste `elevation` |
| **IncomingCallOverlay.tsx** | 220-222 | avatar glow — lipseste `elevation` |
| **IncomingCallOverlay.tsx** | 263-265 | decline button — lipseste `elevation` |
| **IncomingCallOverlay.tsx** | 274-276 | accept button — lipseste `elevation` |
| **ChatScreen.tsx** | 2992-2995 | attachment menu — lipseste `elevation` |
| **ChatScreen.tsx** | 3070-3073 | send button — lipseste `elevation` |

### PROBLEME CRITICE:
- **15+ locuri** unde shadow props sunt folosite FARA `elevation` — pe Android aceste elemente nu vor avea nicio umbra vizibila
- **CallScreen.tsx** — endBtnModern are `elevation: 8` (CORECT), dar localVideo si avatarGlow nu au

---

## 11. STATUSBAR

### Toate ecranele seteaza StatusBar: DA
- Majoritatea folosesc `barStyle={C.statusBarStyle}` — CORECT
- CallScreen: `barStyle="light-content"` hardcodat — CORECT (ecran dark)
- QRScanScreen: `barStyle="light-content"` hardcodat — CORECT (camera dark)
- WelcomeScreen: include `backgroundColor={C.background}` — CORECT pentru Android

### PROBLEMA:
- Majoritatea ecranelor NU seteaza `backgroundColor` pe StatusBar — pe Android, status bar-ul poate avea culoare gresita (MINORA)

---

## 12. KEYBOARD

### KeyboardAvoidingView usage:
- **SetupScreen.tsx:102-104** — `behavior={Platform.OS === 'ios' ? 'padding' : undefined}` — CORECT
- **ChatScreen.tsx** — KeyboardAvoidingView prezent

### NOTA:
- `behavior={undefined}` pe Android = nu aplica niciun ajustment. Android are `windowSoftInputMode` in AndroidManifest care gestioneaza keyboard-ul nativ. Aceasta e abordarea corecta.

---

## 13. PERMISIUNI RUNTIME (CRITIC)

### PermissionsAndroid import:
- **PhoneContactsScreen.tsx:12** — importat dar **NU folosit nicaieri in cod**

### Problema critica:
PhoneContactsScreen apeleaza `Contacts.getAll()` direct FARA `PermissionsAndroid.request()` pe Android.
- Pe iOS, `getAll()` solicita permisiunea automat
- Pe **Android**, trebuie explicit `PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.READ_CONTACTS)` INAINTE de `getAll()`

### Camera (QRScanScreen):
- Camera Kit gestioneaza permisiunile intern — OK
- Dar nu exista fallback UI daca permisiunea e refuzata pe Android

### Microfon (CallScreen):
- `mediaDevices.getUserMedia()` solicita automat — dar fara `PermissionsAndroid.request()` explicit, Android poate refuza silent

### Storage:
- Nu e necesar pentru versiunile moderne Android (scoped storage)

---

## 14. LINKING URLs (CRITIC)

### SMS:
- **PhoneContactsScreen.tsx:118** — `sms:${contact.phone}&body=${message}`
  - iOS: `sms:number&body=text` — CORECT
  - **Android: trebuie `sms:number?body=text`** (cu `?` nu `&`)
  - **LIPSESTE Platform.OS check** — SMS-ul NU va deschide body-ul pre-completat pe Android

### mailto:
- ContactProfileScreen.tsx:194 — `mailto:ruscon2001@gmail.com?subject=...&body=...` — CORECT cross-platform

### app-settings:
- **PhoneContactsScreen.tsx:83** — `Linking.openURL('app-settings:')` — DOAR iOS
  - Pe Android trebuie `Linking.openSettings()` (care este deja folosit la linia 175!)
  - **Alert-ul de la linia 83 nu va functiona pe Android** — butonul "Settings" nu va face nimic

### App Store link:
- **SupportScreen.tsx:51** — `https://apps.apple.com/app/qrchat/id0000000000` — link DOAR iOS
  - Pe Android trebuie Play Store link (sau Platform.OS check)

---

## 15. MEDIAFILESSCREEN — ANDROID COMPATIBILITY

### Status: OK
- Foloseste `Database.getMediaByContact()` — nu depinde de CameraRoll/MediaLibrary
- FlatList grid cu `numColumns={3}` — functioneaza cross-platform
- Linking/Share pentru deschidere fisiere — functioneaza pe Android
- `file://` prefix adaugat corect

---

## LISTA COMPLETA PROBLEME CRITICE (necesita fix inainte de release Android)

| # | Fisier | Problema | Fix necesar |
|---|--------|---------|-------------|
| 1 | PhoneContactsScreen.tsx:55-113 | `Contacts.getAll()` fara `PermissionsAndroid.request()` | Adauga check Android permissions |
| 2 | PhoneContactsScreen.tsx:118 | SMS URL `&body=` in loc de `?body=` pe Android | Adauga `Platform.OS === 'android' ? '?body=' : '&body='` |
| 3 | PhoneContactsScreen.tsx:83 | `app-settings:` URL doar iOS | Inlocuieste cu `Linking.openSettings()` |
| 4 | SupportScreen.tsx:51 | Link App Store fara alternativa Play Store | Adauga Platform.OS check cu Play Store link |
| 5 | 15+ fisiere | shadow* props fara `elevation` | Adauga `elevation` pe toate elementele cu shadow |
| 6 | 4 ecrane | Header paddingTop: 60 hardcodat | Inlocuieste cu `useSafeAreaInsets().top + 16` |

---

## RECOMANDARI PRIORITARE

### P0 — Blocante Android release:
1. Fix `PermissionsAndroid.request(READ_CONTACTS)` in PhoneContactsScreen
2. Fix SMS URL separator (`?` pe Android)
3. Fix `app-settings:` URL pe Android
4. Adauga Play Store link alternativ in SupportScreen

### P1 — Probleme vizuale pe Android:
5. Adauga `elevation` pe toate elementele cu iOS shadow props (15+ locuri)
6. Fix 4 ecrane cu paddingTop hardcodat (QRGenerate, CreateGroup, GroupInfo, Upgrade)
7. Adauga `backgroundColor` pe StatusBar in ecranele care lipseste

### P2 — Imbunatatiri:
8. Inlocuieste `#FF6B00` hardcodat cu `C.primary` in PhoneContactsScreen
9. Adauga `ListEmptyComponent` pe GroupInfoScreen FlatList
10. Inlocuieste `'OK'` hardcodat in Alert cu `t('common.ok')` in UpgradeScreen

---

**CONCLUZIE:** Codebase-ul e bine structurat pentru cross-platform. ThemedActionSheet inlocuieste ActionSheetIOS (excelent). Tema si i18n sunt aproape complet. Problemele critice sunt concentrate in: (1) permisiuni Android, (2) URL-uri platform-specific, (3) shadows fara elevation. Cu aceste fix-uri, aplicatia va fi gata pentru Android.
