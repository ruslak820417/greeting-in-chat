# Apple App Store Review — Section 2: PERFORMANCE

**App:** QRChat v4.0.0 (build 16)
**Auditor:** QA Engineer (Apple Guidelines Specialist)
**Date:** 2026-03-22
**Verdict:** FAIL — 4 blocking issues, 3 warnings

---

## 2.1 App Completeness

### [PASS] App is complete and functional
- 21 screens implemented: HomeScreen, ChatScreen, CallScreen, CallLogScreen, ContactsScreen, ContactProfileScreen, CreateGroupScreen, GroupInfoScreen, MediaFilesScreen, PendingApprovalScreen, PhoneContactsScreen, ProfileScreen, QRGenerateScreen, QRScanScreen, SettingsScreen, SetupScreen, SupportScreen, TermsScreen, ThemeEditorScreen, UpgradeScreen, WelcomeScreen
- Core messaging, calling, QR exchange, and settings all functional

### [FAIL] StoreKit 2 placeholder — incomplete purchase flow
- **File:** `src/screens/UpgradeScreen.tsx:57-63`
- `handlePurchase()` shows alert: "purchaseNotReady" — this is a dead-end button
- **File:** `src/services/LicensingService.ts:124-126`
- `activateWithReceipt()` returns hardcoded `{ success: false, message: 'In-App Purchase not yet available' }`
- **Risk:** Apple will reject for incomplete functionality (Guideline 2.1). If you offer a purchase button, it must work. Either remove the IAP button entirely or implement StoreKit 2.

### [PASS] No "Coming Soon" UI text visible
- The "placeholder" references in code are UI layout spacers (QRGenerateScreen, QRScanScreen), not feature placeholders — acceptable.

### [PASS] Tests pass
```
Test Suites: 3 passed, 3 total
Tests:       9 passed, 9 total
Time:        9.892 s
```
- Warning: Worker process force-exited (timer leak) — not blocking but should be fixed.

### [PASS] TypeScript compiles clean
- `npx tsc --noEmit` returned zero errors.

---

## 2.2 Beta Testing

### [PASS] Not marked as beta/preview
- No "beta", "preview", or "early access" labels in UI or metadata.

### [WARNING] TestFlight reference in documentation
- **File:** `PROJECT_STATUS.md:170` mentions "Export IPA + Upload TestFlight"
- This is internal documentation only, not shipped in the app binary — not blocking but ensure no TestFlight-specific code paths exist in the build.

### [PASS] No TestFlight-specific code
- No TestFlight APIs, beta entitlements, or conditional beta code found in source.

---

## 2.3 Accurate Metadata

### [PASS] Description reflects the actual app
- APP_STORE_METADATA.md describes: encrypted messaging, QR code exchange, voice/video calls, self-destructing messages, themes, multi-language — all implemented.

### [FAIL] Screenshots are NOT App Store ready
**Both existing screenshots (`screen1.png` and `appstore/current.png`) will cause IMMEDIATE REJECTION:**

1. **"Fast Refresh disconnected. Reload app to reconnect."** — Debug development banner visible at the top of the screen
2. **"Open debugger to view warnings."** — Debug warning bar visible at the bottom of the screen
3. **Dynamic Island area blacked out** — the notch/pill area is censored with a black rectangle
4. Screenshots taken during development (Metro bundler connected), not from a release build
5. Only 1 screenshot available — Apple requires **minimum 3 screenshots** per device size
6. Only one device size captured — need screenshots for at minimum:
   - 6.7" (iPhone 15 Pro Max / 16 Pro Max): 1290 x 2796 px
   - 6.5" (iPhone 11 Pro Max): 1284 x 2778 px
   - 5.5" (iPhone 8 Plus): 1242 x 2208 px
7. Screenshots show mostly empty UI (only 1 contact) — not compelling for the store listing

**Action required:** Take fresh screenshots from a RELEASE build with populated demo data across all required device sizes. Show at minimum: chat conversation, QR code, contacts list, call screen, settings.

### [PASS] Keywords are relevant and non-abusive
- `private,messenger,encrypted,e2e,qr,secure,chat,calls,privacy,anonymous`
- 72 characters (under 100 limit). Relevant to the app. No competitor names or misleading terms.

### [PASS] Category is correct
- Primary: Social Networking — correct for a messenger app.
- Secondary: Utilities — acceptable.

### [PASS] Age rating 17+ is correct
- 17+ for Frequent/Intense User Generated Content — appropriate for an unmoderated encrypted messenger.

### [WARNING] Version mismatch
- `project.pbxproj` MARKETING_VERSION = **4.0.0**
- `package.json` version = **4.1.0**
- APP_STORE_METADATA.md "What's New" says **4.0.0**
- Ensure these are aligned before submission.

---

## 2.4 Hardware Compatibility

### [PASS] iPad correctly excluded
```
TARGETED_DEVICE_FAMILY = 1  (both Debug and Release)
```
- Value `1` = iPhone only. iPad is excluded. Correct.

### [PASS] Orientation locked to Portrait
```xml
<key>UISupportedInterfaceOrientations</key>
<array>
    <string>UIInterfaceOrientationPortrait</string>
</array>
```
- Portrait only — consistent with a messaging app.

### [PASS] Device capabilities reasonable
```xml
<key>UIRequiredDeviceCapabilities</key>
<array>
    <string>arm64</string>
</array>
```
- Requires arm64 (iPhone 5s and later) — reasonable since deployment target is iOS 15.1.

---

## 2.5 Software Requirements

### [PASS] iOS minimum deployment target is reasonable
- `IPHONEOS_DEPLOYMENT_TARGET = 15.1` — iOS 15.1 covers iPhone 6s and later.
- As of March 2026, iOS 15 still covers a wide installed base. Acceptable.

### [PASS] No deprecated iOS APIs detected
- No UIWebView, UIAlertView, UIActionSheet, or ABAddressBook references in native code.
- React Native 0.84.0 uses modern APIs.

### [PASS] No private APIs detected
- No usage of private frameworks, dlopen/dlsym for private symbols, or underscore-prefixed private selectors in native code.

### [WARNING] App Transport Security
- ATS is correctly configured with `NSAllowsArbitraryLoads = false` — good.
- However, verify the relay server uses TLS 1.2+ (required by ATS).

---

## Summary

| Section | Status | Details |
|---------|--------|---------|
| 2.1 Completeness | FAIL | StoreKit 2 purchase button is a dead end |
| 2.2 Beta Testing | PASS | No beta markers in shipping code |
| 2.3 Metadata | FAIL | Screenshots show debug UI, only 1 screenshot, wrong sizes |
| 2.4 Hardware | PASS | iPhone-only, Portrait, arm64 — all correct |
| 2.5 Software | PASS | iOS 15.1 target, no deprecated/private APIs |

## Blocking Issues (must fix before submission)

| # | Priority | Issue | Action |
|---|----------|-------|--------|
| 1 | CRITICAL | Screenshots show debug banners ("Fast Refresh disconnected", "Open debugger") | Retake all screenshots from RELEASE build |
| 2 | CRITICAL | Only 1 screenshot exists; Apple requires minimum 3 per device size | Create 3-6 screenshots across required device sizes |
| 3 | HIGH | UpgradeScreen purchase button shows "not ready" alert | Either implement StoreKit 2 or remove the IAP button entirely |
| 4 | HIGH | Version mismatch: pbxproj=4.0.0, package.json=4.1.0 | Align all version references |

## Warnings (recommended fixes)

| # | Issue | Action |
|---|-------|--------|
| 1 | Jest worker force-exit (timer leak) | Add proper teardown in tests |
| 2 | TestFlight mentioned in PROJECT_STATUS.md | Internal only — no action needed |
| 3 | Verify relay server TLS 1.2+ compliance | Test with `nscurl --ats-diagnostics` |
