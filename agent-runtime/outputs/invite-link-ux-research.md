# Invite Link System — UX Research Report

**Date:** 2026-03-24
**Target:** QRChat v3.0.6 (React Native, E2E Encrypted Messenger)
**Languages:** en / ro / ru / fr

---

## Table of Contents

1. [Competitive Analysis](#1-competitive-analysis)
2. [Recommended User Flows](#2-recommended-user-flows)
3. [Screen-by-Screen Design Specifications](#3-screen-by-screen-design-specifications)
4. [Error States](#4-error-states)
5. [Notification UX](#5-notification-ux)
6. [Share Sheet Integration](#6-share-sheet-integration)
7. [Deep Link & Deferred Deep Link Handling](#7-deep-link--deferred-deep-link-handling)
8. [i18n Considerations](#8-i18n-considerations)
9. [Security UX Considerations](#9-security-ux-considerations)
10. [Implementation Recommendations](#10-implementation-recommendations)

---

## 1. Competitive Analysis

### 1.1 Telegram Invite Links

**Creation Flow:**
- Group/Channel > Settings (gear icon) > Invite Links > Create New Link
- Configuration options: Name, Expiration date, Usage limit, Require admin approval
- Link types: Permanent (no limits), Temporary (time-bound), Usage-limited (N uses), Approval-required

**Key UX Patterns:**
- Default invite link is auto-generated when a group is created
- Multiple invite links can coexist (each trackable independently)
- Links follow the pattern `t.me/+XXXXX` (short, shareable)
- Revoked links preserve historical join data but block new joins
- Admin approval flow: user taps link > sees "Request Sent" > admin gets notification > approve/dismiss
- Paid invite links exist for channels (monthly Telegram Stars payments)

**Management Dashboard:**
- List view of all active/revoked links
- Each link shows: name, creation date, usage count, expiration, creator
- Bulk actions: revoke all links from a specific admin

### 1.2 Signal Username & Group Links

**Username Sharing (1:1 connections):**
- Settings > Profile > Username (3-32 chars, must end with 2+ digits)
- Three sharing methods: tell username verbally, share QR code, share URL
- QR code and URL can be reset independently of the username
- Recipient: New Chat > type exact username > sends message request
- Sender receives request > accept / reject / block
- Usernames are NOT searchable — only exact match works (privacy by design)

**Group Links:**
- Group Settings > Group Link > Enable
- Optional: toggle "Approve New Members" for admin gate
- Share via: Copy link, QR code, or native share sheet
- Admin approval: notification appears in-app > View Requests > checkmark to accept, X to reject
- Link management: Reset Link (generates new URL, old one dies), or Disable entirely

**Key Design Principle:** Usernames are ephemeral identifiers, not permanent handles. Users are encouraged to change them contextually (e.g., after a conference).

### 1.3 WhatsApp Group Invite Links

**Creation Flow:**
- Group Info > Invite via Link
- Actions on link screen: Copy Link, Share Link (native share sheet), QR Code, Reset Link

**Acceptance Flow (without admin approval):**
- Tap link > WhatsApp opens > popup shows group name + photo + member count > green "Join Group" button

**Acceptance Flow (with admin approval):**
- Tap link > popup shows "Request to join" button + text "An admin must approve your request"
- After request: user sees pending state; admins see "Pending Requests" notification

**Key UX Pattern:** The acceptance screen always shows the group name, group photo, and a brief description before the user commits. This builds trust and prevents accidental joins.

### 1.4 SimpleX Chat (Privacy-First Reference)

**Connection Types:**
- **1-Time Invitation Link:** Single use, best for known contacts via secure channel or QR scan in person
- **Contact Address:** Long-term, reusable, suitable for social media profiles or email signatures

**Key Design Insight:** Contact addresses are NOT used to deliver messages — only for initial connection requests. Deleting the address does not break existing connections. This is highly relevant for QRChat's encrypted architecture.

**Security UX:** SHA256 security codes displayed for users to verify connections against MITM attacks.

### 1.5 Discord Invite Links

**Error Handling (Anti-Pattern to Avoid):**
- Discord shows a generic "This invite may be expired, or you might not have permission to join" for ALL failure cases
- Does NOT differentiate between expired, revoked, invalid, or server-deleted links
- Does NOT offer actionable recovery (no "Request new link" or "Contact sender" option)
- **Lesson:** Always be specific about what went wrong and offer a next step

---

## 2. Recommended User Flows

### 2.1 Primary Flow: Alice Creates Link, Bob Accepts

```
ALICE (Sender)                              BOB (Recipient)
─────────────────────                       ─────────────────────
1. Opens contact/chat list
2. Taps [+] or "Invite" button
3. Sees "Create Invite Link" screen
   - Toggle: One-time use / Multi-use
   - Expiration: 30min / 1hr / 24hr / 7days / Custom / Never
   - Optional: Personal note
4. Taps "Create Link"
5. Sees share screen with:
   - QR Code (large, scannable)
   - Short link (qrchat.app/i/XXXX)
   - [Copy Link] button
   - [Share] button (native share sheet)
   - [Show QR] toggle
6. Shares via preferred method ──────────►  7. Receives link (SMS/WhatsApp/etc.)
                                            8. Taps link
                                            9a. IF app installed:
                                                App opens > Invite screen shows:
                                                - Alice's display name
                                                - Alice's avatar (if shared)
                                                - "Alice wants to chat securely"
                                                - Security badge: "End-to-end encrypted"
                                                - [Accept] [Decline] buttons
                                            9b. IF app NOT installed:
                                                Web page shows:
                                                - App description + link preview
                                                - [Download on App Store]
                                                - [Get on Google Play]
                                                - Link is preserved for deferred deep link
                                            10. Bob taps [Accept] ──────────────►
11. Alice receives push notification:
    "Bob accepted your invite!"
12. Chat opens automatically between
    Alice and Bob (keys exchanged)
13. Alice sees Bob in contact list
    with status "Connected"
```

### 2.2 Secondary Flow: QR Code Scan (In-Person)

```
ALICE                                       BOB
─────────────────────                       ─────────────────────
1. Opens "Invite" screen
2. Large QR code displayed
3. ──────────────────────────────────────►  4. Opens QRChat camera/scanner
                                            5. Scans QR code
                                            6. Sees Alice's profile + [Connect] button
                                            7. Taps [Connect]
8. Notification: "Bob connected!"
9. Chat ready
```

### 2.3 Link Management Flow

```
ALICE
─────────────────────
1. Settings > Invite Links (or Chat List > Invite icon > "Manage Links")
2. Sees list of all created links:
   - Each card shows:
     [Link name/recipient hint] [Status badge]
     Created: Mar 24, 2026
     Expires: Mar 25, 2026 (countdown: 23h 45m remaining)
     Status: Pending / Accepted / Expired / Revoked
   - Swipe left to reveal: [Revoke] [Delete]
3. Taps a link card > Detail view:
   - Full link URL (copyable)
   - QR code (re-sharable)
   - Timeline: Created > Shared > Viewed > Accepted
   - [Revoke Link] button (red)
   - [Share Again] button
```

---

## 3. Screen-by-Screen Design Specifications

### Screen 1: Create Invite Link

**Layout (top to bottom):**
```
┌─────────────────────────────────┐
│  < Back          Create Invite  │  (Navigation bar)
├─────────────────────────────────┤
│                                 │
│  ┌─────────────────────────┐    │
│  │  Link Type               │   │
│  │  ○ One-time (1 person)   │   │  (Radio buttons)
│  │  ● Reusable              │   │
│  └─────────────────────────┘    │
│                                 │
│  ┌─────────────────────────┐    │
│  │  Expires after           │   │
│  │  [30m] [1h] [24h] [7d]  │   │  (Pill selector, "24h" default)
│  │  [Custom] [Never]       │   │
│  └─────────────────────────┘    │
│                                 │
│  ┌─────────────────────────┐    │
│  │  Personal Note (optional)│   │
│  │  "Hey, scan this to..."  │   │  (Text input, 100 char max)
│  └─────────────────────────┘    │
│                                 │
│  ┌─────────────────────────┐    │
│  │  ℹ️ This link uses end-  │   │
│  │  to-end encryption.      │   │  (Info banner, subtle)
│  │  Only you and the        │   │
│  │  recipient can read      │   │
│  │  messages.               │   │
│  └─────────────────────────┘    │
│                                 │
│  ╔═════════════════════════╗    │
│  ║    Create Link          ║    │  (Primary CTA, full-width)
│  ╚═════════════════════════╝    │
│                                 │
└─────────────────────────────────┘
```

**Design Notes:**
- Default to "One-time" for maximum security (aligned with SimpleX model)
- Default expiration: 24 hours (aligned with Discord/Telegram defaults)
- Info banner uses the app's accent color at 10% opacity
- Personal note is NOT transmitted in the link itself — stored locally for Alice's reference

### Screen 2: Share Invite Link

**Layout:**
```
┌─────────────────────────────────┐
│  < Back           Share Link    │
├─────────────────────────────────┤
│                                 │
│         ┌───────────┐           │
│         │           │           │
│         │  QR CODE  │           │  (200x200pt, high contrast)
│         │           │           │
│         └───────────┘           │
│                                 │
│    qrchat.app/i/Xk9mP2         │  (Monospace, tappable to copy)
│                                 │
│    Expires in 23h 59m           │  (Countdown, subtle gray)
│                                 │
│  ┌─────────┐  ┌──────────┐     │
│  │📋 Copy  │  │📤 Share  │     │  (Two equal buttons)
│  └─────────┘  └──────────┘     │
│                                 │
│  ── or share directly ───       │
│                                 │
│  ┌──────┐┌──────┐┌──────┐      │
│  │ SMS  ││WhatsA││Telegr│      │  (Horizontal scroll of
│  └──────┘└──────┘└──────┘      │   app icons, detected from
│  ┌──────┐┌──────┐┌──────┐      │   installed apps)
│  │Email ││Signal││ More │      │
│  └──────┘└──────┘└──────┘      │
│                                 │
│  ╔═════════════════════════╗    │
│  ║       Done              ║    │
│  ╚═════════════════════════╝    │
│                                 │
└─────────────────────────────────┘
```

**Design Notes:**
- QR code is the hero element — large and prominent (supports in-person scanning)
- Short link uses a vanity URL format: `qrchat.app/i/XXXXXX` (6-8 char alphanumeric)
- "Copy" button shows a checkmark animation + haptic feedback on tap, with text changing to "Copied!" for 2 seconds
- "Share" button opens native iOS/Android share sheet
- Direct share icons: detect installed messaging apps, show top 6, "More" opens full share sheet
- Countdown timer updates in real-time (every minute is sufficient)
- Tap on QR code to enlarge to full screen (useful for scanning in dim environments)

### Screen 3: Invite Acceptance (Bob's View — App Installed)

**Layout:**
```
┌─────────────────────────────────┐
│                                 │
│         ┌─────────┐             │
│         │  Alice   │             │  (Avatar circle, 80pt)
│         │  avatar  │             │
│         └─────────┘             │
│                                 │
│         Alice                   │  (Display name, large bold)
│                                 │
│   wants to connect with you     │  (Subtitle, regular weight)
│                                 │
│  ┌─────────────────────────┐    │
│  │  🔒 End-to-end encrypted │   │  (Security badge, green)
│  │  Messages are secured    │   │
│  │  with TweetNaCl crypto   │   │
│  └─────────────────────────┘    │
│                                 │
│  ┌─────────────────────────┐    │
│  │  "Hey, let's chat on     │   │  (Personal note, if present)
│  │   QRChat!"               │   │  (Italic, card background)
│  └─────────────────────────┘    │
│                                 │
│  ╔═════════════════════════╗    │
│  ║      Accept             ║    │  (Primary CTA, green/accent)
│  ╚═════════════════════════╝    │
│                                 │
│  ┌─────────────────────────┐    │
│  │      Decline             │   │  (Secondary, text-only)
│  └─────────────────────────┘    │
│                                 │
│  ┌─────────────────────────┐    │
│  │  Block & Report          │   │  (Tertiary, red text,
│  └─────────────────────────┘    │   at bottom, small)
│                                 │
└─────────────────────────────────┘
```

**Design Notes:**
- Avatar uses a generated placeholder if Alice has not shared one (first letter + color based on name hash)
- Security badge is always visible — builds trust for encrypted messaging
- Personal note only appears if Alice included one during creation
- "Decline" does NOT notify Alice (privacy)
- "Block & Report" is visually de-emphasized but always accessible
- After tapping "Accept": brief key exchange animation (lock icon closing), then direct to new chat

### Screen 4: Invite Acceptance (Bob's View — App NOT Installed)

**Web Landing Page Layout:**
```
┌─────────────────────────────────┐
│                                 │
│      ┌──────────┐               │
│      │ QRChat   │               │  (App icon, 64pt)
│      │  Logo    │               │
│      └──────────┘               │
│                                 │
│      QRChat                     │  (App name, bold)
│   Encrypted Messaging           │  (Tagline)
│                                 │
│  ┌─────────────────────────┐    │
│  │  Alice invited you to    │   │
│  │  chat securely on QRChat │   │  (Invitation context)
│  └─────────────────────────┘    │
│                                 │
│  ┌─────────────────────────┐    │
│  │  🔒 End-to-end encrypted │   │
│  │  🚫 No phone number req  │   │
│  │  📱 QR code pairing      │   │
│  └─────────────────────────┘    │  (Feature highlights)
│                                 │
│  ╔═════════════════════════╗    │
│  ║  Download on App Store  ║    │  (Apple badge)
│  ╚═════════════════════════╝    │
│  ╔═════════════════════════╗    │
│  ║  Get it on Google Play  ║    │  (Google badge)
│  ╚═════════════════════════╝    │
│                                 │
│  After installing, this link    │
│  will connect you automatically │  (Deferred deep link note)
│                                 │
└─────────────────────────────────┘
```

**Technical Notes:**
- Use Universal Links (iOS) and App Links (Android) for seamless app-to-web fallback
- Store invite token in URL parameters: `qrchat.app/i/Xk9mP2`
- Deferred deep link: after install, first app launch reads the preserved invite token
- Web page must be lightweight, fast-loading, and work without JavaScript for maximum compatibility
- Include Open Graph meta tags for rich link previews in messaging apps

### Screen 5: Invite Link Management

**Layout:**
```
┌─────────────────────────────────┐
│  < Back        Invite Links     │
├─────────────────────────────────┤
│                                 │
│  Active Links (2)               │  (Section header)
│                                 │
│  ┌─────────────────────────┐    │
│  │ For Maria               │    │
│  │ Created Mar 24 at 14:30 │    │
│  │ Expires in 22h 15m  ⏱   │    │  (Countdown in orange)
│  │ Status: ● Pending       │    │  (Yellow dot)
│  │             ─── swipe ──│──► │  [Revoke] [Share Again]
│  └─────────────────────────┘    │
│                                 │
│  ┌─────────────────────────┐    │
│  │ Conference Link         │    │
│  │ Created Mar 23 at 09:00 │    │
│  │ Expires in 5d 18h   ⏱   │    │  (Countdown in green)
│  │ Status: ● 3 accepted    │    │  (Green dot)
│  │ Uses: 3 / 10            │    │  (Progress bar)
│  └─────────────────────────┘    │
│                                 │
│  Past Links (5)                 │  (Section header, collapsed)
│  ▶ Tap to expand                │
│                                 │
│  ┌─────────────────────────┐    │
│  │ Old link                │    │
│  │ Expired Mar 20          │    │  (Dimmed text)
│  │ Status: ● Expired       │    │  (Gray dot)
│  └─────────────────────────┘    │
│                                 │
│  ┌─────────────────────────┐    │
│  │ Test link               │    │
│  │ Revoked Mar 19          │    │  (Dimmed text)
│  │ Status: ● Revoked       │    │  (Red dot)
│  └─────────────────────────┘    │
│                                 │
│  ╔═════════════════════════╗    │
│  ║   + Create New Link     ║    │
│  ╚═════════════════════════╝    │
│                                 │
└─────────────────────────────────┘
```

**Status Indicators:**
| Status   | Color  | Dot  | Description                          |
|----------|--------|------|--------------------------------------|
| Pending  | Yellow | ● | Link created, not yet accepted         |
| Accepted | Green  | ● | Recipient accepted the invitation      |
| Expired  | Gray   | ● | Time limit reached, no longer valid    |
| Revoked  | Red    | ● | Manually revoked by sender             |
| Used     | Blue   | ● | One-time link, already consumed        |

**Countdown Timer Design:**
- > 24h remaining: show "Xd Xh" in green
- 1h - 24h remaining: show "Xh Xm" in orange
- < 1h remaining: show "Xm Xs" in red, pulse animation
- Expired: show "Expired" in gray, no timer

**Swipe Actions (iOS pattern):**
- Swipe left: [Revoke] (red) + [Delete] (gray)
- Swipe right: [Share Again] (accent color)

---

## 4. Error States

### 4.1 Expired Link

**Screen (Bob taps an expired link):**
```
┌─────────────────────────────────┐
│                                 │
│         ⏰                      │  (Clock icon, large)
│                                 │
│    This invite has expired      │  (Title, bold)
│                                 │
│    The link you followed is     │
│    no longer valid. Ask the     │  (Explanation)
│    sender for a new invite.     │
│                                 │
│  ╔═════════════════════════╗    │
│  ║   Open QRChat           ║    │  (If app installed)
│  ╚═════════════════════════╝    │
│                                 │
└─────────────────────────────────┘
```

### 4.2 Revoked Link

```
┌─────────────────────────────────┐
│                                 │
│         🚫                      │  (Block icon)
│                                 │
│    Invite withdrawn             │  (Title)
│                                 │
│    The sender cancelled this    │
│    invitation. If you still     │
│    want to connect, ask them    │
│    for a new link.              │
│                                 │
│  ╔═════════════════════════╗    │
│  ║   Open QRChat           ║    │
│  ╚═════════════════════════╝    │
│                                 │
└─────────────────────────────────┘
```

### 4.3 Already Used (One-Time Link)

```
┌─────────────────────────────────┐
│                                 │
│         ✓                       │  (Checkmark icon)
│                                 │
│    Link already used            │  (Title)
│                                 │
│    This one-time invite link    │
│    has already been accepted.   │
│    If this was you, open the    │
│    app to start chatting.       │
│                                 │
│  ╔═════════════════════════╗    │
│  ║   Open QRChat           ║    │
│  ╚═════════════════════════╝    │
│                                 │
└─────────────────────────────────┘
```

### 4.4 Invalid / Malformed Link

```
┌─────────────────────────────────┐
│                                 │
│         ❓                      │
│                                 │
│    Invalid invite link          │  (Title)
│                                 │
│    This link doesn't appear     │
│    to be a valid QRChat invite. │
│    Please check the link and    │
│    try again.                   │
│                                 │
│  ╔═════════════════════════╗    │
│  ║   Open QRChat           ║    │
│  ╚═════════════════════════╝    │
│                                 │
└─────────────────────────────────┘
```

### 4.5 Network Error During Acceptance

```
┌─────────────────────────────────┐
│                                 │
│         📡                      │
│                                 │
│    Connection problem           │  (Title)
│                                 │
│    Could not verify this        │
│    invite. Check your internet  │
│    connection and try again.    │
│                                 │
│  ╔═════════════════════════╗    │
│  ║   Try Again             ║    │  (Primary)
│  ╚═════════════════════════╝    │
│  ┌─────────────────────────┐    │
│  │   Cancel                │    │  (Secondary)
│  └─────────────────────────┘    │
│                                 │
└─────────────────────────────────┘
```

**Critical Design Rule (learned from Discord's mistake):** ALWAYS tell the user specifically what went wrong. Never combine multiple error types into a single generic message. Each error gets its own screen with a specific explanation and a specific action.

---

## 5. Notification UX

### 5.1 Push Notification: Invite Accepted

**When Bob accepts Alice's invite:**

```
┌─────────────────────────────────────┐
│ QRChat                     just now │
│ 🔒 Bob accepted your invite!       │
│ Tap to start chatting               │
└─────────────────────────────────────┘
```

**Best Practices (from research):**
- Personalize: use Bob's name, not "Someone accepted your invite"
- Actionable: tapping notification opens the new chat directly
- Lock screen safe: do not reveal message content, only the connection event
- Include the lock icon to reinforce encryption branding
- Timing: send immediately upon acceptance (this is a high-priority, awaited event)

### 5.2 In-App Notification: Invite Accepted

**Banner (appears at top of screen if Alice has app open):**
```
┌─────────────────────────────────────┐
│ ✓ Bob is now connected!   [Chat →] │
└─────────────────────────────────────┘
```
- Auto-dismiss after 5 seconds
- Tapping anywhere on the banner opens the new chat
- Also show a badge (1) on the Contacts/Chats tab

### 5.3 Push Notification: Invite Link Viewed (Optional)

```
┌─────────────────────────────────────┐
│ QRChat                       2m ago │
│ Someone viewed your invite link     │
│ Waiting for them to accept...       │
└─────────────────────────────────────┘
```

**Note:** This notification is optional and should be off by default for privacy. The "viewed" event could leak that the recipient has QRChat installed. Only enable if both parties have opted in.

### 5.4 Push Notification: Invite Expired

```
┌─────────────────────────────────────┐
│ QRChat                       1h ago │
│ Your invite link has expired        │
│ Tap to create a new one             │
└─────────────────────────────────────┘
```

- Send at the moment of expiration
- Tapping opens the Create Invite screen with the same settings pre-filled

---

## 6. Share Sheet Integration

### 6.1 Native Share Sheet (React Native)

**Implementation approach:**
- Use React Native's built-in `Share.share()` API for basic sharing
- Use `react-native-share` (v12.2.6, actively maintained) for advanced features like direct app targeting

**Share content format:**
```
Title: "QRChat Invite"
Message: "Join me on QRChat! Tap this link to connect securely: qrchat.app/i/Xk9mP2"
URL: "https://qrchat.app/i/Xk9mP2"
```

### 6.2 Custom Share Sheet (Pre-Native)

Before opening the native share sheet, show a custom bottom sheet with the most common sharing options:

```
┌─────────────────────────────────┐
│  Share invite link              │  (Title)
│                                 │
│  ┌──────┐ ┌──────┐ ┌──────┐   │
│  │ Copy │ │ SMS  │ │WhatsA│   │  (Row 1: most common)
│  │ Link │ │      │ │  pp  │   │
│  └──────┘ └──────┘ └──────┘   │
│  ┌──────┐ ┌──────┐ ┌──────┐   │
│  │Telegr│ │Email │ │ More │   │  (Row 2: additional)
│  │  am  │ │      │ │  ... │   │
│  └──────┘ └──────┘ └──────┘   │
│                                 │
└─────────────────────────────────┘
```

**Best Practices:**
- Detect installed apps dynamically (do not show Telegram icon if not installed)
- "Copy Link" is always first — it is the most universal action
- "More..." opens the native OS share sheet for full app list
- After sharing via any method, show a subtle confirmation: "Link shared!"
- Handle share sheet dismissal gracefully (user cancelled) — do NOT show an error

### 6.3 Link Preview (Open Graph Tags)

When the link is pasted in a messaging app, it should show a rich preview:

```
┌─────────────────────────────────┐
│ 🔒 QRChat Invite               │
│ Alice invited you to chat       │
│ securely on QRChat              │
│ qrchat.app                      │
└─────────────────────────────────┘
```

**Required OG meta tags on the web landing page:**
```html
<meta property="og:title" content="QRChat Invite" />
<meta property="og:description" content="You've been invited to chat securely on QRChat" />
<meta property="og:image" content="https://qrchat.app/og-invite.png" />
<meta property="og:url" content="https://qrchat.app/i/Xk9mP2" />
```

---

## 7. Deep Link & Deferred Deep Link Handling

### 7.1 Universal Links (iOS) / App Links (Android)

**URL scheme:** `https://qrchat.app/i/{token}`

**Routing logic:**
```
User taps link
  ├── App installed?
  │     ├── YES → Open app → Navigate to InviteAcceptScreen(token)
  │     └── NO  → Open web landing page
  │                 ├── User taps "Download"
  │                 ├── App Store / Play Store opens
  │                 ├── User installs and opens app
  │                 └── Deferred deep link → InviteAcceptScreen(token)
  │
  └── Link valid?
        ├── YES → Show acceptance screen
        ├── EXPIRED → Show expired error
        ├── REVOKED → Show revoked error
        ├── USED → Show already-used error
        └── INVALID → Show invalid error
```

### 7.2 Deferred Deep Link Implementation

**Options for React Native:**
- **Firebase Dynamic Links** (deprecated but functional — migrate to alternatives)
- **Adjust SDK** — mature, well-documented deferred deep link support
- **Branch.io** — industry standard for deferred deep links
- **Custom implementation:** Store invite token in clipboard or pasteboard; on first launch, check pasteboard for `qrchat.app/i/` pattern

**Recommended approach for QRChat (privacy-focused):**
- Use Apple's App Clip or a lightweight web intermediary
- Store the invite token server-side with a short-lived session cookie
- On first app launch, attempt to retrieve the token from the server
- Fallback: prompt user to paste or re-tap the link

---

## 8. i18n Considerations

### 8.1 String Catalog

All user-facing strings must be externalized. Key strings for the invite system:

| Key | en | ro | ru | fr |
|-----|----|----|----|----|
| `invite.create_title` | Create Invite | Creaza invitatie | Создать приглашение | Creer une invitation |
| `invite.one_time` | One-time use | Utilizare unica | Одноразовое | Usage unique |
| `invite.reusable` | Reusable | Reutilizabil | Многоразовое | Reutilisable |
| `invite.expires_after` | Expires after | Expira dupa | Истекает через | Expire apres |
| `invite.30min` | 30 minutes | 30 minute | 30 минут | 30 minutes |
| `invite.1hour` | 1 hour | 1 ora | 1 час | 1 heure |
| `invite.24hours` | 24 hours | 24 ore | 24 часа | 24 heures |
| `invite.7days` | 7 days | 7 zile | 7 дней | 7 jours |
| `invite.never` | Never | Niciodata | Никогда | Jamais |
| `invite.custom` | Custom | Personalizat | Свой срок | Personnalise |
| `invite.create_button` | Create Link | Creaza link | Создать ссылку | Creer le lien |
| `invite.share_title` | Share Link | Distribuie link | Поделиться ссылкой | Partager le lien |
| `invite.copy` | Copy Link | Copiaza link | Копировать | Copier le lien |
| `invite.copied` | Copied! | Copiat! | Скопировано! | Copie ! |
| `invite.share` | Share | Distribuie | Поделиться | Partager |
| `invite.done` | Done | Gata | Готово | Termine |
| `invite.expires_in` | Expires in {time} | Expira in {time} | Истекает через {time} | Expire dans {time} |
| `invite.accept_title` | {name} wants to connect | {name} vrea sa se conecteze | {name} хочет связаться | {name} veut se connecter |
| `invite.accept` | Accept | Accepta | Принять | Accepter |
| `invite.decline` | Decline | Refuza | Отклонить | Refuser |
| `invite.block` | Block & Report | Blocheaza si raporteaza | Заблокировать | Bloquer et signaler |
| `invite.encrypted` | End-to-end encrypted | Criptat end-to-end | Сквозное шифрование | Chiffre de bout en bout |
| `invite.status_pending` | Pending | In asteptare | Ожидание | En attente |
| `invite.status_accepted` | Accepted | Acceptat | Принято | Accepte |
| `invite.status_expired` | Expired | Expirat | Истекло | Expire |
| `invite.status_revoked` | Revoked | Revocat | Отозвано | Revoque |
| `invite.error_expired` | This invite has expired | Aceasta invitatie a expirat | Приглашение истекло | Cette invitation a expire |
| `invite.error_revoked` | Invite withdrawn | Invitatie retrasa | Приглашение отозвано | Invitation retiree |
| `invite.error_used` | Link already used | Link deja folosit | Ссылка уже использована | Lien deja utilise |
| `invite.error_invalid` | Invalid invite link | Link de invitatie invalid | Недействительная ссылка | Lien d'invitation invalide |
| `invite.error_network` | Connection problem | Problema de conexiune | Проблема с подключением | Probleme de connexion |
| `invite.notif_accepted` | {name} accepted your invite! | {name} a acceptat invitatia ta! | {name} принял(а) приглашение! | {name} a accepte votre invitation ! |
| `invite.notif_expired` | Your invite link has expired | Link-ul tau de invitatie a expirat | Ваша ссылка приглашения истекла | Votre lien d'invitation a expire |
| `invite.share_message` | Join me on QRChat! {link} | Alatura-te pe QRChat! {link} | Присоединяйся в QRChat! {link} | Rejoins-moi sur QRChat ! {link} |

### 8.2 Layout Considerations by Language

| Language | Avg. Text Expansion vs English | RTL | Special Characters |
|----------|-------------------------------|-----|-------------------|
| Romanian (ro) | +10-15% | No | a, i, s, t, a |
| Russian (ru) | +15-25% | No | Full Cyrillic set |
| French (fr) | +15-20% | No | e, a, c, o, u, etc. |

**Design Rules:**
- All buttons must accommodate 25% text expansion without truncation
- Use flexible height for labels (auto-sizing text containers)
- Test with Russian strings first (longest expansion)
- Avoid fixed-width containers for any text element
- Date/time formats: use `Intl.DateTimeFormat` or i18n library (not hardcoded)
- Pluralization: Russian has 3 plural forms (1, 2-4, 5+); French has 2; Romanian has 3 — use ICU MessageFormat

### 8.3 Gendered Language

Russian requires grammatical gender for some strings:
- "принял" (male) vs "приняла" (female) for "accepted"
- Solution: use gender-neutral constructions where possible, or use the ICU `{gender, select, ...}` syntax
- Fallback: "{name} accepted your invite" avoids the gender issue in most constructions

---

## 9. Security UX Considerations

### 9.1 Trust Signals on Acceptance Screen

Following Signal and SimpleX patterns:
- Always display the encryption badge on the invite acceptance screen
- Show a brief explanation: "Messages are secured with end-to-end encryption"
- Do NOT show the sender's phone number or any PII beyond display name
- Optional: show a security code / fingerprint that both parties can verify later

### 9.2 Link Token Security

- Tokens should be cryptographically random (min 128-bit entropy)
- Short URL format: `qrchat.app/i/` + base62-encoded token (8-12 chars)
- Server stores: token hash (not plaintext), creation time, expiration, usage count, creator ID
- One-time links: mark as consumed atomically (prevent race conditions)
- Rate limit: max 10 active links per user, max 50 link creations per day

### 9.3 Anti-Abuse

- "Block & Report" on every acceptance screen
- Revoke all links option in Settings (panic button)
- If a link is shared publicly and gets many hits, auto-disable and notify creator
- Do NOT reveal whether the sender exists or has an account (prevent enumeration)

---

## 10. Implementation Recommendations

### 10.1 Priority Order

1. **MVP (Phase 1):** One-time invite link creation + share via copy/native share + acceptance screen + push notification on accept
2. **Phase 2:** QR code display + scanning + expiration timer + link management list
3. **Phase 3:** Reusable links + usage limits + deferred deep links + web landing page
4. **Phase 4:** Direct share icons + "viewed" notifications + admin approval (if group invites added)

### 10.2 Tech Stack Alignment

| Feature | Library / Approach |
|---------|-------------------|
| Share sheet | `react-native-share` (v12.2.6) |
| QR generation | `react-native-qrcode-svg` |
| QR scanning | Already in QRChat (camera-based) |
| Deep links | React Navigation deep linking + Universal Links |
| Deferred deep links | Custom server-side token store (privacy-first) |
| Push notifications | Already in QRChat (FCM/APNs) |
| i18n | `react-i18next` or `i18n-js` (whichever QRChat uses) |
| Countdown timer | `useEffect` + `setInterval` with `Date.now()` diffing |

### 10.3 Data Model

```typescript
interface InviteLink {
  id: string;                    // UUID
  token: string;                 // Cryptographic random token (displayed in URL)
  creatorId: string;             // User who created the link
  type: 'one-time' | 'reusable';
  maxUses: number | null;        // null = unlimited
  usesCount: number;
  expiresAt: Date | null;        // null = never
  createdAt: Date;
  status: 'active' | 'expired' | 'revoked' | 'consumed';
  personalNote?: string;         // Stored locally only, not in the link
  acceptedBy?: string[];         // User IDs who accepted
}
```

### 10.4 Key Metrics to Track

- Link creation rate (per user, per day)
- Share method distribution (copy vs share sheet vs QR vs direct app)
- Time from link creation to acceptance (conversion speed)
- Acceptance rate (accepted / total links created)
- Error rate by type (expired, revoked, invalid, network)
- Drop-off at acceptance screen (opened but not accepted)

---

## Sources

- [Telegram Invite API Documentation](https://core.telegram.org/api/invites)
- [Signal: Phone Number Privacy and Usernames](https://signal.org/blog/phone-number-privacy-usernames/)
- [Signal: Phone Number Privacy — Support](https://support.signal.org/hc/en-us/articles/6712070553754-Phone-Number-Privacy-and-Usernames)
- [Signal: Group Link or QR Code — Support](https://support.signal.org/hc/en-us/articles/360051086971-Group-Link-or-QR-code)
- [SimpleX Chat — Making Connections](https://simplex.chat/docs/guide/making-connections.html)
- [PageFlows: Invite Teammates User Flow](https://pageflows.com/resources/invite-teammates-user-flow/)
- [Discord: Invalid Invite Links — Support](https://support.discord.com/hc/en-us/articles/360001556852-Invalid-Invite-Links)
- [WhatsApp: About Group Join Requests](https://faq.whatsapp.com/1110600769849613/?cms_platform=web)
- [WhatsApp: How to Create and Invite into a Group](https://faq.whatsapp.com/3242937609289432/?cms_platform=web)
- [Apple HIG: Collaboration and Sharing](https://developer.apple.com/design/human-interface-guidelines/collaboration-and-sharing)
- [Apple HIG: Activity Views](https://developer.apple.com/design/human-interface-guidelines/activity-views)
- [React Native Share API](https://reactnative.dev/docs/share)
- [react-native-share (npm)](https://www.npmjs.com/package/react-native-share)
- [Adjust: Deferred Deep Linking](https://dev.adjust.com/en/sdk/ios/features/deep-links/deferred/)
- [Phrase: 7 Key UI Design Principles for Multilingual Apps](https://phrase.com/blog/posts/ui-design-principles/)
- [UXCam: Push Notification UX Design Guide 2025](https://uxcam.com/blog/push-notification-guide/)
- [Smashing Magazine: Design Guidelines for Better Notifications UX](https://www.smashingmagazine.com/2025/07/design-guidelines-better-notifications-ux/)
- [Mobbin: Invite / Refer Friends Screen Patterns](https://mobbin.com/explore/mobile/screens/invite-refer-friends)
- [Keet: Peer-to-Peer Chat](https://keet.io/)
- [Telegram UI/UX Design Deep Dive](https://createbytes.com/insights/telegram-ui-ux-review-design-analysis)
