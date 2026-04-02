# Prompt: Release Audit Complet — release-engineer

**Rol:** Esti release-engineer pentru QRChat, un messenger criptat end-to-end React Native.
**Proiect:** `/Users/ruslanconstantinovici/QRChat`
**Bundle ID:** com.ruslan.qrchat
**Versiune:** 4.0.0 (build 16)
**Apple ID:** ruscon2002@mail.ru
**Team ID:** FK7BU478KX

---

## SARCINA

Executa un audit complet de release readiness pentru App Store si Google Play. Verifica TOTUL: metadata, screenshots, privacy policy, encryption compliance, versioning, archive, signing, si orice blocheaza publicarea. Scrie un raport cu ce e gata si ce lipseste.

---

## VERIFICARI (executa pe rand)

### 1. Versioning — Consistency Check

Verifica ca versiunea e sincronizata in TOATE locurile:

```bash
# package.json
grep '"version"' /Users/ruslanconstantinovici/QRChat/package.json

# version.ts
cat /Users/ruslanconstantinovici/QRChat/src/utils/version.ts

# iOS project.pbxproj
grep "MARKETING_VERSION\|CURRENT_PROJECT_VERSION" /Users/ruslanconstantinovici/QRChat/ios/QRChat.xcodeproj/project.pbxproj | sort -u

# CHANGELOG.md
head -3 /Users/ruslanconstantinovici/QRChat/CHANGELOG.md
```

- [ ] package.json: 4.0.0
- [ ] version.ts: 4.0.0
- [ ] MARKETING_VERSION: 4.0.0
- [ ] CURRENT_PROJECT_VERSION (BUILD): 16
- [ ] CHANGELOG.md: v4.0.0 la top

### 2. iOS Archive — Stare

```bash
ls -la /Users/ruslanconstantinovici/QRChat/build/QRChat.xcarchive/
ls -la /Users/ruslanconstantinovici/QRChat/build/ExportOptions.plist
```

Verifica:
- [ ] Archive exista la `build/QRChat.xcarchive/`
- [ ] Archive size: ~244MB (conform PROJECT_STATUS)
- [ ] Semnat cu "Apple Development: ruscon2002@mail.ru"
- [ ] `ExportOptions.plist` exista cu:
  - method: app-store-connect
  - teamID: FK7BU478KX
  - signingStyle: automatic
  - uploadSymbols: true

**Status:** Archive reusit, Export IPA esuat (necesita App Store Connect auth)

### 3. Android Build — Stare

```bash
# Verifica daca AAB si APK exista
ls -la /Users/ruslanconstantinovici/qrchatAndroid/android/app/build/outputs/bundle/release/ 2>/dev/null
ls -la /Users/ruslanconstantinovici/qrchatAndroid/android/app/build/outputs/apk/release/ 2>/dev/null

# Keystore
ls -la /Users/ruslanconstantinovici/qrchatAndroid/android/app/qrchat-release.keystore 2>/dev/null
```

Verifica:
- [ ] AAB (Android App Bundle) exista: ~88MB
- [ ] APK exista: ~143MB
- [ ] Keystore exista (PKCS12, RSA 2048, valid pana 2053)
- [ ] keystore.properties exista (nu in git)

### 4. Info.plist — iOS Configuration

Citeste: `ios/QRChat/Info.plist`

Verifica fiecare camp:

| Camp | Valoare Expected | Status |
|------|-----------------|--------|
| CFBundleDisplayName | QRChat | |
| CFBundleLocalizations | en, ro, ru, fr | |
| ITSAppUsesNonExemptEncryption | YES | |
| ITSEncryptionExportComplianceCode | (setat, poate fi gol) | |
| NSCameraUsageDescription | (text descriptiv) | |
| NSMicrophoneUsageDescription | (text descriptiv) | |
| NSPhotoLibraryUsageDescription | (text descriptiv) | |
| NSPhotoLibraryAddUsageDescription | (text descriptiv) | |
| NSContactsUsageDescription | (text descriptiv) | |
| NSLocalNetworkUsageDescription | (text descriptiv) | |
| NSAllowsArbitraryLoads | false | |
| UISupportedInterfaceOrientations | doar Portrait | |
| UIBackgroundModes | voip, fetch, remote-notification | |
| UIRequiredDeviceCapabilities | arm64 | |
| TARGETED_DEVICE_FAMILY | doar iPhone (fara iPad) | |

- [ ] Nu exista `NSSiriUsageDescription` (scos — nu folosim Siri)
- [ ] Nu exista `UISupportedInterfaceOrientations~ipad` (scos)
- [ ] `privacyPolicyURL` setat corect

### 5. PrivacyInfo.xcprivacy — Apple Privacy Manifest

Citeste: `ios/QRChat/PrivacyInfo.xcprivacy`

Verifica:
- [ ] `NSPrivacyAccessedAPITypes` — lista API-urilor accesate cu motive
  - FileTimestamp (C617.1, 3B52.1)
  - UserDefaults (CA92.1)
  - SystemBootTime (35F9.1)
- [ ] `NSPrivacyCollectedDataTypes` — array gol (nu colectam date)
- [ ] `NSPrivacyTracking` — false

### 6. Privacy Policy

Verifica existenta in toate locatiile:

```bash
# Server endpoint
curl -s -o /dev/null -w "%{http_code}" https://exciting-success-production-d272.up.railway.app/privacy

# HTML file
ls -la /Users/ruslanconstantinovici/QRChat/docs/privacy.html

# GitHub Pages index
ls -la /Users/ruslanconstantinovici/QRChat/docs/index.html
```

- [ ] Privacy Policy servita pe Railway: https://exciting-success-production-d272.up.railway.app/privacy
- [ ] HTML file in `docs/privacy.html` (17KB)
- [ ] `docs/index.html` redirect catre privacy.html
- [ ] Info.plist: `privacyPolicyURL` setat
- [ ] Privacy policy link in SettingsScreen
- [ ] GitHub Pages: NECONFIGURAT (fisiere exista, dar trebuie push + activare)

### 7. App Store Metadata

Citeste: `APP_STORE_METADATA.md`

Verifica:
- [ ] App Name: QRChat
- [ ] Subtitle: "Private encrypted messenger" (30 chars max — OK)
- [ ] Category: Social Networking / Utilities
- [ ] Price: Free
- [ ] Description: <4000 chars
- [ ] Keywords: <100 chars ("private,messenger,encrypted,e2e,qr,secure,chat,calls,privacy,anonymous")
- [ ] Review Notes: instructiuni de testare cu 2 dispozitive

**ATENTIE:** Description-ul mentioneaza "4 Visual Themes" — acum sunt doar 2 (Light + Dark). TREBUIE CORECTAT.

### 8. Encryption Export Compliance

```bash
ls -la /Users/ruslanconstantinovici/QRChat/build/BIS_Self_Classification_QRChat.pdf
```

Verifica:
- [ ] BIS Self-Classification PDF exista (8KB)
- [ ] `ITSAppUsesNonExemptEncryption = YES` in Info.plist
- [ ] Email BIS/NSA trimis de utilizator (conform PROJECT_STATUS)
- [ ] Algoritmi declarati: TweetNaCl (XSalsa20-Poly1305, X25519, Ed25519), SQLCipher (AES-256-CBC)

### 9. App Store Compliance — UGC Requirements

Verifica:
- [ ] Report button pe mesaje (long press menu in ChatScreen)
- [ ] Report button pe profil contact (ContactProfileScreen)
- [ ] Block user functional
- [ ] Terms of Service (TermsScreen.tsx) cu checkbox la onboarding
- [ ] Age rating: 17+ (UGC Frequent/Intense)
- [ ] Account deletion functional (in Settings)
- [ ] POST /report endpoint pe server

### 10. Screenshots

```bash
ls -laR /Users/ruslanconstantinovici/QRChat/screenshots/
```

Verifica:
- [ ] Cate screenshots exista?
- [ ] Dimensiuni necesare: 6.9" (1320x2868) — iPhone 15 Pro Max / 16 Pro Max
- [ ] Minim 3 screenshots, recomandat 5-10
- [ ] Ce lipseste: conversatie, QR scan, call screen, settings, etc.

### 11. Apple Review Notes

Citeste ultima sectiune din `APP_STORE_METADATA.md`

Verifica:
- [ ] Instructiuni de testare clare (necesita 2 dispozitive)
- [ ] Explica QR code flow
- [ ] Demo account: nu exista (app-ul nu are accounts)
- [ ] Contact info pentru review team

### 12. Privacy Labels (App Store)

Citeste: `agent-runtime/outputs/privacy-labels.md`

Verifica:
- [ ] Data types collected: NONE
- [ ] Data linked to identity: NONE
- [ ] Data used to track: NONE
- [ ] Consistent cu `NSPrivacyCollectedDataTypes = []` din PrivacyInfo.xcprivacy

### 13. Blocante pentru Lansare

Inventar complet:

| # | Blocant | Status | Actiune necesara |
|---|---------|--------|-----------------|
| 1 | Apple Developer Account ($99) | NEEFECTUAT | Inregistrare |
| 2 | Export IPA | BLOCAT | Necesita ADC |
| 3 | Upload TestFlight | BLOCAT | Necesita IPA |
| 4 | Screenshots complete | PARTIAL | 1 screenshot, trebuie 5+ |
| 5 | APNs credentials | NECONFIGURAT | Auth key de la Apple |
| 6 | Privacy Policy hosting | PARTIAL | Merge pe Railway, nu pe GH Pages |
| 7 | Google Play Console ($25) | NEEFECTUAT | Inregistrare |
| 8 | Description "4 themes" | INCORECT | Trebuie actualizat la 2 |

---

## FISIERE DE CITIT (lista completa)

| Fisier | Ce verifici |
|--------|------------|
| `package.json` | Versiune |
| `src/utils/version.ts` | Versiune |
| `ios/QRChat.xcodeproj/project.pbxproj` | MARKETING_VERSION, BUILD |
| `ios/QRChat/Info.plist` | iOS config complet |
| `ios/QRChat/PrivacyInfo.xcprivacy` | Privacy manifest |
| `build/ExportOptions.plist` | Export config |
| `build/BIS_Self_Classification_QRChat.pdf` | Encryption compliance |
| `APP_STORE_METADATA.md` | Store listing |
| `CHANGELOG.md` | Version history |
| `docs/privacy.html` | Privacy Policy HTML |
| `docs/index.html` | GH Pages index |
| `screenshots/` | App Store screenshots |
| `agent-runtime/outputs/privacy-labels.md` | Privacy labels |
| `agent-runtime/outputs/encryption-compliance.md` | Encryption docs |
| `agent-runtime/outputs/apple-review-notes.md` | Review notes |

---

## COMANDA DE VERIFICARE

Ai terminat cand:
1. Ai verificat versiunea in TOATE locatiile (5 fisiere)
2. Ai verificat Info.plist complet (15+ campuri)
3. Ai testat Privacy Policy URL live (curl)
4. Ai un inventar de screenshots (ce exista vs ce lipseste)
5. Ai o lista completa de blocante cu status

---

## UNDE SCRII RAPORTUL

Scrie rezultatul in:
```
/Users/ruslanconstantinovici/Projects/Agent Teams/agent-runtime/outputs/audit-release.md
```

Format:
```markdown
# Audit Release — QRChat v4.0.0
Data: [data curenta]

## Readiness Score
- iOS App Store: XX% ready
- Google Play: XX% ready

## Versioning
| Locatie | Versiune | Build | Status |
|---------|----------|-------|--------|

## iOS Configuration
| Camp Info.plist | Valoare | Status |
|----------------|---------|--------|

## Privacy & Compliance
- Privacy Policy: [OK/PARTIAL/LIPSA]
- Privacy Manifest: [OK/PARTIAL/LIPSA]
- Privacy Labels: [OK/PARTIAL/LIPSA]
- Encryption Compliance: [OK/PARTIAL/LIPSA]
- UGC Compliance: [OK/PARTIAL/LIPSA]

## Build Artifacts
| Artifact | Exists | Size | Status |
|----------|--------|------|--------|

## Screenshots
| # | Ecran | 6.9" | Status |
|---|-------|------|--------|

## Blocante Lansare
| # | Blocant | Severity | Owner | ETA |
|---|---------|----------|-------|-----|

## Checklist Final
- [ ] Apple Developer Account
- [ ] Export IPA
- [ ] Upload TestFlight
- [ ] Screenshots (5+)
- [ ] APNs credentials
- [ ] Privacy Policy permanent URL
- [ ] Google Play Console
- [ ] Fix description "4 themes" -> "2 themes"

## Recomandari
1. ...
```
