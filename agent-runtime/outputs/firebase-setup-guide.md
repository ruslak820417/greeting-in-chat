# Firebase Cloud Messaging (FCM) Setup Guide

## Overview

QRChat uses Firebase Cloud Messaging to wake the Android app from background/killed state when an incoming call arrives. On iOS, CallKit handles this natively. On Android, FCM high-priority data messages trigger a full-screen notification with Answer/Decline buttons.

## What's Already Done (Code)

### Client-side (QRChat-Android)
- `@react-native-firebase/app` and `@react-native-firebase/messaging` installed
- `android/build.gradle` — google-services plugin added
- `android/app/build.gradle` — google-services plugin applied
- `android/app/google-services.json` — placeholder (needs replacement)
- `AndroidManifest.xml` — permissions added (POST_NOTIFICATIONS, USE_FULL_SCREEN_INTENT, FOREGROUND_SERVICE, WAKE_LOCK)
- `src/services/FCMService.ts` — handles token registration, foreground/background messages, full-screen call notification
- `src/services/PushTokenService.ts` — updated to send platform='android' for FCM tokens
- `index.js` — background message handler registered before AppRegistry
- `App.tsx` — FCM initialized on startup, Answer/Decline event handlers wired

### Server-side (QRChat/server)
- `firebase-admin` installed
- `push.js` — `sendAndroidPush()` and `sendPush()` functions added
- `index.js` — sends FCM push when call offer goes to offline Android user
- `firebase-service-account.json.example` — template for service account key

---

## Steps for the User

### Step 1: Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Add project"
3. Name it `qrchat` (or any name)
4. Disable Google Analytics (optional, not needed)
5. Click "Create project"

### Step 2: Register Android App

1. In the Firebase project, click the Android icon to add an app
2. Package name: `com.ruslan.qrchat`
3. App nickname: `QRChat`
4. Skip the SHA-1 for now (needed later for production)
5. Click "Register app"

### Step 3: Download google-services.json

1. Download the `google-services.json` file
2. Replace the placeholder at: `QRChat-Android/android/app/google-services.json`
3. This file is gitignored — keep it private

### Step 4: Generate Server Key (Service Account)

1. In Firebase Console, go to Project Settings > Service accounts
2. Click "Generate new private key"
3. Download the JSON file
4. Rename it to `firebase-service-account.json`
5. Place it in `QRChat/server/firebase-service-account.json`

**OR** use environment variables (recommended for Railway):

### Step 5: Configure Railway Environment Variables

Add these env vars to your Railway deployment:

```
FCM_PROJECT_ID=your-firebase-project-id
FCM_CLIENT_EMAIL=firebase-adminsdk-xxxxx@your-project.iam.gserviceaccount.com
FCM_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n"
```

The private key must include the `\n` escape sequences for newlines.

### Step 6: Rebuild Android App

```bash
cd QRChat-Android
cd android && ./gradlew clean && cd ..
npx react-native run-android
```

### Step 7: Verify

1. Open QRChat on Android device
2. Check logs for: `[FCMService] Initialized` and `[FCMService] FCM token: ...`
3. On server logs, check for: `[Push] FCM (Firebase Admin) initialized`
4. Test: put Android app in background, call from another device
5. Expected: full-screen notification appears with Answer/Decline buttons

---

## Architecture

```
Caller (iOS/Android)
  │
  ▼
Server (offer to offline recipient)
  │
  ├── iOS → APNs silent push → CallKit wakes app
  │
  └── Android → FCM high-priority data message
                  │
                  ▼
              Background handler (index.js)
                  │
                  ▼
              FCMService.handleMessage()
                  │
                  ▼
              Notifee full-screen notification
              [Answer] [Decline]
                  │
                  ▼
              EventBus → App.tsx → navigate to Call screen
```

## Security Notes

- FCM data payload contains only: type, from (senderId), callerName, isVideo, offer
- No message content is ever sent via push
- Push tokens are registered via anonymous mailbox IDs (same as APNs)
- Service account key must never be committed to git

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "FCM not configured" in server logs | Set FCM_PROJECT_ID env var |
| No notification on Android | Check POST_NOTIFICATIONS permission granted |
| Notification appears but doesn't wake screen | Check USE_FULL_SCREEN_INTENT permission and showWhenLocked in AndroidManifest |
| Token registration fails | Verify google-services.json is correct and matches package name |
| Build fails with google-services error | Run `cd android && ./gradlew clean` and rebuild |
