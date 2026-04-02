# Mobile App Invite Link System — Technical Research Report

**Date:** 2026-03-24
**Target:** QRChat v4.3.0 (React Native 0.84, iOS + Android)
**Bundle ID (iOS):** com.qrchat
**Application ID (Android):** com.qrchat
**Server:** exciting-success-production-d272.up.railway.app

---

## Table of Contents

1. [iOS Universal Links (AASA)](#1-ios-universal-links)
2. [Android App Links (assetlinks.json)](#2-android-app-links)
3. [Deep Linking in React Native](#3-deep-linking-in-react-native)
4. [How Popular Messengers Handle Invite Links](#4-how-popular-messengers-handle-invite-links)
5. [Deferred Deep Linking](#5-deferred-deep-linking)
6. [Security Considerations for E2E Encrypted Messengers](#6-security-considerations)
7. [Recommendations for QRChat](#7-recommendations-for-qrchat)

---

## 1. iOS Universal Links

### How They Work

Universal Links are standard `https://` URLs that seamlessly open your app when installed, or fall back to Safari when not. When a user taps a Universal Link, iOS checks if the domain has an associated app by reading the Apple App Site Association (AASA) file from Apple's CDN (not your server directly — Apple caches it).

**Flow:**
1. App installed → Xcode downloads AASA from Apple CDN at install time
2. User taps `https://qrchat.app/invite/abc123`
3. iOS matches the URL against cached AASA rules
4. If matched → app opens, `continueUserActivity` fires
5. If not matched or app not installed → Safari opens the URL

### AASA File Setup

The file must be hosted at **one** of these paths (no redirect allowed):
- `https://qrchat.app/.well-known/apple-app-site-association`
- `https://qrchat.app/apple-app-site-association`

**Requirements:**
- Served over HTTPS (no redirects — this is the #1 pitfall)
- Content-Type: `application/json`
- No `.json` extension on the filename
- Maximum 128 KB uncompressed
- Must NOT be blocked by Cloudflare, WAF, or bot protection

**Modern format (iOS 13+, recommended):**

```json
{
  "applinks": {
    "details": [
      {
        "appIDs": [
          "TEAMID.com.qrchat"
        ],
        "components": [
          {
            "/": "/invite/*",
            "comment": "Invite links open in app"
          },
          {
            "/": "/join/*",
            "comment": "Group join links"
          },
          {
            "/": "/verify/*",
            "comment": "Key verification links"
          },
          {
            "/": "/privacy*",
            "exclude": true,
            "comment": "Privacy policy stays in browser"
          },
          {
            "/": "/faq*",
            "exclude": true,
            "comment": "FAQ stays in browser"
          }
        ]
      }
    ]
  }
}
```

**Legacy format (iOS 9-12 compatibility):**

```json
{
  "applinks": {
    "apps": [],
    "details": [
      {
        "appID": "TEAMID.com.qrchat",
        "paths": [
          "/invite/*",
          "/join/*",
          "/verify/*",
          "NOT /privacy*",
          "NOT /faq*"
        ]
      }
    ]
  }
}
```

**Best practice:** Include BOTH formats in the same file for maximum compatibility.

### Xcode Configuration (QRChat-Specific)

Current entitlements (`QRChat.entitlements`) need a new key:

```xml
<key>com.apple.developer.associated-domains</key>
<array>
    <string>applinks:qrchat.app</string>
    <string>applinks:qrchat.app?mode=developer</string>
</array>
```

The `?mode=developer` variant bypasses CDN caching during development (iOS 14+).

### AppDelegate Changes Needed

QRChat's `AppDelegate.swift` already has `continueUserActivity` for CallKit, but it does NOT forward to `RCTLinkingManager`. This must be fixed:

```swift
func application(
    _ application: UIApplication,
    continue userActivity: NSUserActivity,
    restorationHandler: @escaping ([UIUserActivityRestoring]?) -> Void
) -> Bool {
    // Forward universal links to React Native FIRST
    if userActivity.activityType == NSUserActivityTypeBrowsingWeb {
        return RCTLinkingManager.application(
            application,
            continue: userActivity,
            restorationHandler: restorationHandler
        )
    }

    // Then handle CallKit (existing code)
    if let callKeepClass = NSClassFromString("RNCallKeep") as? NSObject.Type {
        let sel = NSSelectorFromString("application:continueUserActivity:restorationHandler:")
        if callKeepClass.responds(to: sel) {
            _ = callKeepClass.perform(sel, with: application, with: userActivity)
        }
    }
    return true
}
```

You also need to import RCTLinkingManager:
```swift
import React  // already present
// RCTLinkingManager is auto-linked via React Native 0.84
```

### Common Pitfalls

1. **CDN Caching:** Apple's CDN fetches your AASA at install time and re-checks ~once per week. During development, use `?mode=developer` or reinstall the app to force re-fetch.
2. **Redirects kill Universal Links:** If `qrchat.app/.well-known/apple-app-site-association` returns a 301/302, it WILL NOT WORK.
3. **Social media in-app browsers:** Facebook, Instagram, Twitter, TikTok open links in their own WebViews — Universal Links do NOT fire there. This affects invite link sharing on social platforms.
4. **Same-domain navigation:** If the user is already on `qrchat.app` in Safari and taps a link to `qrchat.app/invite/x`, the link opens in Safari (not the app). Universal Links only work for cross-domain navigation.
5. **Cloudflare/WAF blocking:** Bot protection can block Apple's CDN from fetching AASA. Whitelist Apple's CDN IPs or the User-Agent.
6. **JavaScript redirects don't trigger Universal Links:** Only direct taps on `<a href>` work.

### Validation

- Use https://getuniversal.link/ to validate your AASA file
- Apple's `swcutil` CLI: `swcutil dl -d qrchat.app`
- iOS 18+ Developer Settings → Universal Links diagnostics

---

## 2. Android App Links

### How They Work

Android App Links are verified `https://` intents. When `android:autoVerify="true"` is set, Android downloads `assetlinks.json` from your domain at install time and verifies the SHA-256 fingerprint matches your signing key.

**Flow:**
1. App installed → Android verifies assetlinks.json
2. User taps `https://qrchat.app/invite/abc123`
3. If verified → app opens directly (no disambiguation dialog)
4. If not verified → browser opens (or disambiguation dialog)

### assetlinks.json Setup

Must be hosted at:
```
https://qrchat.app/.well-known/assetlinks.json
```

**Requirements:**
- Served over HTTPS (no redirects)
- Content-Type: `application/json`
- Publicly accessible (no auth, no geo-blocking)

**File content:**

```json
[
  {
    "relation": ["delegate_permission/common.handle_all_urls"],
    "target": {
      "namespace": "android_app",
      "package_name": "com.qrchat",
      "sha256_cert_fingerprints": [
        "AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99"
      ]
    }
  }
]
```

**Get your SHA-256 fingerprint:**
```bash
# Debug key
keytool -list -v -keystore ~/.android/debug.keystore -alias androiddebugkey -storepass android | grep SHA256

# Release key (from Play Console or your keystore)
keytool -list -v -keystore /path/to/release.keystore -alias your-alias | grep SHA256
```

Include BOTH debug and release fingerprints during development.

### AndroidManifest.xml Changes Needed

QRChat's current manifest has NO deep link intent filters. Add inside `<activity>`:

```xml
<activity
    android:name=".MainActivity"
    android:label="@string/app_name"
    android:configChanges="keyboard|keyboardHidden|orientation|screenLayout|screenSize|smallestScreenSize|uiMode"
    android:launchMode="singleTask"
    android:windowSoftInputMode="adjustResize"
    android:exported="true">

    <intent-filter>
        <action android:name="android.intent.action.MAIN" />
        <category android:name="android.intent.category.LAUNCHER" />
    </intent-filter>

    <!-- App Links (verified https) -->
    <intent-filter android:autoVerify="true">
        <action android:name="android.intent.action.VIEW" />
        <category android:name="android.intent.category.DEFAULT" />
        <category android:name="android.intent.category.BROWSABLE" />
        <data android:scheme="https" android:host="qrchat.app" />
    </intent-filter>

    <!-- Custom scheme fallback -->
    <intent-filter>
        <action android:name="android.intent.action.VIEW" />
        <category android:name="android.intent.category.DEFAULT" />
        <category android:name="android.intent.category.BROWSABLE" />
        <data android:scheme="qrchat" android:host="invite" />
    </intent-filter>
</activity>
```

### Android 15+ Dynamic Rules

Android 15 (API 35) supports dynamic URL pattern matching in assetlinks.json:

```json
[
  {
    "relation": ["delegate_permission/common.handle_all_urls"],
    "target": {
      "namespace": "android_app",
      "package_name": "com.qrchat",
      "sha256_cert_fingerprints": ["..."]
    }
  },
  {
    "relation": ["delegate_permission/common.handle_all_urls"],
    "target": {
      "namespace": "web"
    },
    "include": [
      {"path": "/invite/*"},
      {"path": "/join/*"}
    ],
    "exclude": [
      {"path": "/privacy*"},
      {"path": "/faq*"}
    ]
  }
]
```

### Verification

```bash
# Check verification status
adb shell pm get-app-links com.qrchat

# Force re-verification
adb shell pm verify-app-links --re-verify com.qrchat

# Test a deep link
adb shell am start -a android.intent.action.VIEW -d "https://qrchat.app/invite/test123" com.qrchat
```

---

## 3. Deep Linking in React Native

### Current State of QRChat

QRChat v4.3.0 uses:
- `@react-navigation/native` v7.1.31
- `@react-navigation/native-stack` v7.14.2
- `@react-navigation/bottom-tabs` v7.15.2
- React Native 0.84

The `Linking` API is imported in multiple screens (ChatScreen, SettingsScreen, MediaFilesScreen, etc.) but ONLY for `openURL()` — there is NO incoming deep link handling.

### Implementation with React Navigation

React Navigation has built-in deep linking support through the `linking` prop on `NavigationContainer`.

**Step 1: Define linking configuration**

```typescript
// src/navigation/linking.ts
import { LinkingOptions } from '@react-navigation/native';
import { Linking } from 'react-native';

const linking: LinkingOptions<RootParamList> = {
  prefixes: [
    'https://qrchat.app',
    'qrchat://',  // custom scheme fallback
  ],

  config: {
    screens: {
      // Invite link → opens AddContact flow with pre-filled data
      AddContact: {
        path: 'invite/:inviteCode',
      },
      // Group join → opens group join confirmation
      GroupJoin: {
        path: 'join/:groupInviteCode',
      },
      // Key verification
      VerifyKey: {
        path: 'verify/:verificationData',
      },
      // Chat direct open
      Chat: {
        path: 'chat/:contactId',
      },
      // Nested navigators
      Main: {
        screens: {
          Chats: 'chats',
          Settings: 'settings',
        },
      },
    },
  },

  // Custom URL resolution (for push notifications + deep links)
  async getInitialURL() {
    // Check if app was opened from a deep link
    const url = await Linking.getInitialURL();
    if (url != null) {
      return url;
    }
    // Check if app was opened from a push notification
    // (integrate with your push notification handler)
    return null;
  },

  // Listen for incoming links while app is open
  subscribe(listener) {
    const linkingSubscription = Linking.addEventListener('url', ({ url }) => {
      listener(url);
    });

    return () => {
      linkingSubscription.remove();
    };
  },
};

export default linking;
```

**Step 2: Apply to NavigationContainer**

```typescript
// In App.tsx or wherever NavigationContainer is rendered
import linking from './navigation/linking';

function App() {
  return (
    <NavigationContainer
      linking={linking}
      fallback={<LoadingScreen />}
    >
      <RootNavigator />
    </NavigationContainer>
  );
}
```

**Step 3: Handle the deep link in the target screen**

```typescript
// src/screens/AddContactScreen.tsx
import { useRoute } from '@react-navigation/native';

function AddContactScreen() {
  const route = useRoute();
  const { inviteCode } = route.params ?? {};

  useEffect(() => {
    if (inviteCode) {
      // Fetch invite data from server or decode from link
      processInviteCode(inviteCode);
    }
  }, [inviteCode]);
}
```

### Manual Deep Link Handling (Alternative)

If you need more control than React Navigation provides:

```typescript
// src/hooks/useDeepLink.ts
import { useEffect, useCallback } from 'react';
import { Linking } from 'react-native';

type DeepLinkHandler = (url: string) => void;

export function useDeepLink(handler: DeepLinkHandler) {
  const handleUrl = useCallback(({ url }: { url: string }) => {
    handler(url);
  }, [handler]);

  useEffect(() => {
    // Handle URL that launched the app (cold start)
    Linking.getInitialURL().then((url) => {
      if (url) handler(url);
    });

    // Handle URL while app is already running (warm start)
    const subscription = Linking.addEventListener('url', handleUrl);

    return () => subscription.remove();
  }, [handler, handleUrl]);
}

// Usage in App.tsx:
function App() {
  useDeepLink((url) => {
    const parsed = parseQRChatURL(url);
    if (parsed.type === 'invite') {
      NavigationService.navigate('AddContact', { inviteCode: parsed.code });
    } else if (parsed.type === 'join') {
      NavigationService.navigate('GroupJoin', { code: parsed.code });
    }
  });
}
```

### Available Libraries (2026)

| Library | Use Case | Status |
|---------|----------|--------|
| React Navigation `linking` | Built-in, handles URL→screen mapping | Recommended, active |
| `react-native` `Linking` API | Core RN module for URL handling | Built-in, always available |
| `@apliko/react-native-deep-link` | Lightweight, pure JS, no native modules | Active, good for simple cases |
| `react-native-branch` | Full deferred deep linking + attribution | Active but paid ($499+/mo) |
| Expo `expo-linking` | Expo-managed deep linking | Only for Expo projects |

**Note:** Firebase Dynamic Links was shut down in August 2025. Do NOT use it.

---

## 4. How Popular Messengers Handle Invite Links

### Telegram (t.me)

**Link formats:**
- Profile: `https://t.me/username` or `tg://resolve?domain=username`
- Group invite: `https://t.me/+HASH` (modern) or `https://t.me/joinchat/HASH` (legacy)
- Bot start: `https://t.me/botname?start=parameter`
- Share: `https://t.me/share?url=URL&text=TEXT`

**Technical implementation:**
- t.me is a web domain owned by Telegram, with AASA + assetlinks.json configured
- Also supports `telegram.me`, `telegram.dog` as aliases
- Custom `tg://` URI scheme as fallback
- Each link type maps to a specific API call (e.g., `tg://join?invite=HASH` calls `messages.importChatInvite`)
- Parameters: max 64 characters, base64url encoding, characters A-Z a-z 0-9 _ -

**App-not-installed fallback:**
- t.me is a functional website — the web page shows a preview and "Open in Telegram" / "Download Telegram" buttons
- The web page uses `<meta>` tags for social sharing previews
- Smart app banners redirect to App Store / Google Play

**Key insight for QRChat:** Telegram's dual-format approach (https + custom scheme) with a functional web fallback page is the gold standard.

### Signal (signal.me)

**Link formats:**
- Phone-based: `https://signal.me/#p/+12345678901`
- Username-based: `https://signal.me/#eu/ENCRYPTED_USERNAME`

**Privacy-critical design:**
- All identifying data is in the URL **fragment** (after `#`)
- Fragments are NEVER sent to the server in HTTP requests
- Signal's server receives only `https://signal.me/` — it has ZERO knowledge of which user is being contacted
- This is by design for a privacy-focused messenger

**Group invite links:**
- Contain the `GroupMasterKey` (encrypted) that allows deriving `GroupSecretParams`
- When a new member joins via link, they receive the group key via encrypted message
- Admin approval can be required for link-based joins

**Key insight for QRChat:** Signal's fragment-based approach is the privacy gold standard for E2E encrypted messengers. The server never sees the invite target.

### WhatsApp (wa.me)

**Link formats:**
- Direct chat: `https://wa.me/PHONE_NUMBER`
- Pre-filled message: `https://wa.me/PHONE_NUMBER?text=MESSAGE`
- Group invite: `https://chat.whatsapp.com/INVITE_CODE`
- Custom scheme: `whatsapp://send?phone=PHONE&text=MESSAGE`

**Technical implementation:**
- wa.me is a redirect service — it checks user-agent and redirects to web or app
- Group invite codes are server-generated opaque tokens
- Group invites have member limits (1024 members max)
- Admins can revoke/regenerate invite links

**App-not-installed fallback:**
- wa.me shows a landing page: "You need WhatsApp to use this feature"
- Link to App Store / Google Play
- No deferred deep linking — you need to re-tap the link after install

**Key insight for QRChat:** WhatsApp's group invite pattern (opaque server token, admin-controlled, revocable) is practical and secure.

### Comparison Matrix

| Feature | Telegram | Signal | WhatsApp | QRChat (proposed) |
|---------|----------|--------|----------|-------------------|
| Link domain | t.me | signal.me | wa.me | qrchat.app |
| Custom scheme | tg:// | sgnl:// | whatsapp:// | qrchat:// |
| Web fallback | Full preview | Minimal redirect | Landing page | Needed |
| Privacy (server sees?) | Hash only | Nothing (fragment) | Phone number | Fragment-based |
| Deferred deep link | Via web page | No | No | Clipboard-based |
| Group invites | Server hash | Encrypted key | Server token | Server token + fragment key |

---

## 5. Deferred Deep Linking

### The Problem

User taps `https://qrchat.app/invite/abc123` → app NOT installed → goes to App Store → installs → opens app → ...how does the app know about the original invite?

### Techniques (Ranked by Reliability)

#### 1. Clipboard / Pasteboard Method (Recommended for QRChat)

**How it works:**
1. User taps invite link → lands on `qrchat.app/invite/abc123` in browser
2. Web page shows "Install QRChat" button
3. When user taps the button, JavaScript copies the invite URL to clipboard
4. User installs from App Store, opens app
5. On first launch, app checks clipboard for `qrchat.app` URLs
6. If found → processes the invite

**Implementation (web landing page):**

```html
<!-- https://qrchat.app/invite/abc123 -->
<script>
async function installAndCopy() {
  try {
    await navigator.clipboard.writeText(window.location.href);
  } catch {
    // Fallback for older browsers
    const ta = document.createElement('textarea');
    ta.value = window.location.href;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
  }

  // Redirect to App Store
  const isIOS = /iPhone|iPad/.test(navigator.userAgent);
  if (isIOS) {
    window.location.href = 'https://apps.apple.com/app/qrchat/idXXXXXXXXXX';
  } else {
    window.location.href = 'https://play.google.com/store/apps/details?id=com.qrchat';
  }
}
</script>
```

**Implementation (app side, React Native):**

```typescript
// src/utils/deferredDeepLink.ts
import Clipboard from '@react-native-clipboard/clipboard';
import AsyncStorage from '@react-native-async-storage/async-storage';

const DEFERRED_LINK_CHECKED = 'deferred_deep_link_checked';

export async function checkDeferredDeepLink(): Promise<string | null> {
  // Only check on first launch
  const alreadyChecked = await AsyncStorage.getItem(DEFERRED_LINK_CHECKED);
  if (alreadyChecked) return null;

  try {
    const clipboardContent = await Clipboard.getString();

    if (clipboardContent && clipboardContent.startsWith('https://qrchat.app/')) {
      // Mark as checked so we don't re-process
      await AsyncStorage.setItem(DEFERRED_LINK_CHECKED, 'true');

      // Clear the clipboard for privacy
      Clipboard.setString('');

      return clipboardContent;
    }
  } catch (e) {
    console.log('[DeferredDeepLink] Clipboard check failed:', e);
  }

  await AsyncStorage.setItem(DEFERRED_LINK_CHECKED, 'true');
  return null;
}
```

**iOS caveat:** Since iOS 16, reading the clipboard shows a "paste" permission banner to the user. This is unavoidable but acceptable. Since iOS 16.4, you can use `UIPasteboard.detectValues(for:)` which is less intrusive.

#### 2. Device Fingerprinting (Probabilistic)

**How it works:**
1. User clicks link → server records IP, user-agent, screen size, OS version, language, timezone
2. User installs app → app sends same device info to server on first launch
3. Server matches the two fingerprints within a time window (typically 24h)

**Accuracy:** 85-95% post-ATT (Apple's App Tracking Transparency). Drops significantly on corporate WiFi or VPN.

**NOT recommended as primary method** for QRChat — too unreliable and privacy-invasive for an encrypted messenger.

#### 3. Android Install Referrer (Android Only, Deterministic)

**How it works:**
1. Generate a Play Store URL with referrer: `https://play.google.com/store/apps/details?id=com.qrchat&referrer=invite%3Dabc123`
2. After install, use the Install Referrer API to retrieve the referrer string

```typescript
// Android-only, requires react-native-device-info or a native module
import { getInstallReferrerAsync } from './native/InstallReferrer';

const referrer = await getInstallReferrerAsync();
// referrer = "invite=abc123"
```

**This is 100% reliable on Android** and should always be used as the Android strategy.

#### 4. App Clip / Instant App (Platform-Specific)

- **iOS App Clips:** A lightweight version of your app (10MB max) that opens instantly from a link. Can pass data to the full app after install.
- **Android Instant Apps:** Similar concept — runs without install, can pass intent data to full install.

Both are complex to implement but provide the best UX. Consider for a future version.

### Recommended Strategy for QRChat

| Platform | Primary Method | Fallback |
|----------|---------------|----------|
| iOS | Clipboard (web page copies URL before App Store redirect) | Manual re-tap after install |
| Android | Play Store Install Referrer (deterministic, 100%) | Clipboard |
| Both | Web landing page with smart routing | QR code contains all data |

---

## 6. Security Considerations for E2E Encrypted Messengers

### The Core Question: What Goes in the URL vs. on the Server?

For QRChat (E2E encrypted, TweetNaCl), this is critical. The invite link must not leak information that compromises encryption.

### Data Classification

#### SAFE to put in the URL (public data):
- Invite code / opaque token (random, server-generated)
- Link type identifier (invite, join, verify)
- Expiration hint
- Version number

#### MUST go in URL fragment (after #) — never reaches server:
- Public keys for key exchange
- Key verification fingerprints
- Any data the server should not see

#### MUST stay on the server (retrieved after authentication):
- User identity mapping (invite code → user public key)
- Group metadata
- Invite usage count / limits
- Revocation status

### Recommended URL Format for QRChat

```
https://qrchat.app/invite/TOKEN#PUBLIC_KEY_DATA
```

**Breakdown:**
- `https://qrchat.app/invite/` — triggers Universal Link / App Link
- `TOKEN` — opaque server-generated invite token (e.g., `a7f3b2c1d4e5`)
  - Server maps TOKEN → inviter's identity, creation time, expiration, usage limit
  - Server can revoke TOKEN at any time
- `#PUBLIC_KEY_DATA` — base64url-encoded public key material
  - This is the inviter's TweetNaCl public key (32 bytes → 43 chars base64url)
  - The `#` fragment is NEVER sent to the server in HTTP requests
  - Only the receiving client (the person tapping the link) sees this
  - Enables immediate key exchange without server knowing the keys

**Example:**
```
https://qrchat.app/invite/a7f3b2c1#dGhpcyBpcyBhIHRlc3QgcHVibGljIGtleQ
```

### Security Properties

1. **Server never sees public keys** — they're in the fragment
2. **Server can revoke invites** — by invalidating the TOKEN
3. **Links are time-limited** — server enforces expiration
4. **Links are usage-limited** — server tracks how many times TOKEN was used
5. **Man-in-the-middle protection** — the public key in the fragment allows out-of-band key verification
6. **No metadata leakage** — server only knows "someone used invite TOKEN" but not the key material exchanged

### Invite Flow (Detailed)

```
INVITER (Alice)                    SERVER                     INVITEE (Bob)
    |                                |                            |
    |  1. Generate invite            |                            |
    |  - Create random TOKEN         |                            |
    |  - Include her public key      |                            |
    |     in URL fragment            |                            |
    |                                |                            |
    |  2. POST /api/invite           |                            |
    |  {token: TOKEN,                |                            |
    |   expires: 24h,                |                            |
    |   maxUses: 1}                  |                            |
    |------------------------------->|                            |
    |                                | 3. Store invite metadata   |
    |                                |                            |
    |  4. Share link:                |                            |
    |  qrchat.app/invite/TOKEN      |                            |
    |  #ALICE_PUBLIC_KEY             |                            |
    |---------------------------------------------->              |
    |                                |                            |
    |                                |  5. Bob taps link          |
    |                                |  App extracts:             |
    |                                |  - TOKEN from path         |
    |                                |  - ALICE_PUBLIC_KEY from # |
    |                                |                            |
    |                                |  6. GET /api/invite/TOKEN  |
    |                                |<---------------------------|
    |                                |                            |
    |                                |  7. Return invite metadata |
    |                                |  {inviterName: "Alice",    |
    |                                |   status: "valid",         |
    |                                |   expiresAt: "..."}        |
    |                                |--------------------------->|
    |                                |                            |
    |                                |  8. Bob confirms "Add      |
    |                                |     Alice as contact"      |
    |                                |                            |
    |                                |  9. Bob sends his public   |
    |                                |     key to Alice via       |
    |                                |     encrypted channel      |
    |                                |     (using Alice's key     |
    |                                |      from the fragment)    |
    |<-------------------------------|<---------------------------|
    |                                |                            |
    | 10. Both have each other's     |                            |
    |     public keys → E2E ready    |                            |
```

### Threat Model

| Threat | Mitigation |
|--------|-----------|
| Server compromise | Server never has key material (it's in the fragment) |
| Link interception (MITM) | HTTPS protects the TOKEN; public key in fragment enables verification |
| Link forwarding (wrong person uses it) | Set maxUses=1; require mutual confirmation |
| Brute-force TOKEN guessing | Use cryptographically random tokens (128+ bits) |
| Link never expires | Server-enforced TTL (e.g., 24 hours) |
| Replay attack | One-time use tokens + server-side invalidation |
| Metadata analysis | Minimal server-side data; no key material stored |

---

## 7. Recommendations for QRChat

### Architecture Overview

```
                                 ┌─────────────────────┐
                                 │   qrchat.app (web)   │
                                 │                       │
                                 │  /.well-known/        │
                                 │    apple-app-site-    │
                                 │    association        │
                                 │    assetlinks.json    │
                                 │                       │
                                 │  /invite/:token       │
                                 │    → landing page     │
                                 │    → app (if installed)│
                                 └───────────┬───────────┘
                                             │
                              ┌──────────────┼──────────────┐
                              │              │              │
                         App installed  App NOT installed  Browser
                              │              │              │
                         Universal Link  Landing page    Landing page
                         / App Link      shows preview   shows preview
                              │          + "Install" btn  + "Install" btn
                              │              │
                         App opens       Clipboard copy
                         with URL        + Store redirect
                              │              │
                         Parse TOKEN     After install,
                         + fragment      check clipboard
                              │              │
                         Process invite  Process invite
```

### Implementation Phases

#### Phase 1: Domain + Web Infrastructure
1. **Register `qrchat.app`** (or use a subdomain of your Railway deployment)
2. Host AASA file at `/.well-known/apple-app-site-association`
3. Host assetlinks.json at `/.well-known/assetlinks.json`
4. Create landing page template for `/invite/:token`

#### Phase 2: Native Configuration
1. Add `applinks:qrchat.app` to iOS entitlements
2. Update `AppDelegate.swift` to forward universal links to RCTLinkingManager
3. Add intent-filter with `autoVerify="true"` to AndroidManifest.xml
4. Test on physical devices (both platforms)

#### Phase 3: React Native Deep Link Handler
1. Add `linking` config to NavigationContainer
2. Create invite processing screen
3. Implement `useDeepLink` hook for manual handling
4. Handle cold start + warm start scenarios

#### Phase 4: Invite Generation + Server API
1. `POST /api/invite` — create invite (returns TOKEN)
2. `GET /api/invite/:token` — validate invite (returns metadata)
3. `DELETE /api/invite/:token` — revoke invite
4. Rate limiting on invite creation and validation

#### Phase 5: Deferred Deep Linking
1. Build web landing page with clipboard copy
2. Implement clipboard check on first app launch
3. Android: add Install Referrer support
4. Test the full flow: link → store → install → auto-process

#### Phase 6: Share UI
1. "Invite friend" button in the app
2. Generate invite link with public key in fragment
3. Share via system share sheet
4. QR code generation for in-person sharing (QRChat already has QR support)

### Key Technical Decisions

| Decision | Recommendation | Rationale |
|----------|---------------|-----------|
| Domain | `qrchat.app` (dedicated) | Clean URLs, proper AASA/assetlinks hosting |
| Custom scheme | `qrchat://` as fallback only | Universal/App Links are more reliable |
| Deep link library | React Navigation built-in `linking` | Already using RN Navigation v7, no extra deps |
| Deferred DL (iOS) | Clipboard method | Self-hosted, no vendor lock-in, privacy-respecting |
| Deferred DL (Android) | Install Referrer API | 100% reliable, deterministic |
| Key material in URL | URL fragment (`#`) | Server never sees keys — critical for E2E |
| Invite tokens | Server-generated, 128-bit random | Revocable, rate-limited, time-limited |
| Third-party DL service | NOT recommended | QRChat is privacy-focused; Branch/AppsFlyer collect too much data |

### Files That Need Changes

| File | Change |
|------|--------|
| `ios/QRChat/QRChat.entitlements` | Add `com.apple.developer.associated-domains` |
| `ios/QRChat/AppDelegate.swift` | Forward universal links to RCTLinkingManager |
| `android/app/src/main/AndroidManifest.xml` | Add intent-filter with autoVerify |
| `App.tsx` (or NavigationContainer wrapper) | Add `linking` prop with config |
| `server/index.js` | Add `/api/invite` CRUD endpoints |
| `server/` (new) | Serve AASA + assetlinks.json + landing pages |
| `src/screens/` (new) | InviteScreen, GroupJoinScreen |
| `src/utils/deferredDeepLink.ts` (new) | Clipboard-based deferred link check |
| `src/navigation/linking.ts` (new) | Deep link configuration |

---

## Sources

- [Universal Links AASA Implementation Guide — HashStudioz](https://www.hashstudioz.com/blog/universal-links-and-apple-app-site-association-aasa-implementation-debugging/)
- [iOS Universal Links — Expo Documentation](https://docs.expo.dev/linking/ios-universal-links/)
- [iOS Universal Links Setup and Debugging — Bugfender](https://bugfender.com/blog/ios-universal-links/)
- [Apple App Site Association (AASA) — Branch](https://www.branch.io/glossary/aasa-apple-app-site-association/)
- [Apple Developer: Supporting Associated Domains](https://developer.apple.com/documentation/xcode/supporting-associated-domains)
- [TN3155: Debugging Universal Links — Apple](https://developer.apple.com/documentation/technotes/tn3155-debugging-universal-links)
- [Universal Link Checker & AASA Validator](https://getuniversal.link/)
- [IOS Universal Links Not Opening — Troubleshooting Guide 2026](https://copyprogramming.com/howto/ios-universal-links-are-not-opening-in-app)
- [Configure Website Associations — Android Developers](https://developer.android.com/training/app-links/configure-assetlinks)
- [Add Android App Links — Android Studio](https://developer.android.com/studio/write/app-link-indexing)
- [Verify App Links — Android Developers](https://developer.android.com/training/app-links/verify-applinks)
- [Getting Started — Google Digital Asset Links](https://developers.google.com/digital-asset-links/v1/getting-started)
- [Android App Links — Expo Documentation](https://docs.expo.dev/linking/android-app-links/)
- [Deep Linking — React Navigation](https://reactnavigation.org/docs/deep-linking/)
- [Configuring Links — React Navigation](https://reactnavigation.org/docs/configuring-links/)
- [Linking API — React Native](https://reactnative.dev/docs/linking)
- [Deep Linking in React Native: Complete Guide 2026 — Smler](https://app.smler.io/blogs/deep-linking/react-native/deep-linking-in-react-native-complete-guide-2026)
- [How to Implement Deep Linking in React Native — OneUptime](https://oneuptime.com/blog/post/2026-01-15-react-native-deep-linking/view)
- [Telegram Deep Links — core.telegram.org](https://core.telegram.org/api/links)
- [Signal.me URLs — Signal Wiki](https://signal.miraheze.org/wiki/Signal.me_URLs)
- [Signal Private Group System](https://signal.org/blog/pdfs/signal_private_group_system.pdf)
- [Group Link or QR-code — Signal Support](https://support.signal.org/hc/en-us/articles/360051086971-Group-Link-or-QR-code)
- [WhatsApp Deep Links Guide — Visito](https://www.visitoai.com/en/blog/whatsapp-deep-links-complete-setup-guide)
- [Deferred Deep Linking in iOS and Android: Guide for 2026 — Adapty](https://adapty.io/blog/deferred-deep-linking/)
- [Deferred Deep Linking: How It Works Internally — DEV](https://dev.to/sky1095/deferred-deep-linking-how-it-works-internally-1l1a)
- [Implementing Deferred Deep Links with Clipboard — Medium](https://medium.com/@jongchanko/ios-implementing-deferred-deep-links-with-clipboard-5aad094d0edb)
- [Deferred Deep Linking with Device Snapshotting — Branch](https://www.branch.io/resources/blog/deferred-deep-linking-with-device-snapshotting/)
- [Branch.io Alternative for Deep Linking — DEV](https://dev.to/stefanobholz/i-built-a-branchio-alternative-for-79mo-instead-of-499-50oe)
- [How to Set Up Deferred Deep Linking with Dub](https://dub.co/docs/concepts/deep-links/deferred-deep-linking)
- [NativeLink Deferred Deep Linking — Branch](https://help.branch.io/faq/docs/nativelink-deferred-deep-linking)
- [SimpleX Chat Invitation — Key Material in URL Fragment](https://simplex.chat/invitation/)
- [RocketShare Security Whitepaper](https://rocketshare.app/security-whitepaper)
- [Deep Links, Universal and Asset Links — Widlarz Group](https://www.thewidlarzgroup.com/blog/deep-links-universal-and-asset-links)
- [React Native Deep Linking That Actually Works — Medium](https://medium.com/@nikhithsomasani/react-native-deep-linking-that-actually-works-universal-links-cold-starts-oauth-aced7bffaa56)
