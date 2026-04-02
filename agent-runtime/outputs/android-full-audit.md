# QRChat Android — Full Audit Report

**Date:** 2026-03-23
**Auditor:** QA Engineer
**Project:** /Users/ruslanconstantinovici/QRChat-Android
**Version:** 4.2.0 (versionCode 43)

---

## Executive Summary

| Category | Status | Issues |
|----------|--------|--------|
| TypeScript | FAIL | 2 errors in FCMService.ts |
| Jest Tests | PASS | 9/9 pass (with async teardown warnings) |
| AndroidManifest.xml | PASS | All 12 required permissions present |
| build.gradle | PASS | All config values correct |
| Native Android Modules | PASS | All 3 modules present + registered |
| Firebase | PARTIAL | Placeholder google-services.json, missing background handler |
| Code Review | ISSUES | 5 Android-specific issues found |
| Version Sync | PASS | 4.2.0 in all 3 locations |
| Potential Problems | CRITICAL | 4 critical, 2 high, 2 medium issues |

**Overall verdict: NOT READY for Play Store submission** — 4 critical blockers must be resolved first.

---

## 1. TypeScript Check — `npx tsc --noEmit`

**Result: FAIL — 2 errors**

Both errors are in `src/services/FCMService.ts`:

| Line | Error | Description |
|------|-------|-------------|
| 70 | TS2345 | `remoteMessage.data` (`Record<string, string \| number \| object>`) is not assignable to `Record<string, string>` |
| 103 | TS2345 | Same type mismatch when passing `data` to `showIncomingCallNotification()` |

**Fix:** Cast `data` explicitly or change parameter type to accept broader types:
```typescript
await this.showIncomingCallNotification(data as Record<string, string>);
```

---

## 2. Jest Tests — `npx jest --no-cache`

**Result: PASS — 9/9 tests, 3/3 suites**

| Metric | Value |
|--------|-------|
| Test Suites | 3 passed |
| Tests | 9 passed |
| Snapshots | 0 |
| Time | 7.607s |

**Warnings (non-blocking):**
- `IAPService.ts:289` — "Cannot log after tests are done" — async teardown leak in `IAPService.destroy()`
- `TypeError: window.dispatchEvent is not a function` — react-test-renderer attempting browser API in RN context
- Worker process force-exited (likely caused by above)

**Recommendation:** Add proper cleanup in IAPService test (await destroy before test ends).

---

## 3. AndroidManifest.xml — Permissions Audit

**Result: PASS — ALL 12 required permissions present**

| Permission | Present |
|-----------|---------|
| INTERNET | YES |
| CAMERA | YES |
| RECORD_AUDIO | YES |
| VIBRATE | YES |
| READ_CONTACTS | YES |
| WRITE_EXTERNAL_STORAGE | YES |
| READ_EXTERNAL_STORAGE | YES |
| READ_MEDIA_IMAGES | YES |
| POST_NOTIFICATIONS | YES |
| USE_FULL_SCREEN_INTENT | YES |
| FOREGROUND_SERVICE | YES |
| WAKE_LOCK | YES |

**Additional manifest features:**
- `showWhenLocked="true"` and `turnScreenOn="true"` on MainActivity (for incoming calls)
- `launchMode="singleTask"` (prevents duplicate activities)
- `usesCleartextTraffic` from build config (dev/prod toggle)

**Note:** Permissions are declared but NEVER requested at runtime — see Critical Issue #1 below.

---

## 4. build.gradle — Configuration Audit

**Result: PASS — All values correct**

| Setting | Expected | Actual | Status |
|---------|----------|--------|--------|
| applicationId | com.ruslan.qrchat | com.ruslan.qrchat | PASS |
| versionName | 4.2.0 | 4.2.0 | PASS |
| versionCode | 43 | 43 | PASS |
| google-services plugin | present | `apply plugin: "com.google.gms.google-services"` | PASS |
| Signing config (release) | keystore.properties | keystore.properties loaded | PASS |
| compileSdk | 36 | 36 | PASS |
| targetSdkVersion | 36 | 36 | PASS |
| minSdkVersion | 24 | 24 | PASS |
| Kotlin version | - | 2.1.20 | OK |
| google-services classpath | - | 4.4.2 | OK |

---

## 5. Native Android Modules — Audit

**Result: PASS — All modules present and registered**

### Files verified:

| File | Path | Status |
|------|------|--------|
| SystemSoundModule.kt | `android/app/src/main/java/com/qrchat/` | EXISTS |
| SystemSoundPackage.kt | `android/app/src/main/java/com/qrchat/` | EXISTS |
| AudioManagerModule.kt | `android/app/src/main/java/com/qrchat/` | EXISTS |
| MainApplication.kt | `android/app/src/main/java/com/qrchat/` | EXISTS |
| MainActivity.kt | `android/app/src/main/java/com/qrchat/` | EXISTS |

### Registration chain:

1. `MainApplication.kt` line 18: `add(SystemSoundPackage())`
2. `SystemSoundPackage.kt` lines 10-12: registers `SystemSoundModule` + `AudioManagerModule`
3. Both modules expose `@ReactMethod` annotations for JS bridge

### Module capabilities:

| Module | Methods | Purpose |
|--------|---------|---------|
| SystemSoundModule | `playSystemSound(soundId)`, `playAudioFileLoop(path)`, `stopLoop()` | Notification sounds, ringtone loop |
| AudioManagerModule | `setSpeakerOn(enabled)`, `setEarpiece()` | Speaker/earpiece toggle during calls |

---

## 6. Firebase — Configuration Audit

**Result: PARTIAL — 2 critical issues**

### google-services.json

**Status: PLACEHOLDER — NOT a real Firebase config**

File at `android/app/google-services.json` contains template values:
- `project_number: "REPLACE_WITH_YOUR_PROJECT_NUMBER"`
- `project_id: "REPLACE_WITH_YOUR_PROJECT_ID"`
- `current_key: "REPLACE_WITH_YOUR_API_KEY"`
- `package_name: "com.ruslan.qrchat"` (correct)

**Impact: Firebase will NOT initialize. FCM push notifications WILL NOT WORK.**

### Package dependencies

| Package | Version | Status |
|---------|---------|--------|
| @react-native-firebase/app | ^23.8.8 | PRESENT |
| @react-native-firebase/messaging | ^23.8.8 | PRESENT |
| @notifee/react-native | ^9.1.8 | PRESENT |

### FCMService.ts

- EXISTS at `src/services/FCMService.ts`
- Well-structured: token registration, channel creation, incoming call notification
- Imported in App.tsx (assumed)
- Has proper Platform.OS guard (`if (Platform.OS !== 'android') return`)

### MISSING: Background Message Handler

**`index.js` does NOT register `messaging().setBackgroundMessageHandler()`.**

Current index.js:
```javascript
import { AppRegistry } from 'react-native';
import App from './App';
import { name as appName } from './app.json';
AppRegistry.registerComponent(appName, () => App);
```

**Impact: When app is killed/background, incoming FCM messages (calls, new messages) will NOT be processed. Full-screen incoming call notification will NOT display.**

**Fix required:**
```javascript
import messaging from '@react-native-firebase/messaging';
messaging().setBackgroundMessageHandler(async (remoteMessage) => {
  // Handle background FCM
});
```

---

## 7. Code Review — Key Screens and Services

### CallScreen.tsx

| Feature | Status | Notes |
|---------|--------|-------|
| Speaker toggle | PASS | Uses `AudioManagerModule.setSpeakerOn()` with Platform.OS check (line 254) |
| Ringback tone | PASS | Uses `InCallManager.startRingback('_BUNDLE_')` when status is 'ringing' (line 88) |
| 60s timeout | PASS | Auto-ends unanswered call after 60s (line 204) |
| Stream cleanup | PASS | Stops local tracks on end (lines 114-117, 146-148) |
| InCallManager cleanup | PASS | Stops ringback + InCallManager in finishAndGoBack() |

### NotificationService.ts

| Feature | Status | Notes |
|---------|--------|-------|
| isPlayingCallSound guard | PASS | Line 126: `if (this.isPlayingCallSound) return;` prevents double-play |
| Muted contact check | PASS | Checks `contact?.isMuted` before playing sound |
| Sound suppression | PASS | Notifee notification has NO sound — SystemSoundModule handles it |
| Lazy-load notifee | PASS | Safe try/catch for missing native module |

### ChatScreen.tsx

| Feature | Status | Notes |
|---------|--------|-------|
| Save image | PASS | Uses `Share.share()` which works cross-platform |
| Voice recording | **FAIL** | No `PermissionsAndroid.request(RECORD_AUDIO)` before `startRecording()` (line 863) |
| File handling | PASS | Uses RNFS consistently for file operations |

### HomeScreen.tsx

| Feature | Status | Notes |
|---------|--------|-------|
| ErrorBoundary on tabs | **MISSING** | Tabs render PhoneContactsScreen and CallLogScreen directly without ErrorBoundary wrapper (lines 618-628) |
| ErrorBoundary component | EXISTS | `src/components/ErrorBoundary.tsx` exists but is not used in HomeScreen |

### PhoneContactsScreen.tsx

| Feature | Status | Notes |
|---------|--------|-------|
| Android contacts permission | **FAIL** | Imports `PermissionsAndroid` but NEVER calls `.request()` — relies on iOS auto-permission flow |
| SMS invite URL | **FAIL** | Uses `sms:${phone}&body=${message}` — iOS format. Android needs `?body=` separator |
| Settings deep-link | **PARTIAL** | Line 83: `Linking.openURL('app-settings:')` is iOS-only; Line 175: `Linking.openSettings()` is correct |

---

## 8. Version Sync Check

**Result: PASS — All 3 locations show 4.2.0**

| Location | Version | Status |
|----------|---------|--------|
| package.json | "4.2.0" | PASS |
| src/utils/version.ts | '4.2.0' | PASS |
| android/app/build.gradle | versionName "4.2.0", versionCode 43 | PASS |

---

## 9. Potential Problems — Full Scan

### CRITICAL (Must fix before release)

#### C1. No Runtime Permission Requests (PermissionsAndroid)

**`PermissionsAndroid.request()` is NEVER called anywhere in the src/ directory.**

On Android 6.0+ (API 23+), these permissions MUST be requested at runtime even if declared in AndroidManifest:
- `RECORD_AUDIO` — voice recording in ChatScreen will silently fail or crash
- `READ_CONTACTS` — PhoneContactsScreen will fail on Android (works on iOS because it auto-prompts)
- `CAMERA` — QR scanning and video calls will fail

**Impact: Core features (voice messages, contacts, camera) will not work on Android.**

#### C2. keystore.properties Not in .gitignore

File `android/keystore.properties` contains plaintext signing credentials:
```
storePassword=QRChat2026Release
keyPassword=QRChat2026Release
```

This file is NOT listed in `.gitignore` and will be committed to version control.

**Impact: Security vulnerability — signing keys exposed in repo.**

#### C3. google-services.json is Placeholder

All Firebase values are `REPLACE_WITH_*` templates. Firebase SDK will crash or fail silently on initialization.

**Impact: No push notifications, no FCM, no incoming call notifications when app is backgrounded/killed.**

#### C4. Missing setBackgroundMessageHandler

`index.js` does not register a background FCM handler. Even with real google-services.json, background push processing won't work.

**Impact: No incoming calls/messages when app is killed.**

### HIGH (Should fix before release)

#### H1. SMS URL Format — iOS-Only Separator

`PhoneContactsScreen.tsx:118`:
```typescript
const url = `sms:${contact.phone}&body=${message}`;
```

On Android, the correct format is `sms:${phone}?body=${encodeURIComponent(message)}`.

**Fix:**
```typescript
const separator = Platform.OS === 'ios' ? '&' : '?';
const url = `sms:${contact.phone}${separator}body=${encodeURIComponent(message)}`;
```

#### H2. iOS-Only Deep Link in Alert

`PhoneContactsScreen.tsx:83`:
```typescript
Linking.openURL('app-settings:')
```

`app-settings:` is an iOS URL scheme. On Android this will fail silently or throw. Should use `Linking.openSettings()` (which is already used on line 175).

### MEDIUM

#### M1. No ErrorBoundary on HomeScreen Tabs

`HomeScreen.tsx` renders `PhoneContactsScreen` and `CallLogScreen` directly (lines 618-628) without wrapping in the existing `ErrorBoundary` component. A crash in either tab will crash the entire app.

#### M2. CallKitService iOS-Only Guard

`CallKitService.ts:32` has `if (Platform.OS !== 'ios') return;` — the service is completely disabled on Android. While Android uses FCMService + Notifee for incoming calls, there's no ConnectionService integration for native Android call UI.

### LOW

#### L1. TypeScript Errors in FCMService.ts

2 type errors related to `Record<string, string>` vs broader data types. Non-blocking but should be fixed for clean builds.

#### L2. Jest Async Teardown Warning

IAPService.destroy() leaks async operations after test completion. Should add proper cleanup.

---

## Action Items — Priority Order

| # | Priority | Issue | Owner | Effort |
|---|----------|-------|-------|--------|
| 1 | CRITICAL | Add PermissionsAndroid.request() for RECORD_AUDIO, READ_CONTACTS, CAMERA | frontend-engineer | 2h |
| 2 | CRITICAL | Add keystore.properties to .gitignore + rotate credentials | release-engineer | 30m |
| 3 | CRITICAL | Replace google-services.json with real Firebase config | backend-engineer | 1h |
| 4 | CRITICAL | Add setBackgroundMessageHandler in index.js | backend-engineer | 1h |
| 5 | HIGH | Fix SMS URL format for Android (Platform.OS check) | frontend-engineer | 15m |
| 6 | HIGH | Fix iOS-only app-settings: deep link | frontend-engineer | 15m |
| 7 | MEDIUM | Wrap HomeScreen tabs with ErrorBoundary | frontend-engineer | 30m |
| 8 | MEDIUM | Consider ConnectionService for Android incoming calls | network-engineer | 4h |
| 9 | LOW | Fix TypeScript errors in FCMService.ts | backend-engineer | 15m |
| 10 | LOW | Fix IAPService test async teardown | qa-engineer | 30m |

---

## Files Audited

```
android/app/src/main/AndroidManifest.xml
android/app/build.gradle
android/build.gradle
android/app/google-services.json
android/keystore.properties
android/app/src/main/java/com/qrchat/MainApplication.kt
android/app/src/main/java/com/qrchat/SystemSoundModule.kt
android/app/src/main/java/com/qrchat/SystemSoundPackage.kt
android/app/src/main/java/com/qrchat/AudioManagerModule.kt
src/services/FCMService.ts
src/services/NotificationService.ts
src/services/CallKitService.ts
src/screens/CallScreen.tsx
src/screens/ChatScreen.tsx
src/screens/HomeScreen.tsx
src/screens/PhoneContactsScreen.tsx
src/components/ErrorBoundary.tsx
src/utils/version.ts
package.json
index.js
.gitignore
```

---

*Report generated by QA Engineer agent — 2026-03-23*
