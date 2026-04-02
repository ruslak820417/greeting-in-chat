# Audit Hardcoded Strings — QRChat v4.0.0

**Data:** 2026-03-21
**Auditor:** i18n-specialist
**Scope:** `src/screens/`, `src/components/`, `src/utils/ThemeContext.tsx`
**Metodologie:** Grep + citire manuala a fiecarui fisier TSX

---

## Texte hardcodate gasite

### CRITICE — Texte vizibile user-ului, direct in JSX sau Alert

| Fisier | Linie | Text | Limba | Fix sugerat |
|--------|-------|------|-------|-------------|
| `components/ErrorBoundary.tsx` | 35 | `"Something went wrong"` | EN | `t('error.title')` |
| `components/ErrorBoundary.tsx` | 37 | `"An unexpected error occurred"` | EN | `t('error.unexpected')` |
| `components/ErrorBoundary.tsx` | 40 | `"Try Again"` | EN | `t('error.tryAgain')` |
| `components/NotificationBanner.tsx` | 66 | `"QRChat"` | Brand | `t('app.name')` sau constant |
| `components/SplashScreen.tsx` | 69 | `"QR"` | Brand | Constant brand — OK daca intentionat |
| `components/SplashScreen.tsx` | 71 | `"HAT"` | Brand | Constant brand — OK daca intentionat |
| `components/SplashScreen.tsx` | 99 | `"© 2026 Ruslan Constantinovici"` | EN | `t('app.copyright')` |
| `screens/UpgradeScreen.tsx` | 86 | `"QRChat Unlimited"` (header title) | EN | `t('upgrade.headerTitle')` |
| `screens/UpgradeScreen.tsx` | 50 | `"OK"` (Alert button) | EN | `t('common.ok')` |
| `screens/UpgradeScreen.tsx` | 127 | `"$2.99"` (pret hardcodat) | EN | `t('upgrade.price')` sau din StoreKit |
| `screens/SettingsScreen.tsx` | 370 | `"QRCHAT UNLIMITED"` (section title) | EN | `t('upgrade.sectionTitle')` |
| `screens/SettingsScreen.tsx` | 387 | `"QRChat Unlimited"` (label cand activ) | EN | `t('upgrade.unlimitedActive')` |
| `screens/SettingsScreen.tsx` | 397 | `"Upgrade"` (buton text) | EN | `t('upgrade.upgradeButton')` |
| `screens/SettingsScreen.tsx` | 439 | `placeholder="QRCHAT-XXXX-XXXX-XXXX"` | EN | OK — format cod, nu text vizibil |
| `screens/SettingsScreen.tsx` | 482 | `"QRChat v... · Ed25519 + X25519 · Relay E2E + WebRTC P2P"` | EN | `t('app.techInfo')` sau OK ca info tehnica |
| `screens/SettingsScreen.tsx` | 542 | `"© 2026 Ruslan Constantinovici. All rights reserved."` | EN | `t('app.copyright')` |
| `screens/ProfileScreen.tsx` | 173 | `"Ed25519 + X25519"` | EN | OK — nume tehnice, nu se traduc |
| `screens/ProfileScreen.tsx` | 220 | `"QRChat v... · Ed25519 + X25519 · Relay E2E + WebRTC P2P"` | EN | Same ca Settings |
| `screens/ProfileScreen.tsx` | 223 | `"© 2026 Ruslan Constantinovici. All rights reserved."` | EN | `t('app.copyright')` |
| `screens/ThemeEditorScreen.tsx` | 79 | `"Reset"` (buton) | EN | `t('themeEditor.resetButton')` |
| `screens/ThemeEditorScreen.tsx` | 95 | `"Salut!"` (preview bubble) | RO | `t('themeEditor.previewMsg1')` |
| `screens/ThemeEditorScreen.tsx` | 98 | `"Bună!"` (preview bubble) | RO | `t('themeEditor.previewMsg2')` |
| `screens/ThemeEditorScreen.tsx` | 101 | `"Preview..."` | EN | `t('themeEditor.previewMsg3')` |
| `screens/ThemeEditorScreen.tsx` | 162 | `placeholder="#FF6B00"` | EN | OK — format HEX, nu text user |
| `screens/ChatScreen.tsx` | 457 | `Alert.alert('Error', ...)` — titlu `'Error'` hardcodat | EN | `t('common.error')` |
| `screens/ChatScreen.tsx` | 477 | `Alert.alert('Error', ...)` — titlu `'Error'` hardcodat | EN | `t('common.error')` |
| `screens/ChatScreen.tsx` | 601 | `"Video"` (label sub icon) | EN | `t('chat.videoLabel')` |
| `screens/ChatScreen.tsx` | 608 | `"Video"` (subtitle in bubble) | EN | `t('chat.videoLabel')` |
| `screens/ChatScreen.tsx` | 1848 | `[{ text: 'OK' }]` (Alert button) | EN | `t('common.ok')` |
| `screens/ChatScreen.tsx` | 1936 | `` `Max 25 MB. Acest video: ${...} MB` `` | RO | `t('chat.videoTooLargeMsg', { size })` |
| `screens/HomeScreen.tsx` | 575-577 | `"QR"`, `"C"`, `"HAT"` (logo text) | Brand | OK — brand display |
| `screens/ContactProfileScreen.tsx` | 192 | `"User ID:"`, `"User Name:"`, `"Unknown"`, `"Reason:"`, `"Additional details:"` (report email body) | EN | `t('contactProfile.reportBody')` |

### MEDII — Fallback-uri romanesti in `|| 'text'` (apar daca cheia i18n lipseste)

| Fisier | Linie | Fallback text | Limba | Fix sugerat |
|--------|-------|---------------|-------|-------------|
| `screens/ChatScreen.tsx` | 434 | `|| 'File'` | EN | Adauga cheia `chat.file` in toate limbile |
| `screens/ChatScreen.tsx` | 457, 477 | `|| 'File not found'` | EN | Adauga cheia `chat.fileUnavailable` |
| `screens/ChatScreen.tsx` | 528 | `|| 'Trimitere...'` | RO | Adauga cheia `chat.sending` |
| `screens/ChatScreen.tsx` | 528 | `|| 'Se descarcă...'` | RO | Adauga cheia `chat.downloading` |
| `screens/ChatScreen.tsx` | 563 | `|| 'Se descarcă...'` | RO | Duplicate — same fix |
| `screens/ChatScreen.tsx` | 569 | `|| 'Indisponibil'` | RO | Adauga cheia `chat.fileUnavailable` |
| `screens/ChatScreen.tsx` | 1846 | `|| 'Fișier prea mare'` | RO | Adauga cheia `chat.fileTooLarge` |
| `screens/ChatScreen.tsx` | 1847 | `|| 'Dimensiunea maximă acceptată este 25 MB...'` | RO | Adauga cheia `chat.fileTooLargeMsg` |
| `screens/ChatScreen.tsx` | 1935 | `|| 'Fișier prea mare'` | RO | Duplicate |
| `components/NotificationBanner.tsx` | 27 | `|| 'Fișier'` | RO | Adauga cheia `notifications.file` |
| `screens/PhoneContactsScreen.tsx` | 78 | `|| 'Acces contacte'` | RO | Adauga cheia `phoneContacts.permissionTitle` |
| `screens/PhoneContactsScreen.tsx` | 79 | `|| 'QRChat are nevoie de acces...'` | RO | Adauga cheia `phoneContacts.permissionMessage` |
| `screens/PhoneContactsScreen.tsx` | 81 | `|| 'Anulează'` | RO | Adauga cheia `common.cancel` |
| `screens/PhoneContactsScreen.tsx` | 82 | `|| 'Settings'` | EN | Adauga cheia `phoneContacts.openSettings` |

### SCAZUTE — defaultValue in t() (functional dar suboptimal)

| Fisier | Linie | Text in `defaultValue` | Limba | Fix sugerat |
|--------|-------|------------------------|-------|-------------|
| `screens/SupportScreen.tsx` | 24 | `'Conditii de utilizare'` | RO | Muta in fisierul de traduceri `ro.json` |
| `screens/SupportScreen.tsx` | 30 | `'Politica de confidentialitate'` | RO | Muta in fisierul de traduceri `ro.json` |
| `screens/SupportScreen.tsx` | 35 | `'FAQ'` | EN | Muta in fisierul de traduceri |
| `screens/SupportScreen.tsx` | 36 | `'Intrebari frecvente'` | RO | Muta in fisierul de traduceri `ro.json` |
| `screens/SupportScreen.tsx` | 41 | `'Evalueaza aplicatia'` | RO | Muta in fisierul de traduceri `ro.json` |
| `screens/SupportScreen.tsx` | 42 | `'Lasa un review pe App Store'` | RO | Muta in fisierul de traduceri `ro.json` |
| `screens/SupportScreen.tsx` | 66 | `'Cum te putem ajuta?'` | RO | Muta in fisierul de traduceri `ro.json` |
| `screens/SettingsScreen.tsx` | 494 | `{ defaultValue: 'Privacy Policy' }` | EN | Muta in fisierul de traduceri |

### DATE TEHNICE — Hardcodat in ThemeContext (nu in JSX dar afisat in UI)

| Fisier | Linie | Text | Limba | Fix sugerat |
|--------|-------|------|-------|-------------|
| `utils/ThemeContext.tsx` | 116 | `name: 'Light'`, `subtitle: 'Clar · Clasic'` | EN+RO | Foloseste chei i18n |
| `utils/ThemeContext.tsx` | 117 | `name: 'Dark'`, `subtitle: 'Inchis · Modern'` | EN+RO | Foloseste chei i18n |
| `utils/ThemeContext.tsx` | 199 | `label: 'Culori principale'` | RO | `t('themeEditor.groupColors')` |
| `utils/ThemeContext.tsx` | 201-203 | `label: 'Accent principal'` etc. | RO | Chei i18n |
| `utils/ThemeContext.tsx` | 207 | `label: 'Fundal'` | RO | Chei i18n |
| `utils/ThemeContext.tsx` | 209-212 | `label: 'Fundal general'` etc. | RO | Chei i18n |
| `utils/ThemeContext.tsx` | 216 | `label: 'Text'` | RO | Chei i18n |
| `utils/ThemeContext.tsx` | 218-220 | `label: 'Text principal'` etc. | RO | Chei i18n |
| `utils/ThemeContext.tsx` | 224 | `label: 'Chat'` | RO | Chei i18n |
| `utils/ThemeContext.tsx` | 226-227 | `label: 'Bule trimise'` etc. | RO | Chei i18n |

### BOOT LOG — SplashScreen (decorativ, posibil OK)

| Fisier | Linie | Text | Limba | Fix sugerat |
|--------|-------|------|-------|-------------|
| `components/SplashScreen.tsx` | 25-34 | `"> init nacl.secretbox ..."` etc. (10 linii boot log) | EN | Decorativ/tehnic — poate ramane hardcodat |

---

## Sumar

| Categorie | Count |
|-----------|-------|
| **CRITICE** — texte vizibile hardcodate | 30 |
| **MEDII** — fallback-uri `\|\| 'text'` | 14 |
| **SCAZUTE** — defaultValue in t() | 8 |
| **ThemeContext** — labels hardcodate | 12 |
| **Decorativ** — boot log, brand | ~12 |
| **TOTAL** | **~76** |

## Ecrane curate (fara probleme)

- `WelcomeScreen.tsx` — toate textele folosesc `t()`
- `SetupScreen.tsx` — toate textele folosesc `t()`
- `CallScreen.tsx` — toate textele folosesc `t()`
- `CallLogScreen.tsx` — toate textele folosesc `t()`
- `QRScanScreen.tsx` — toate textele folosesc `t()`
- `QRGenerateScreen.tsx` — toate textele folosesc `t()`
- `CreateGroupScreen.tsx` — toate textele folosesc `t()`
- `GroupInfoScreen.tsx` — toate textele folosesc `t()`
- `PendingApprovalScreen.tsx` — toate textele folosesc `t()`
- `ContactsScreen.tsx` — toate textele folosesc `t()`
- `IncomingCallOverlay.tsx` — toate textele folosesc `t()`
- `TermsScreen.tsx` — toate textele folosesc `t()`
- `StyledName.tsx` — fara text user-visible
- `Logo.tsx` — fara text user-visible
- `ThemedActionSheet.tsx` — primeste text ca props

## Prioritate fix

1. **ErrorBoundary.tsx** — nu foloseste deloc `useTranslation` (e class component). Necesita refactorizare.
2. **ChatScreen.tsx** — 2x `Alert.alert('Error', ...)` cu titlu hardcodat + fallback-uri RO + `"Video"` label + `"OK"` button
3. **SupportScreen.tsx** — 7 defaultValue-uri in romana (confirmat: textele vizibile "Conditii de utilizare" etc. vin din defaultValue, NU din i18n JSON)
4. **SettingsScreen.tsx** — "QRCHAT UNLIMITED", "Upgrade", "QRChat Unlimited" hardcodate
5. **UpgradeScreen.tsx** — "QRChat Unlimited" header, "$2.99", "OK" button
6. **ThemeEditorScreen.tsx** — "Reset", "Salut!", "Bună!", "Preview..."
7. **ThemeContext.tsx** — toate label-urile tema editor in romana
8. **ProfileScreen.tsx** + **SettingsScreen.tsx** — copyright duplicat
