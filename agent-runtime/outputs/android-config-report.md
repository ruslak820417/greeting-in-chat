# Android Configuration Audit Report — QRChat-Android

**Date:** 2026-03-22
**Auditor:** qa-engineer
**Project:** /Users/ruslanconstantinovici/QRChat-Android

---

## 1. package.json

| Check | Status | Notes |
|-------|--------|-------|
| Version | OK | 4.1.0 — matches iOS |
| Native dependencies | OK | All major deps (react-native-webrtc, react-native-camera-kit, react-native-contacts, react-native-callkeep, react-native-iap, react-native-keychain, op-sqlite, notifee) have Android support |
| React Native version | OK | 0.84.0 |
| Node engine | OK | >= 22.11.0 |

---

## 2. android/app/build.gradle

| Check | Status | Value | Expected |
|-------|--------|-------|----------|
| applicationId | FAIL | `com.qrchat` | `com.ruslan.qrchat` |
| namespace | FAIL | `com.qrchat` | `com.ruslan.qrchat` |
| versionName | FAIL | `1.0` | `4.1.0` |
| versionCode | FAIL | `1` | `17` (to match iOS build) |
| minSdkVersion | OK | 24 (via rootProject) | — |
| targetSdkVersion | OK | 36 (via rootProject) | — |
| compileSdkVersion | OK | 36 (via rootProject) | — |
| Signing (debug) | OK | debug.keystore | — |
| Signing (release) | WARN | Uses debug keystore | Needs production keystore for Play Store |
| ProGuard | OK | Disabled (fine for now) | — |

### Critical Issues:
1. **applicationId** is `com.qrchat` — must be `com.ruslan.qrchat` to match iOS bundle ID
2. **versionName** is `1.0` — must be `4.1.0`
3. **versionCode** is `1` — should be `17` to stay in sync with iOS
4. **Release signing** uses debug keystore — will be rejected by Play Store

---

## 3. android/build.gradle (root)

| Check | Status | Value |
|-------|--------|-------|
| Gradle Plugin | OK | com.android.tools.build:gradle (version-less, resolved by Gradle) |
| Kotlin | OK | 2.1.20 |
| buildToolsVersion | OK | 36.0.0 |
| compileSdkVersion | OK | 36 |
| minSdkVersion | OK | 24 (Android 7.0) |
| targetSdkVersion | OK | 36 |
| ndkVersion | OK | 27.1.12297006 |
| Repositories | OK | google(), mavenCentral() |
| Gradle wrapper | OK | 9.0.0 |

No issues.

---

## 4. gradle.properties

| Property | Status | Value |
|----------|--------|-------|
| newArchEnabled | OK | true |
| hermesEnabled | OK | true |
| android.useAndroidX | OK | true |
| reactNativeArchitectures | OK | armeabi-v7a,arm64-v8a,x86,x86_64 |
| JVM args | OK | -Xmx2048m -XX:MaxMetaspaceSize=512m |
| edgeToEdgeEnabled | OK | false |

No issues.

---

## 5. AndroidManifest.xml

| Permission | Status | Notes |
|------------|--------|-------|
| INTERNET | OK | Present |
| CAMERA | MISSING | Required for QR scanning + media |
| RECORD_AUDIO | MISSING | Required for calls (WebRTC) |
| READ_EXTERNAL_STORAGE | MISSING | Required for file sharing |
| WRITE_EXTERNAL_STORAGE | MISSING | Required for file saving |
| VIBRATE | MISSING | Required for notifications |
| READ_CONTACTS | MISSING | Required for contact sync |
| FOREGROUND_SERVICE | MISSING | Likely needed for calls + notifications |
| BLUETOOTH | MISSING | Needed for WebRTC audio routing |

### Note:
Some libraries (react-native-webrtc, react-native-contacts, notifee) may inject permissions via manifest merging, but explicit declaration is safer and more predictable. Need to verify merged manifest after build.

---

## 6. Versioning Sync (iOS vs Android)

| Field | iOS | Android | Match? |
|-------|-----|---------|--------|
| Marketing version | 4.1.0 | 1.0 | NO |
| Build number | 17 | 1 | NO |
| package.json | 4.1.0 | 4.1.0 | OK |

**Action needed:** Update `versionName` to `4.1.0` and `versionCode` to `17` in `android/app/build.gradle`.

---

## 7. App Icons

| Density | File | Size | Status |
|---------|------|------|--------|
| mdpi | ic_launcher.png | 48x48 | OK |
| hdpi | ic_launcher.png | 72x72 | OK |
| xhdpi | ic_launcher.png | 96x96 | OK |
| xxhdpi | ic_launcher.png | 144x144 | OK |
| xxxhdpi | ic_launcher.png | 192x192 | OK |

- Both `ic_launcher` and `ic_launcher_round` present in all 5 densities
- Visual: Orange chat bubble with QR code — matches the new QRChat logo
- **No adaptive icon** (ic_launcher_foreground/background) — recommended for Android 8+ but not blocking

---

## Summary

### CRITICAL (must fix before release):
1. `applicationId` / `namespace`: Change `com.qrchat` -> `com.ruslan.qrchat`
2. `versionName`: Change `1.0` -> `4.1.0`
3. `versionCode`: Change `1` -> `17`
4. AndroidManifest.xml: Add missing permissions (CAMERA, RECORD_AUDIO, VIBRATE, READ_CONTACTS, storage)
5. Release signing config: Generate production keystore

### WARNINGS:
1. No adaptive icon (Android 8+ feature)
2. Manifest permissions may partially come from library merging — verify after build

### PASSED:
1. package.json dependencies all have Android support
2. Gradle config (root build.gradle, gradle.properties) is correct
3. New Architecture enabled, Hermes enabled, AndroidX enabled
4. App icons are present in all densities with correct sizes and new logo
5. Gradle 9.0.0, Kotlin 2.1.20, compileSdk 36 — all up to date
