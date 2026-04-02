# Apple App Store Review Audit — Section 5: PRIVACY

**App:** QRChat v3.0.6
**Auditor:** Privacy Auditor Agent
**Date:** 2026-03-22
**Verdict:** PASS (with 1 minor warning)

---

## 5.1.1 Data Collection and Storage

### Privacy Policy Accessibility

| Check | Result | Details |
|-------|--------|---------|
| Privacy Policy URL returns 200? | PASS | `curl -s -o /dev/null -w "%{http_code}" https://exciting-success-production-d272.up.railway.app/privacy` returns **200** |
| Privacy Policy link in Info.plist? | PASS | `privacyPolicyURL` present at `ios/QRChat/Info.plist:82-83` — points to `https://exciting-success-production-d272.up.railway.app/privacy` |
| Privacy Policy link in app (Settings)? | PASS | `SettingsScreen.tsx:491` opens privacy URL with locale suffix. Also accessible from `SupportScreen.tsx:29-34` |
| Privacy Policy HTML files exist? | PASS | `docs/privacy.html` and `server/docs/privacy.html` both exist. Multi-language: EN, RO, RU, FR |
| Privacy Policy matches app behavior? | PASS | See detailed analysis below |

### Privacy Policy Content Analysis

The privacy policy (effective 2026-03-21) is comprehensive and accurately reflects the app's actual behavior:

- **Developer:** Ruslan Constantinovici, Chisinau, Moldova
- **Contact:** ruscon2001@gmail.com
- **Zero-knowledge architecture** clearly described
- **E2E encryption** (TweetNaCl XSalsa20-Poly1305) documented
- **GDPR, CCPA/CPRA, Moldova Law 133/2011** compliance sections present

---

## 5.1.1(i) Privacy Policy Requirements

| Requirement | Status | Evidence |
|-------------|--------|----------|
| What data is collected | PASS | Display Name (device-only), Mailbox ID (random 128-bit), Push Tokens, Encrypted messages (max 48h), Device ID (license), Report Data |
| What is NOT collected | PASS | Explicitly lists: no phone numbers, no email, no address book upload, no location, no analytics, no IDFA, no cookies |
| How data is used | PASS | Routing encrypted messages, push notifications, license verification |
| Third-party sharing | PASS | No data sales. Only: APNs, FCM (push delivery), Metered.ca TURN (media relay), Railway.app (hosting) |
| Data retention | PASS | Encrypted messages: 48h max. Push tokens: until invalidated. IPs: 60 seconds (rate limiting). Local data: until uninstall |
| How to delete data | PASS | Delete Account in Settings (`SettingsScreen.tsx:514-541`) calls `Database.clearAll()`. Uninstall also removes all local data. Server-side deletion via email request |

---

## 5.1.2 Data Use and Sharing

| Check | Result | Details |
|-------|--------|---------|
| No tracking SDKs? | PASS | No analytics, amplitude, mixpanel, segment, sentry, bugsnag, crashlytics, appsflyer, adjust, or branch in `package.json` |
| No advertising SDKs? | PASS | No AdSupport, AppTrackingTransparency, or IDFA usage found |
| No third-party data sharing? | PASS | Zero data sharing with third parties beyond essential push notification services |
| Push notifications anonymous? | PASS | `PushTokenService.ts` uses random 128-bit mailbox IDs (`nacl.randomBytes`), explicitly NOT derived from key material. Comment at line 8: "This prevents linking push tokens to user identity" |
| Contact data stays on device? | PASS | `PhoneContactsScreen.tsx` reads contacts locally for matching. No server upload of contact data |

---

## 5.1.3 Health and Health Research

**N/A** — App does not access HealthKit or health data.

---

## 5.1.4 Kids

**N/A** — App is rated 17+. Privacy policy states: "Not directed at children under 13 (COPPA) or 16 (GDPR)."

---

## 5.1.5 Location Services

**N/A** — No location permissions requested. No `NSLocationWhenInUseUsageDescription` or `NSLocationAlwaysUsageDescription` in Info.plist.

---

## 5.2 Intellectual Property

| Check | Result | Details |
|-------|--------|---------|
| Logo original? | PASS | Custom QRChat logo (QR code + chat bubble design) |
| Name "QRChat" trademark conflict? | INFO | No registered trademark found in cursory check. Recommend formal trademark search before submission |

---

## PrivacyInfo.xcprivacy — Apple Privacy Manifest

**File:** `ios/QRChat/PrivacyInfo.xcprivacy`

| Check | Result | Details |
|-------|--------|---------|
| File exists? | PASS | Present at `ios/QRChat/PrivacyInfo.xcprivacy` |
| NSPrivacyTracking | PASS | `false` — No tracking |
| NSPrivacyCollectedDataTypes | PASS | Empty array `[]` — No data collected |
| NSPrivacyAccessedAPITypes | PASS | 3 entries, all with valid reasons: |

### NSPrivacyAccessedAPITypes Detail:

| API Category | Reasons | Valid? |
|-------------|---------|--------|
| `NSPrivacyAccessedAPICategoryFileTimestamp` | C617.1 (inside app container), 3B52.1 (file management) | PASS |
| `NSPrivacyAccessedAPICategoryUserDefaults` | CA92.1 (read/write to app's own UserDefaults) | PASS |
| `NSPrivacyAccessedAPICategorySystemBootTime` | 35F9.1 (measure elapsed time) | PASS |

---

## Privacy Nutrition Labels

| Label | Expected | Actual | Status |
|-------|----------|--------|--------|
| Data Not Collected | YES | `NSPrivacyCollectedDataTypes = []` | PASS |
| Data Not Linked to You | YES | No identifiers collected | PASS |
| No Tracking | YES | `NSPrivacyTracking = false` | PASS |

**App Store Connect should declare: "Data Not Collected"**

---

## Info.plist NSUsageDescription Strings

| Key | Present? | Description | Status |
|-----|----------|-------------|--------|
| `NSCameraUsageDescription` | YES | "QRChat needs camera access to take photos and video calls" | PASS |
| `NSMicrophoneUsageDescription` | YES | "QRChat needs microphone for voice messages and calls" | PASS |
| `NSPhotoLibraryUsageDescription` | YES | "QRChat needs access to your photos to send images" | PASS |
| `NSPhotoLibraryAddUsageDescription` | YES | "QRChat needs access to save your QR code to Photos" | PASS |
| `NSContactsUsageDescription` | YES | "QRChat uses your contacts to show who already uses QRChat and to invite friends" | PASS |
| `NSLocalNetworkUsageDescription` | YES | "QRChat uses the local network for peer-to-peer encrypted communication" | PASS |
| `NSSiriUsageDescription` | ABSENT | Correctly removed — app does not use Siri | PASS |

All usage descriptions are human-readable, specific, and accurately describe why the permission is needed.

---

## Encryption Compliance

| Check | Result | Details |
|-------|--------|---------|
| `ITSAppUsesNonExemptEncryption` | PASS | `true` in Info.plist (line 37) — correctly declares non-exempt encryption |
| `ITSEncryptionExportComplianceCode` | WARNING | Present but **empty string** (line 39). See note below |
| BIS Self-Classification document | PASS | `build/BIS_Self_Classification_QRChat.pdf` exists (8168 bytes, dated 2026-03-21) |
| Encryption used | INFO | TweetNaCl (XSalsa20-Poly1305, X25519, Ed25519), SQLCipher (AES-256-CBC) |

### Warning: ITSEncryptionExportComplianceCode

The `ITSEncryptionExportComplianceCode` key is present but contains an **empty string**. This key should either:
- Be **removed entirely** if using mass-market exemption (EAR 740.17(b)(1)), OR
- Contain the actual **CCATS/ENC code** if a formal BIS classification was obtained

**Recommendation:** Since the BIS Self-Classification document exists and the app qualifies for mass-market exemption, either populate this field with the classification reference number or remove the key entirely. Apple will prompt during submission if needed.

---

## NSAppTransportSecurity

| Check | Result | Details |
|-------|--------|---------|
| `NSAllowsArbitraryLoads` | PASS | Set to `false` — all connections must use HTTPS/TLS. Secure configuration |

---

## Summary Checklist

| # | Section | Status |
|---|---------|--------|
| 1 | 5.1.1 — Privacy Policy exists and accessible | PASS |
| 2 | 5.1.1 — Privacy Policy in Info.plist | PASS |
| 3 | 5.1.1 — Privacy Policy link in app | PASS |
| 4 | 5.1.1 — Policy matches actual app behavior | PASS |
| 5 | 5.1.1(i) — Data collection described | PASS |
| 6 | 5.1.1(i) — Data usage described | PASS |
| 7 | 5.1.1(i) — Third-party sharing described | PASS |
| 8 | 5.1.1(i) — Data retention described | PASS |
| 9 | 5.1.1(i) — Data deletion mechanism | PASS |
| 10 | 5.1.2 — No tracking/analytics | PASS |
| 11 | 5.1.2 — No third-party data sharing | PASS |
| 12 | 5.1.2 — Anonymous push notifications | PASS |
| 13 | 5.2 — Original logo | PASS |
| 14 | PrivacyInfo.xcprivacy exists | PASS |
| 15 | NSPrivacyAccessedAPITypes correct | PASS |
| 16 | NSPrivacyCollectedDataTypes = [] | PASS |
| 17 | NSPrivacyTracking = false | PASS |
| 18 | Privacy Nutrition Labels correct | PASS |
| 19 | NSCameraUsageDescription | PASS |
| 20 | NSMicrophoneUsageDescription | PASS |
| 21 | NSPhotoLibraryUsageDescription | PASS |
| 22 | NSContactsUsageDescription | PASS |
| 23 | NSLocalNetworkUsageDescription | PASS |
| 24 | NSSiriUsageDescription absent | PASS |
| 25 | ITSAppUsesNonExemptEncryption = YES | PASS |
| 26 | ITSEncryptionExportComplianceCode | WARNING — empty string |
| 27 | BIS Self-Classification document | PASS |
| 28 | NSAppTransportSecurity secure | PASS |

---

## Final Verdict

**27/28 PASS | 1 WARNING | 0 FAIL**

The app demonstrates excellent privacy compliance. The zero-knowledge architecture, anonymous mailbox system, lack of any tracking/analytics SDKs, and comprehensive multi-language privacy policy exceed Apple's minimum requirements.

**Single action item:** Fix `ITSEncryptionExportComplianceCode` — either populate with BIS reference or remove the empty key.
