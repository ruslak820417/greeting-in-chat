# SimpleX Chat -- UX & Product Research Report

**Date:** 2026-03-30
**Current SimpleX version:** v6.4.1 (July 2025)
**App Store rating:** 4.4/5 (iOS)
**Tagline:** "Private and secure messenger without any user IDs (not even random)"

---

## 1. User Onboarding

### First Launch Flow (step by step)

1. **Create chat profile** -- enter display name (required) and full name (optional). Profile is stored locally only, never on any server. Profile image is optional.
2. **Choose notification mode** -- three options:
   - **Instant** (highest battery, most convenient -- uses persistent connection)
   - **Periodic** (background fetch every few minutes -- iOS tradeoff is privacy vs convenience)
   - **When app is running** (most private, no background notifications)
3. **"Chat with the developers"** button appears -- a one-tap way to test the app immediately. This button disappears after the first connection is made.
4. User lands on an empty chat list with a floating "+" button to create connections.

### Profile Setup

- Display name + optional full name + optional profile image
- Everything is local-only -- zero server storage
- You can create unlimited additional profiles later (Settings > Your chat profiles > + Add profile)
- Each profile maintains its own independent contact list and group memberships
- Profiles function as completely separate identities

### How Fast Is Onboarding?

Under 30 seconds from install to ready-to-chat. No phone number, no email, no username registration, no verification code. Just type a name and go.

---

## 2. Contact Management

### Connection Invitation Methods

SimpleX has two fundamentally different ways to connect:

**A) One-time invitation link:**
- Tap "+" > "Create one-time invitation link"
- Generates a link + QR code
- Can only be used once, then expires
- Best for: sharing in-person or via video call
- Both parties know context of who they are connecting to
- Uses double ratchet encryption from the first message
- As of v6.4: links are now short (< 80 characters), e.g. `https://smp6.simplex.im/a#lrdvu2d8A1GumSmoKb2krQmtKhWXq-tyGpHuM7aMwsw`
- QR codes are now small enough to fit on a business card

**B) SimpleX address (reusable long-term address):**
- Created once, shared publicly (social media bio, email signature, website)
- Can be used by unlimited people to connect
- Incoming requests appear as connection requests that can be accepted or rejected
- Can configure auto-accept with optional welcome message
- Can be deleted without breaking existing connections made through it
- Initial connection does NOT use double ratchet (slightly lower security than one-time links)

### New Connection Flow (v6.4+)

Major UX improvement in v6.4:
- When scanning a link, you **instantly see the contact's name and profile image** before connecting
- You **choose which profile to use** (or connect incognito)
- Conversation opens **immediately** -- messages send even if contact is offline
- Links are now short enough for social media bios
- If a link is intercepted, it becomes inaccessible to the intended recipient (security alert)

### Contact Verification

- Each connection has a **security code** (SHA256 hash of combined public keys)
- Verification methods: scan QR code from contact's screen, visual comparison, or read aloud over voice call
- Verified contacts are **marked as verified** in the UI (shield icon)
- Prevents man-in-the-middle attacks
- You can also tap "mark verified" if you trust the contact's confirmation

### Contact Aliases

- You can attach an alias to an invitation link as soon as you share it, to identify the contact before they accept
- Contact names can be edited locally

---

## 3. Messaging Features

### Message Types

| Type | Support | Details |
|------|---------|---------|
| Text | Yes | Full markdown support, markdown hyperlinks (v6.4+) |
| Images | Yes | Camera, gallery, clipboard (iOS) |
| Video | Yes | Supported via XFTP |
| Voice messages | Yes | Up to 5 minutes, 32kbps quality, playback slider |
| Files | Yes | Up to 1GB via XFTP protocol |
| GIFs/Stickers | Yes | Via third-party keyboards (GIPHY on iOS, native on Android 13+) |
| Live messages | Yes | Real-time typing visible to recipient (unique feature) |

### File Transfer (XFTP Protocol)

- Files up to 1GB
- Sent asynchronously -- sender doesn't need to be online for recipient to download
- Files split into encrypted chunks (256KB, 1MB, 4MB) across multiple relays
- Chunks stored temporarily (48 hours) then auto-deleted
- Relay servers see only anonymous chunks, no metadata
- 25MB file sends in ~3 seconds, 1GB in ~2 minutes

### Disappearing Messages

- Time range: **1 second to 3 months** (granular selection)
- Requires mutual consent -- both parties must agree to enable
- For sender: timer starts from send time
- For recipient: timer starts from read time
- Can set per-message timing by long-pressing the send button
- Group owners can enable for entire groups
- Can enable disappearing messages for all new contacts automatically (v6.4.1+)

### Message Reactions

- 6 available reactions: thumbs up, thumbs down, smile, tear, heart, rocket
- Maximum 3 reactions per message per user
- Deliberately limited set (design decision for simplicity)

### Reply/Quote

- Long-press message > choose "Reply" to quote and reply inline
- Quoted message appears above the reply with context

### Edit Messages

- Long-press > Edit
- Edit history is visible (shows when messages were sent, received, edited, deleted)
- Original message content remains recoverable in history

### Delete Messages

- **Delete for me:** removes locally only
- **Mark as deleted:** within 24 hours, message shows as "deleted message" but recipient can reveal original
- **Delete for everyone:** both parties must enable in Contact preferences, within 24 hours of sending
- Group admins can delete others' messages

### Read Receipts

**SimpleX deliberately does NOT have read receipts.** The developers consider read receipts an "anti-feature" that hurts user relations and only benefits app developers. Not planned even as opt-in. Recommendation: use a reaction to signal you've read a message.

### Delivery Receipts

- Double-tick system (server received + delivered to device)
- Optional -- can be disabled per contact
- Enabled by default

### Typing Indicators

**SimpleX does NOT have typing indicators.** Considered an invasive feature alongside read receipts and presence notifications.

### Message Search

- Available in conversations
- v6.3 added quick navigation from search results to the point in conversation where the message was sent
- Can jump from forwarded messages to their original source

### Message Forwarding

- Messages can be forwarded to other contacts/groups
- When forwarding media, file names are changed to match forwarding time (privacy: no metadata leakage)

### Live Messages (Unique Feature)

- Press the lightning/bolt button to start a live message
- Recipients see text appearing in real-time as you type
- Updates send every few seconds (complete words only)
- Press checkmark to finalize
- Can convert already-started messages to live format via long-press send
- Unique to SimpleX -- not found in Signal, Telegram, or WhatsApp

---

## 4. Groups (Secret Groups)

### Creating Groups

- Tap "+" > "Create secret group"
- Enter group display name
- Tap "Create"
- Creator is automatically assigned Owner role

### Group Invitation Process

- Owners/admins add members directly or generate shareable invite links
- Members receive invitation in conversation list
- Can accept from conversation list or within the conversation
- v6.4.1: Groups can enable member review ("knocking") -- new members must be approved

### Roles (5 levels, v6.4+)

| Role | Permissions |
|------|------------|
| **Owner** | Full control: change group preferences, manage all roles, add owners |
| **Admin** | Delete others' messages, remove members, add members (up to admin role) |
| **Moderator** (new in v6.4) | Approve members in review, moderate messages, block members. Cannot add/permanently remove members |
| **Member** | Send messages, delete own messages |
| **Observer** | Read-only (can delete/mark their own previously sent messages) |

### Group Size

- No hard numerical limit documented
- Every message and file is sent separately to every member (P2P mesh)
- Practical limit: designed for smaller groups due to this architecture
- Large communities are a 2025-2027 roadmap item

### Group Encryption

- End-to-end encrypted between each pair of members
- Each member connection uses separate encryption keys
- Quantum-resistant encryption available

### Group Moderation Features (v6.3-6.4)

- **Captcha verification:** owners can require captcha before joining
- **Profanity filter:** reject members with profanity in usernames
- **Private reports:** members can report messages/members to moderators privately
- **Multi-member actions:** moderators can bulk-adjust roles, block, or remove members
- **Member feedback:** mini-group conversations where admins/moderators can talk to a specific member
- **Welcome messages:** owner-created messages shown to new joiners
- **Content restrictions:** owners can prohibit file/media sharing
- **Member mentions:** type "@" to mention members; notifications for mentions and replies
- **Mentions-only notifications:** switch group to only notify on mentions

---

## 5. Calls

### Technology

- End-to-end encrypted WebRTC
- iOS uses native WebRTC library (not web view)
- Routed via TURN relay server by default (IP address hidden)
- Optional P2P mode (faster but reveals IP to contact)
- Custom WebRTC ICE server configuration supported

### Call Screen UI

- **Audio call:** tap phone icon at top of conversation
- **Video call:** tap three-dot menu > "Video call"
- Can switch between audio and video during call
- iOS: native CallKit interface by default (incoming calls on lock screen)
- Android: three lock screen options -- Disable, Show (unlock required), Accept (direct from lock screen)

### Platform-Specific Features

- **Android:** Bluetooth headphone support, volume control in video calls, proximity sensor during audio calls
- **iOS:** CallKit integration for native call experience, optional call history inclusion
- **Both:** end-to-end encrypted, compatible across platforms

### Limitations

- **No group calls** (1-to-1 only)
- No call quality indicators documented
- No reconnection for dropped calls (feature requested in GitHub issues)
- Call notifications can be slow (reported delay of ~1 minute)
- Audio input selection reportedly broken on iOS with some Bluetooth devices

### Missed Calls & Call History

- iOS CallKit optionally includes calls in phone call history
- No dedicated in-app call history feature documented
- Missed calls appear as events in the chat conversation

---

## 6. Privacy Features (User-Facing)

### Incognito Mode

- Toggle in app settings
- When enabled, a **random profile name** is generated for each new contact or group
- Your real profile name and image are never shared
- All incognito contacts appear in the same chat list as regular contacts
- Unique to SimpleX -- no equivalent in Signal, WhatsApp, Telegram
- v6.4+: when connecting via link, you can choose to connect incognito on a per-connection basis

### Hidden Profiles

- Any chat profile can be hidden with a password
- Hidden profiles are invisible in the profile list
- To reveal: enter the full password in the search bar
- Use case: anonymous tips to journalists, activism, sensitive identities
- Long-press (Android) or swipe (iOS) on profile to hide/unhide

### SimpleX Lock (App Lock)

- Biometric (fingerprint/Face ID) or PIN/passcode
- Required to open app or resume after 30 seconds in background
- Required for security-sensitive actions within the app

### Self-Destruct Passcode

- Set up a secondary passcode that **wipes all app data** when entered
- Designed for coercion scenarios (border crossings, arrests)
- After wipe, app opens with a fresh empty profile (optionally named)
- Setup: Settings > Privacy & security > SimpleX Lock > enable Passcode > enable Self-destruct

### Screen Protection

- Hides app content in recent apps/app switcher (enabled by default)
- Android: also prevents screenshots
- iOS: blurs app preview

### Network Privacy

- **SOCKS5 proxy support** for Tor routing
  - Android: enable "Use SOCKS proxy" on port 9050
  - iOS: via Orbot (acts as VPN provider)
- **Use .onion hosts** option for direct Tor routing
- **Transport isolation** (BETA): each contact uses a separate TCP connection (and separate Tor circuit)
- **Private message routing** (v5.8+): 2-hop onion routing where sender picks first relay, recipient picks second. Neither side sees the other's IP address
- **.onion service** available: `isdb4l77sjqoy2qq7ipum6x3at6hyn3jmxfx4zdhc72ufbmuq4ilwkqd.onion`

### Database Export/Import (Device Migration)

- Database is portable, encrypted, self-contained
- Export: Settings > Database passphrase & export > Export
- Must set database passphrase manually first (default is random)
- Import on new device (cross-platform: Android to iOS, mobile to desktop CLI)
- **Simplified migration (v5.6+):** archive and upload to XFTP servers in chunks, scan QR code on new device
- **Critical:** cannot use same database on two devices simultaneously (breaks connections)
- **Critical:** always use latest database version (old backups will break connections)
- No per-profile migration -- entire database moves as one unit
- Lost passphrase = unrecoverable data

### Additional Privacy Settings

- **Chat retention period:** auto-delete messages after 1 day, 1 week, 1 month, or 1 year (per conversation)
- **Private media file names:** file names changed on forwarding to hide metadata
- **Automatic message deletion:** per-profile setting for local message cleanup
- **File/media storage cleanup:** delete all files without deleting messages
- **Link tracking removal:** option to strip tracking parameters from shared links (v6.4+)

---

## 7. Customization

### Themes

- **Three base themes:** Light, Dark, SimpleX
- **Custom themes:** adjust accent color, background, transparency
- **Wallpapers:** preset options or custom images (Android & desktop)
- **Per-profile themes:** different visual identity per chat profile (helps avoid sending to wrong identity)
- **Per-conversation themes:** different colors/wallpaper for specific contacts
- **Theme export/sharing:** themes can be exported and shared with others

### Chat Colors

- Accent color customizable globally
- Different themes per profile effectively give different colors per identity group
- Per-conversation wallpaper/theme support

### Notification Settings

- Three modes: instant, periodic, when app is running
- Message preview toggle (show/hide content in notifications)
- Per-contact muting (long-press to mute)
- Groups: can switch to "mentions only" notifications (v6.3+)
- Android: may require disabling power optimization

### App Icon

- Customizable app icon (selectable from settings)

### Font Size

- Adjustable font size

### Language Support

- **34+ languages** via community translations on Weblate
- **Fully supported:** Czech, German, Spanish, French, Italian, Dutch, Russian, Chinese
- **Newer additions:** Catalan, Indonesian, Romanian, Vietnamese, Persian
- **In progress:** Arabic, Japanese, Korean, Portuguese, and others
- Language selectable in app settings independently from system language
- Community testing groups per language (#SimpleX-DE, #SimpleX-ES, #SimpleX-FR, #SimpleX-RU, #SimpleX-IT)

---

## 8. Desktop & Multi-Device

### How Desktop Linking Works

1. Install desktop app (macOS, Windows, Linux) and create a profile
2. In desktop app: Settings > "Link a mobile" -- shows QR code
3. In mobile app: Settings > "Use from desktop" -- scan QR code
4. Verify session code matches on both devices
5. Connection established via TLS 1.3 + quantum-resistant encryption (XRCP protocol)
6. Subsequent reconnections are faster (desktop broadcasts encrypted session address)

### Companion, Not Standalone

- Desktop is a **companion device** -- it remotely controls the mobile app
- While using from desktop, you **cannot use the mobile app simultaneously**
- Android: mobile app can run in background during desktop session
- iOS: mobile app must remain in foreground
- You do **not** have a full copy of data on desktop (privacy advantage -- desktops typically have lower security)

### Sync Between Devices

- Not true sync -- it's **remote control**
- Files sent/received/viewed from desktop are saved locally on desktop (encrypted by default, except videos)
- Unlinking removes synced files from desktop
- Both devices must be on the **same local network**

### What's Missing

- No true multi-device with independent databases (feature requested, not yet implemented)
- No cloud sync between devices
- Cannot use mobile + desktop simultaneously

---

## 9. What SimpleX Does BETTER Than Most Messengers

### 1. Zero Identity Architecture

The single most distinctive feature: **no user identifiers whatsoever** -- not even random ones. No phone number, no email, no username. This is unprecedented in messaging. Signal requires phone number, Session uses public keys, Matrix uses usernames. SimpleX uses none.

### 2. Incognito Mode (Unique Feature)

No other messenger offers automatic random identity generation per contact. This is a killer feature for: journalists receiving anonymous tips, activists, whistleblowers, anyone wanting complete compartmentalization without managing multiple accounts manually.

### 3. Multiple Chat Profiles

True identity separation within one app. Each profile has its own contacts, groups, and visual theme. Two taps to switch. Signal and WhatsApp offer nothing comparable. Telegram has "anonymous mode" in groups but nothing this comprehensive.

### 4. Self-Destruct Passcode

While some apps have app lock, SimpleX's self-destruct passcode that wipes all data under coercion is rare and extremely valuable for high-risk users.

### 5. Live Messages

Unique feature -- recipients see text appearing in real-time as you type, character by character. No other major messenger has this.

### 6. No Metadata Leakage by Design

- Unidirectional message queues prevent social graph mapping
- Packet padding defeats size analysis
- Message mixing prevents timing analysis
- Private message routing (2-hop onion routing) hides IP from both relays
- Transport isolation (one TCP connection per contact)

### 7. Decentralized Infrastructure Without Blockchain

Anyone can run their own SMP/XFTP relay servers. No central authority, no blockchain complexity, no tokens. Users can configure custom servers in settings.

### 8. Connection Security That's Actually Verifiable

Security code verification with QR scanning, visual comparison, or voice call verification. When verified, contacts are marked in the UI -- simple and accessible.

### 9. Per-Conversation Visual Themes

Practical privacy feature: different visual themes per identity/profile help prevent accidentally sending messages to the wrong person when managing multiple identities.

### 10. Short Connection Links (v6.4+)

Connection links are now < 80 characters, fit on business cards as QR codes, and work in social media bios. This solved a major UX pain point.

### 11. Privacy-Respecting Design Decisions

- **No read receipts by design** (considered harmful to relationships)
- **No typing indicators** (considered invasive)
- **No online/last seen status** (no presence tracking)
- These are deliberate philosophical choices, not missing features

---

## 10. Known Weaknesses & User Complaints

### Notification Reliability

The most common complaint across all review sources. Messages can arrive 20+ minutes late. Notification modes involve tradeoffs between privacy and reliability. This is the biggest barrier to daily-driver adoption.

### Call Quality

Audio/video calls are described as "in beta and a bit flaky." Issues include:
- Slow call notifications (~1 minute delay)
- No ringing tone sometimes
- Audio delay after pickup
- Bluetooth device compatibility issues on iOS
- No automatic reconnection for dropped calls
- No group calls

### Desktop Experience

- Requires same local network (no remote access)
- Mobile app blocked during desktop session (iOS must stay in foreground)
- Not true multi-device -- just remote control

### Group Scalability

- P2P mesh architecture means every message is sent N times (once per member)
- Impractical for large groups (100+ members)
- Large community support is on the 2025-2027 roadmap

### Onboarding Friction

- Adding first contact requires out-of-band link/QR sharing
- No username search/directory for discovery
- Complex for non-technical users
- v6.4's improvements significantly help but the fundamental model requires link exchange

### Occasional Bugs

- iOS keyboard autofill issues since iOS 17
- App freezing reported when tapping text entry
- Stability issues with frequent crashes mentioned in some reviews

---

## 11. Competitive Positioning

| Feature | SimpleX | Signal | Telegram | WhatsApp | Session |
|---------|---------|--------|----------|----------|---------|
| No phone/email required | YES | No | No | No | YES |
| No user IDs at all | YES | No | No | No | No (public key) |
| Multiple profiles | YES | No | No | No | No |
| Incognito mode | YES | No | No | No | No |
| Self-destruct passcode | YES | No | No | No | No |
| E2E encryption default | YES | YES | No (opt-in) | YES | YES |
| Quantum-resistant E2E | YES | YES | No | No | No |
| Group calls | No | YES | YES | YES | No |
| Read receipts | No (by design) | YES | YES | YES | No |
| Custom servers | YES | No | No | No | Community |
| Desktop standalone | No (companion) | YES | YES | Companion | YES |
| File size limit | 1GB | 100MB | 2GB | 100MB | 10MB |
| Open source | YES | YES | Client only | No | YES |

---

## Key Takeaways for QRChat

1. **Zero-identity onboarding is a massive differentiator** -- QRChat already has QR-code-based connections which is philosophically similar
2. **Incognito mode is a killer feature** worth considering -- random identity per contact
3. **No read receipts is a deliberate philosophical stance** -- worth considering whether to include or omit
4. **Self-destruct passcode** is low-effort, high-value for privacy-focused users
5. **Per-conversation themes** serve a practical privacy purpose, not just aesthetics
6. **Short connection links (< 80 chars)** solve a real UX problem SimpleX struggled with for years
7. **Live messages** are a unique differentiator -- novel but niche
8. **Notification reliability** is the biggest risk for privacy messengers -- must be solved for daily use
9. **Group scalability** via P2P mesh hits walls -- QRChat should plan architecture for this early
10. **Desktop as companion** (not standalone) is a valid architecture choice that improves security

---

## Sources

- [SimpleX Chat User Guide](https://simplex.chat/docs/guide/readme.html)
- [Making Connections](https://simplex.chat/docs/guide/making-connections.html)
- [Chat Profiles](https://simplex.chat/docs/guide/chat-profiles.html)
- [Privacy & Security](https://simplex.chat/docs/guide/privacy-security.html)
- [App Settings](https://simplex.chat/docs/guide/app-settings.html)
- [Audio & Video Calls](https://simplex.chat/docs/guide/audio-video-calls.html)
- [Secret Groups](https://simplex.chat/docs/guide/secret-groups.html)
- [Sending Messages](https://simplex.chat/docs/guide/send-messages.html)
- [Managing Data](https://simplex.chat/docs/guide/managing-data.html)
- [v6.4.1 Release Blog](https://simplex.chat/blog/20250729-simplex-chat-v6-4-1-welcome-contacts-protect-groups-app-security.html)
- [v6.4-beta New Connection Experience](https://simplex.chat/blog/20250703-simplex-network-protocol-extension-for-securely-connecting-people.html)
- [v6.3 Release Blog](https://simplex.chat/blog/20250308-simplex-chat-v6-3-new-user-experience-safety-in-public-groups.html)
- [v5.8 Chat Themes & Private Routing](https://simplex.chat/blog/20240604-simplex-chat-v5.8-private-message-routing-chat-themes.html)
- [v5.4 Desktop Linking](https://simplex.chat/blog/20231125-simplex-chat-v5-4-link-mobile-desktop-quantum-resistant-better-groups.html)
- [v5.1 Message Reactions](https://simplex.chat/blog/20230523-simplex-chat-v5-1-message-reactions-self-destruct-passcode.html)
- [v4.4 Disappearing Messages](https://simplex.chat/blog/20230103-simplex-chat-v4.4-disappearing-messages.html)
- [XFTP Protocol Blog](https://simplex.chat/blog/20230301-simplex-file-transfer-protocol.html)
- [Freedom.tech Review](https://freedom.tech/simplex-chat-review/)
- [DarwinDynamic Review 2026](https://darwindynamic.com/simplex-chat-review-2026/)
- [ItsFoss Review](https://news.itsfoss.com/simplex-chat/)
- [Translations/Weblate](https://hosted.weblate.org/projects/simplex-chat/)
- [SimpleX Chat GitHub](https://github.com/simplex-chat/simplex-chat)
- [App Store Listing](https://apps.apple.com/us/app/simplex-chat-secure-messenger/id1605771084)
- [Google Play Listing](https://play.google.com/store/apps/details?id=chat.simplex.app)
