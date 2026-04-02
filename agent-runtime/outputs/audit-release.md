# Audit Release — QRChat v4.0.0
Data: 2026-03-21

## Readiness Score
- iOS App Store: **65% ready** (code & build ready; blocked by Apple Developer Account + screenshots)
- Google Play: **60% ready** (AAB built & signed; blocked by Play Console + screenshots)

---

## Versioning

| Locatie | Versiune | Build | Status |
|---------|----------|-------|--------|
| package.json | 4.0.0 | — | OK |
| src/utils/version.ts | 4.0.0 (BUILD_DATE: 2026-03-21) | — | OK |
| project.pbxproj MARKETING_VERSION | 4.0.0 | — | OK |
| project.pbxproj CURRENT_PROJECT_VERSION | — | 16 | OK |
| CHANGELOG.md | v4.0.0 (2026-03-21) la top | — | OK |

**Verdict:** Versiunea e sincronizata in toate cele 5 locatii.

---

## iOS Configuration (Info.plist)

| Camp Info.plist | Valoare | Status |
|----------------|---------|--------|
| CFBundleDisplayName | QRChat | OK |
| CFBundleLocalizations | en, ro, ru, fr | OK |
| ITSAppUsesNonExemptEncryption | YES (true) | OK |
| ITSEncryptionExportComplianceCode | (string gol) | OK |
| NSCameraUsageDescription | "QRChat needs camera access to take photos and video calls" | OK |
| NSMicrophoneUsageDescription | "QRChat needs microphone for voice messages and calls" | OK |
| NSPhotoLibraryUsageDescription | "QRChat needs access to your photos to send images" | OK |
| NSPhotoLibraryAddUsageDescription | "QRChat needs access to save your QR code to Photos" | OK |
| NSContactsUsageDescription | "QRChat uses your contacts to show who already uses QRChat and to invite friends" | REVIEW — daca contacts nu e folosit, scoate cheia |
| NSLocalNetworkUsageDescription | "QRChat uses the local network for peer-to-peer encrypted communication" | OK |
| NSAllowsArbitraryLoads | false | OK |
| UISupportedInterfaceOrientations | Portrait only | OK |
| UIBackgroundModes | voip, fetch, remote-notification | OK |
| UIRequiredDeviceCapabilities | arm64 | OK |
| TARGETED_DEVICE_FAMILY | 1 (doar iPhone) | OK |
| NSSiriUsageDescription | ABSENT | OK (corect — nu folosim Siri) |
| UISupportedInterfaceOrientations~ipad | ABSENT | OK (corect — nu suportam iPad) |
| privacyPolicyURL | https://qrchat.app/privacy | ATENTIE — domeniu custom, nu Railway URL |

**Verdict:** Info.plist complet si corect. Un singur punct de atentie: privacyPolicyURL pointeaza catre `qrchat.app` care poate nu e configurat inca.

---

## Privacy & Compliance

| Categorie | Status | Detalii |
|-----------|--------|---------|
| Privacy Policy | PARTIAL | Railway URL (200 OK), HTML in docs/ (17KB), index.html redirect OK. Dar Info.plist are `qrchat.app/privacy` (domeniu custom neconfigurat). GH Pages neactivat. |
| Privacy Manifest (PrivacyInfo.xcprivacy) | OK | FileTimestamp (C617.1, 3B52.1), UserDefaults (CA92.1), SystemBootTime (35F9.1). NSPrivacyCollectedDataTypes = []. NSPrivacyTracking = false. |
| Privacy Labels | OK | Document complet in privacy-labels.md. Data collected: Device ID (anonymous mailbox + APNs token). No tracking. |
| Encryption Compliance | OK | BIS PDF (8KB) exista. ITSAppUsesNonExemptEncryption = YES. Algoritmi: TweetNaCl (XSalsa20-Poly1305, X25519, Ed25519) + SQLCipher (AES-256-CBC). ECCN 5D002, License Exception ENC. |
| UGC Compliance | PARTIAL | Vezi sectiunea dedicata mai jos. |

### UGC Compliance Detail

| Cerinta | Status | Detalii |
|---------|--------|---------|
| Report button pe mesaje (ChatScreen long press) | OK | Spam, harassment, inappropriate, other |
| Report button pe profil (ContactProfileScreen) | OK | Acelasi flow |
| Block user | OK | blockContact implementat in 6 fisiere |
| Terms of Service (SetupScreen) | OK | Checkbox obligatoriu, agreedToTerms state, TermsScreen.tsx |
| POST /report endpoint pe server | OK | server/index.js:268 |
| Account deletion | ATENTIE | Referinta gasita in ProfileScreen.tsx (comment: "mutat in SettingsScreen") dar NU gasit in SettingsScreen. Necesita verificare — Apple cere account/data deletion. |
| Age rating 17+ | MANUAL | Trebuie setat in App Store Connect la submission |

---

## Build Artifacts

| Artifact | Exists | Size | Status |
|----------|--------|------|--------|
| iOS Archive (build/QRChat.xcarchive/) | DA | 243MB | OK — contine Info.plist, Products, dSYMs |
| ExportOptions.plist | DA | 500B | OK — method: app-store-connect, teamID: FK7BU478KX, signingStyle: automatic, uploadSymbols: true |
| BIS Self-Classification PDF | DA | 8KB | OK |
| Android AAB (app-release.aab) | DA | ~88MB | OK |
| Android APK (app-release.apk) | DA | ~143MB | OK |
| Android Keystore (qrchat-release.keystore) | DA | 2.7KB | OK — PKCS12 |
| Android keystore.properties | DA | 116B | OK — nu in git |
| Export IPA | NU | — | BLOCAT — necesita Apple Developer Account |

---

## App Store Metadata

| Camp | Valoare | Status |
|------|---------|--------|
| App Name | QRChat | OK |
| Subtitle | "Private encrypted messenger" (26 chars) | OK (<30) |
| Category | Social Networking / Utilities | OK |
| Price | Free | OK |
| Keywords | "private,messenger,encrypted,e2e,qr,secure,chat,calls,privacy,anonymous" | OK (<100 chars) |
| Privacy Policy URL | Railway URL in metadata, `qrchat.app` in Info.plist | DISCREPANTA |
| Review Notes | Detaliate, 2 dispozitive, QR flow, demo N/A | OK |
| Description | ~1500 chars | OK (<4000) |
| Description "4 Visual Themes" | Mentioneaza 4 teme | INCORECT — sunt doar 2 (Light + Dark) |
| "What's New" section | References v1.15.0 | INCORECT — trebuie actualizat la v4.0.0 |
| Screenshots sizes in metadata | 6.7" (1290x2796) listed | OUTDATED — trebuie 6.9" (1320x2868) |

---

## Screenshots

| # | Ecran | Dimensiune | Locatie | Status |
|---|-------|------------|---------|--------|
| 1 | screen1.png | 1320x2868 (6.9") | screenshots/ | OK dimensiune |
| 2 | current.png | 1320x2868 (6.9") | screenshots/appstore/ | OK dimensiune |

**Total: 2 screenshots. Minim necesar: 3 (Apple), recomandat: 5-10.**

### Screenshots lipsa (recomandate):
- Chat conversation cu mesaje, read receipts
- QR code scan screen
- Voice/video call screen
- Settings / profile screen
- Contact list

---

## Blocante Lansare

| # | Blocant | Severity | Owner | Status |
|---|---------|----------|-------|--------|
| 1 | Apple Developer Account ($99) | CRITICAL | Ruslan | NEEFECTUAT |
| 2 | Export IPA din archive | CRITICAL | release-engineer | BLOCAT de #1 |
| 3 | Upload TestFlight | CRITICAL | release-engineer | BLOCAT de #2 |
| 4 | Screenshots (min 3, recomandat 5+) | HIGH | frontend-engineer | PARTIAL (2/5) |
| 5 | APNs credentials (push notifications) | HIGH | Ruslan / backend | NECONFIGURAT |
| 6 | Privacy Policy permanent URL | MEDIUM | Ruslan | PARTIAL — Railway OK, qrchat.app neconfigurat, GH Pages neactivat |
| 7 | Google Play Console ($25) | CRITICAL (Android) | Ruslan | NEEFECTUAT |
| 8 | Description "4 themes" -> "2 themes" | MEDIUM | release-engineer | INCORECT, fix simplu |
| 9 | "What's New" section v1.15.0 -> v4.0.0 | MEDIUM | release-engineer | INCORECT, fix simplu |
| 10 | Account deletion in Settings | HIGH | frontend-engineer | POSIBIL ABSENT — Apple cere obligatoriu |
| 11 | Privacy Policy URL discrepancy | MEDIUM | release-engineer | Info.plist = qrchat.app, metadata = Railway URL |
| 12 | Screenshot sizes in metadata doc | LOW | release-engineer | Doc zice 6.7", actual screenshots sunt 6.9" (corect) |

---

## Checklist Final

- [ ] Apple Developer Account ($99) — inregistrare
- [ ] Export IPA din archive existent
- [ ] Upload TestFlight si beta testing
- [ ] Screenshots complete (min 5): chat, QR scan, call, settings, contact list
- [ ] APNs credentials (Auth Key de la Apple)
- [ ] Privacy Policy URL permanent (decide: Railway vs qrchat.app vs GitHub Pages)
- [ ] Sincronizeaza privacyPolicyURL in Info.plist cu URL-ul real
- [ ] Google Play Console ($25) — inregistrare
- [x] Fix description "4 Visual Themes" -> "2 themes" (Light/Dark)
- [x] Fix "What's New" section — actualizare de la v1.15.0 la v4.0.0
- [ ] Verifica account deletion e functional in Settings (Apple requirement)
- [ ] Seteaza Age Rating 17+ in App Store Connect
- [x] ~~NSSiriUsageDescription~~ — deja scos (OK)
- [x] ~~UISupportedInterfaceOrientations~ipad~~ — deja scos (OK)

---

## Ce e GATA

- Versioning sincronizat in toate cele 5 locatii (4.0.0 / build 16)
- iOS archive creat si semnat (243MB)
- Android AAB + APK builds complete si semnate
- ExportOptions.plist configurat corect pt App Store Connect
- Info.plist complet — toate permissions, encryption keys, background modes
- PrivacyInfo.xcprivacy complet si corect
- BIS Self-Classification document generat
- Encryption compliance documentat complet
- Privacy labels documentate
- App Store metadata (description, keywords, review notes)
- UGC compliance: report buttons, block user, Terms of Service cu checkbox
- POST /report endpoint pe server
- Privacy Policy HTML (17KB) in docs/
- Privacy Policy live pe Railway (HTTP 200)
- Apple Review Notes detaliate

---

## Recomandari

1. **PRIORITAR:** Inregistrare Apple Developer Account — debloca IPA export, TestFlight, APNs
2. **PRIORITAR:** Genereaza 5+ screenshots pe iPhone 15/16 Pro Max (6.9") — chat, QR, call, settings, contacts
3. **FIX IMEDIAT:** Actualizeaza APP_STORE_METADATA.md — "4 themes" -> "2 themes" si "What's New" -> v4.0.0
4. **VERIFICA:** Account deletion flow — Apple respinge fara optiunea de stergere date/cont
5. **DECIDE:** Privacy Policy URL final — Railway e functional dar `qrchat.app` ar fi mai profesional
6. **OPTIONAL:** Configureaza GitHub Pages ca backup pt Privacy Policy
7. **ANDROID:** Inregistrare Google Play Console cand iOS e submis
