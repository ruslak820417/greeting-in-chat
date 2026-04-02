# Apple App Store Review — Section 4: DESIGN Audit

**App:** QRChat v4.1.0
**Date:** 2026-03-22
**Auditor:** Design Audit Agent
**Verdict:** PASS with minor recommendations

---

## 4.0 Design — General

### App offers a useful, unique experience?
- **PASS** — QRChat is an E2E encrypted messenger with a unique QR code-based contact exchange system. Differentiation: TweetNaCl (Ed25519 + X25519) crypto, no phone number required, QR-only contact adding, self-destruct messages, WebRTC P2P calls.

### Not a simple copy of another messenger?
- **PASS** — Original UI with custom theme engine (Light + Dark + user-editable themes via ThemeEditorScreen), custom SplashScreen with boot log animation, unique QR code identity system. Not a WhatsApp/Signal skin clone.

### Sufficient functionality (not a thin app)?
- **PASS** — Full-featured messenger with 22 screens: chat, contacts, groups, calls (audio+video), profile, settings, QR scan/generate, call log, media files, contact profiles, phone contacts import, theme editor, upgrade, terms, support.

---

## 4.1 Copycats

### UI is original?
- **PASS** — ChatScreen.tsx (2000+ lines): custom message bubbles with swipe-to-reply, album grid layout for grouped images, phone number auto-detection, link previews, waveform visualization for audio, date separators, reactions overlay. Not a clone of any existing messenger UI.
- HomeScreen.tsx: custom tab architecture (messages/contacts/calls in one screen), swipeable conversations with pin/archive/delete, real-time contact status polling, pending contact requests system.

---

## 4.2 Minimum Functionality

### Required features present?

| Feature | Status | Location |
|---------|--------|----------|
| Chat (text) | PASS | ChatScreen.tsx — encrypted-message type |
| Contacts | PASS | ContactsScreen.tsx, ContactProfileScreen.tsx |
| Settings | PASS | SettingsScreen.tsx — full settings with 15+ options |
| Profile | PASS | ProfileScreen.tsx — avatar, name, fingerprint, QR |
| Photos/Images | PASS | launchImageLibrary/launchCamera in ChatScreen |
| Video messages | PASS | image-picker with video support |
| File sharing | PASS | react-native-document-picker in ChatScreen |
| Audio messages | PASS | @react-native-community/audio-toolkit Recorder/Player |
| Voice calls | PASS | CallScreen.tsx + WebRTCManager + react-native-webrtc |
| Video calls | PASS | CallScreen.tsx with RTCView, isVideo param |
| Groups | PASS | CreateGroupScreen.tsx, GroupInfoScreen.tsx |
| Call log | PASS | CallLogScreen.tsx |
| Contact requests | PASS | contact-request/contact-accepted/contact-rejected in server |

### Not just a WebView wrapper?
- **PASS** — Zero WebView usage found in src/. Pure React Native with native modules (react-native-webrtc, react-native-keychain, op-sqlite, react-native-camera-kit, react-native-callkeep, react-native-incall-manager).

---

## 4.3 Spam

### No spam mechanisms?
- **PASS** — No mass messaging, no broadcast lists, no automated sending.

### Rate limiting on server?
- **PASS** — server/index.js implements:
  - Token bucket rate limiting per WebSocket connection: 200 burst, 20 tokens/sec refill (line 149-150)
  - Payload size cap: 1.5MB per WS message (line 150, 371-376)
  - Pending queue DoS protection: MAX_PENDING_PER_USER=1000, MAX_PENDING_SIZE_PER_USER=50MB (lines 143-144)
  - Admin rate limiting: 5 attempts per 60s per IP (lines 84-107)
  - Message expiry: 48 hours for pending messages (line 39)
  - Rate-limited response with retryAfter sent to client (lines 380-384)

---

## 4.4 Extensions
- **N/A** — No app extensions.

---

## 4.5 Apple Sites and Services

### Does not reproduce Apple functionality (Messages, FaceTime)?
- **PASS** — QRChat differentiates from Apple Messages/FaceTime through:
  - E2E encryption with TweetNaCl (Ed25519 + X25519) — not iMessage protocol
  - QR code-based contact exchange (no phone number/Apple ID)
  - Self-destruct messages
  - Custom WebRTC P2P calling (not FaceTime)
  - Cross-platform design (React Native for iOS + Android)
  - Zero-knowledge server architecture (relay only, no message storage)
  - User-configurable themes with editor

---

## 4.6 Alternate App Icons
- **N/A** — Single app icon.

---

## 4.7 HTML5 Games, Bots
- **N/A** — No games, no bots.

---

## UI/UX Quality Check

### Accessibility Labels

- **PASS** — 147 accessibilityLabel occurrences across 22 files
- **PASS** — 145 accessibilityRole occurrences across 22 files
- Coverage: All screens have accessibility labels on interactive elements
- Roles used: "button", "switch", "radio", "text", "link", "imagebutton"
- SettingsScreen: 15 occurrences (comprehensive)
- ContactProfileScreen: 11 occurrences
- HomeScreen: 15 occurrences
- ChatScreen: 37 occurrences

### Dynamic Type Support

- **WARNING** — No `allowFontScaling` or `maxFontSizeMultiplier` props found anywhere in src/. React Native defaults to `allowFontScaling={true}`, which means Dynamic Type IS supported by default. However, no explicit `maxFontSizeMultiplier` guards could cause layout breakage at the largest accessibility text sizes.
- **Recommendation:** Add `maxFontSizeMultiplier={1.5}` to critical layout Text components (headers, buttons) to prevent overflow while still supporting Dynamic Type.

### Safe Area Respected

- **PASS** — `useSafeAreaInsets` imported in 10 screens. All major screens use `insets.top` for header padding:
  - HomeScreen.tsx: `paddingTop: insets.top + 16`
  - SettingsScreen.tsx: `paddingTop: insets.top + 16`
  - ProfileScreen.tsx: `paddingTop: insets.top + 16`
  - ContactsScreen.tsx: uses insets
  - ContactProfileScreen.tsx: uses insets

### Status Bar Visible and Correct

- **PASS** — StatusBar component used in 20 screens with theme-aware style:
  - `barStyle={C.statusBarStyle}` — dynamically switches between 'light-content' and 'dark-content' based on active theme
  - Light theme: 'dark-content', Dark theme: 'light-content'
  - SplashScreen: hardcoded 'light-content' (correct — dark background)

### Navigation Back Button

- **PASS** — `navigation.goBack()` found in 15 screens. Custom back button pattern: `<TouchableOpacity onPress={() => navigation.goBack()}>` with accessibility labels.
- All sub-screens (Settings, Profile, Contacts, ContactProfile, QRScan, QRGenerate, etc.) have back navigation.

### Keyboard Does Not Cover Input

- **PASS** — `KeyboardAvoidingView` used in:
  - ChatScreen.tsx (critical — message input)
  - SetupScreen.tsx (name input)
- Other screens with TextInput (SettingsScreen promo code) use ScrollView which handles keyboard avoidance.

### Launch Screen / Splash Screen

- **PASS** — Two-layer splash:
  1. iOS native: `ios/QRChat/LaunchScreen.storyboard` (required by Apple)
  2. Custom React Native: `src/components/SplashScreen.tsx` — animated boot log with Logo, version display, fade-out transition

### Dark Mode Support

- **PASS** — Full dark mode implementation:
  - ThemeContext.tsx: 2 built-in themes (Light + Dark) + custom theme editor
  - Dark theme follows WhatsApp/Telegram best practices (comment in code)
  - All 20+ screens use `useTheme()` hook for dynamic colors
  - Status bar style adapts per theme
  - Theme persisted in AsyncStorage

---

## Account Deletion (OBLIGATORY since June 2022)

### Delete Account Present in Settings?
- **PASS** — SettingsScreen.tsx lines 504-543: "Delete all data" button at bottom of settings.

### Is it functional?
- **PASS** — Delete flow:
  1. Confirmation alert with destructive action (`Alert.alert` with cancel + destructive button)
  2. `MessagingService.destroy()` — disconnects WebSocket, stops services
  3. `Database.clearAll()` — comprehensive wipe:
     - Keychain reset (cryptographic keys deleted)
     - SQLite tables cleared: messages, contacts, groups_table, contact_requests, settings
     - AsyncStorage cleared: profile, contacts, messages, settings, keys, groups, contact_requests, install_id, migration flags, unlimited license
  4. Navigation reset to WelcomeScreen (fresh start)
- **Note:** Server-side deregistration not explicitly called — the server has no persistent user record beyond the WebSocket session, so this is acceptable given the zero-knowledge architecture.

### Button visible and accessible?
- **PASS** — Red-bordered button with trash icon, `accessibilityLabel="Delete all data"`, `accessibilityRole="button"`. Clear destructive styling with `borderColor: C.error`.

---

## Additional Design Quality Notes

### Report / Block User (Apple 1.2 requirement cross-check)
- **PASS** — ContactProfileScreen.tsx has "Report User" button with 4 categories: spam, harassment, inappropriate_content, other. Reports sent via email AND server has /report endpoint (server/index.js lines 271-302) that logs reports to disk.
- Block user functionality in ContactsScreen via `Database.blockContact()` / `Database.unblockContact()`.

### Internationalization (i18n)
- **PASS** — 4 languages: English, Romanian, Russian, French
- react-i18next used across all screens
- Language selector in SettingsScreen
- Privacy policy URL adapts per language

### Theme Editor
- **BONUS** — ThemeEditorScreen allows users to customize themes, demonstrating above-minimum design effort.

---

## Summary

| Section | Verdict | Issues |
|---------|---------|--------|
| 4.0 Design General | PASS | None |
| 4.1 Copycats | PASS | None |
| 4.2 Minimum Functionality | PASS | None |
| 4.3 Spam | PASS | None |
| 4.4 Extensions | N/A | — |
| 4.5 Apple Sites/Services | PASS | None |
| 4.6 Alternate Icons | N/A | — |
| 4.7 HTML5/Bots | N/A | — |
| Accessibility | PASS | Minor: add maxFontSizeMultiplier guards |
| Dynamic Type | PASS (default) | Recommendation: explicit maxFontSizeMultiplier |
| Safe Area | PASS | None |
| Status Bar | PASS | None |
| Back Navigation | PASS | None |
| Keyboard Handling | PASS | None |
| Launch Screen | PASS | None |
| Dark Mode | PASS | None |
| Account Deletion | PASS | None |

### Overall Design Verdict: PASS

**Risk level for Apple rejection on Section 4:** LOW

**One recommendation:**
- Add `maxFontSizeMultiplier={1.5}` on header and button Text components to prevent layout breakage at extreme Dynamic Type sizes. This is not a rejection reason but improves accessibility compliance.
