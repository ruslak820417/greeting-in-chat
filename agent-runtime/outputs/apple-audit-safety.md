# Apple App Store Review — Section 1: SAFETY Audit

**App:** QRChat v4.0.0 (build 16)
**Bundle ID:** com.ruslan.qrchat
**Auditor:** Safety Compliance Agent
**Date:** 2026-03-22
**Codebase:** /Users/ruslanconstantinovici/QRChat

---

## 1.1 Objectionable Content

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1.1.1 | App does not contain objectionable content | **PASS** | App is an E2E encrypted messenger — no pre-loaded content. All content is user-generated. |
| 1.1.2 | Report button on messages (long press) | **PASS** | `ChatScreen.tsx:1545-1564` — long press menu includes "Report" option for received messages. 4 categories: spam, harassment, inappropriate_content, other. Opens mailto to `ruscon2001@gmail.com` with message ID, timestamp, and reason. |
| 1.1.3 | Report button on contact profile | **PASS** | `ContactProfileScreen.tsx:502-532` — "Report User" button with red flag icon. Same 4 report categories. Sends email with user ID and display name. |
| 1.1.4 | Block user functional | **PASS** | `HomeScreen.tsx:216-225` — Block/Unblock via long press on conversation + swipe action (`HomeScreen.tsx:291-299`). Also available in `ContactsScreen.tsx:59-77`. Uses `Database.blockContact()` / `Database.unblockContact()`. Blocked contacts shown with ban icon and dimmed opacity. |
| 1.1.5 | Content filter | **N/A** | Not required for E2E encrypted messaging apps (Apple precedent: Signal, WhatsApp). Content cannot be read server-side. |

**1.1 Score: PASS**

---

## 1.2 User-Generated Content

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1.2.1 | Report mechanism functional | **PASS** | Dual report: (1) Email-based report from ChatScreen + ContactProfileScreen via `mailto:ruscon2001@gmail.com`. (2) Server-side `POST /report` endpoint (`server/index.js:272-299`) stores reports to `qrchat_reports.json` with reporterId, reportedUserId, messageId, reason, timestamp. |
| 1.2.2 | Block mechanism functional | **PASS** | `Database.blockContact()` sets `isBlocked` flag. Blocked users filtered from group creation (`CreateGroupScreen.tsx:34`), pings skipped (`HomeScreen.tsx:138`). Visual indicator (ban icon, dimmed). Reversible (unblock available). |
| 1.2.3 | Ability to remove objectionable content | **PASS** | Users can delete messages locally ("Delete for me") and remotely ("Delete for all" via `MessagingService.sendDeleteMessage()`). Blocked contacts' messages not displayed. |
| 1.2.4 | Terms of Service accepted at onboarding | **PASS** | `SetupScreen.tsx:33,51-54,202-219` — Checkbox "I agree to the Terms of Service and Privacy Policy" (`agreedToTerms` state). Button disabled until checked. Alert shown if user tries to proceed without accepting. Localized in 4 languages (en/ro/ru/fr). |
| 1.2.5 | Contact info visible | **PASS** | `SupportScreen.tsx:17-19` — `ruscon2001@gmail.com` displayed with mail icon. Also in `TermsScreen.tsx` via `terms.contactBody` i18n key. |
| 1.2.6 | Age rating 17+ set | **PASS** | `PROJECT_STATUS.md` confirms 17+ rating. ToS eligibility: "You must be at least 13 years old" (`en.json:527`). 17+ rating appropriate for UGC chat without automated moderation. |
| 1.2.7 | Account deletion functional | **PASS** | `SettingsScreen.tsx:515-526` — "Delete everything" with destructive confirmation dialog. Calls `MessagingService.destroy()` then wipes all data (keys, contacts, messages). Compliant with Apple's account deletion requirement (effective June 2022). |

**1.2 Score: PASS**

---

## 1.3 Kids Category

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1.3.1 | App NOT in Kids Category | **PASS** | App is rated 17+, targets adult users. Not a children's app. |
| 1.3.2 | Does not collect data from minors | **PASS** | No personal data collection at all — no phone number, no email, no age verification needed. Identity is a locally-generated cryptographic keypair. ToS states minimum age requirement of 13. |

**1.3 Score: PASS**

---

## 1.4 Physical Harm

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1.4.1 | App does not encourage violence or physical harm | **PASS** | App is a communication tool. No gamification of harmful behavior. Prohibited uses explicitly listed in ToS (`en.json:531`): no harassment, threats, illegal content, malware distribution. |
| 1.4.2 | No medical/health features without disclaimers | **N/A** | App has no health-related functionality. |
| 1.4.3 | No dangerous instructions | **PASS** | No instructional content. Pure messaging functionality. |

**1.4 Score: PASS**

---

## 1.5 Developer Information

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1.5.1 | Real contact email | **PASS** | `ruscon2001@gmail.com` — displayed in `SupportScreen.tsx:18`, used in report flows, referenced in Privacy Policy and Terms. |
| 1.5.2 | Developer name | **PASS** | Ruslan Constantinovici — in `SupportScreen.tsx:101` copyright, `PROJECT_STATUS.md`, and App Store metadata. |
| 1.5.3 | Country/Region | **PASS** | Republic of Moldova, Chisinau — in `PROJECT_STATUS.md`. |
| 1.5.4 | Privacy Policy URL accessible | **WARNING** | `Info.plist:82-83` references `https://exciting-success-production-d272.up.railway.app/privacy`. Privacy HTML exists in 4 languages (`docs/privacy.html`, `privacy-ro.html`, `privacy-ru.html`, `privacy-fr.html`). However, `PROJECT_STATUS.md` notes Privacy Policy hosting via GitHub Pages is still pending (item #6 in remaining tasks). The Railway URL may serve the policy but this needs verification. |
| 1.5.5 | Apple ID registered | **PASS** | `ruscon2002@mail.ru` — Apple Developer account referenced. |

**1.5 Score: PASS (with 1 WARNING)**

---

## Overall Safety Score

| Section | Result |
|---------|--------|
| 1.1 Objectionable Content | **PASS** |
| 1.2 User-Generated Content | **PASS** |
| 1.3 Kids Category | **PASS** |
| 1.4 Physical Harm | **PASS** |
| 1.5 Developer Information | **PASS** (1 WARNING) |

### **OVERALL: PASS**

---

## Warnings & Recommendations

### WARNING: Privacy Policy URL Hosting (1.5.4)
- **Issue:** Privacy Policy files exist locally but GitHub Pages hosting is not yet active. The `Info.plist` references Railway URL which may or may not serve the HTML files.
- **Risk:** Apple requires a working, publicly accessible Privacy Policy URL. If the URL returns 404, the app will be rejected.
- **Fix:** Either (a) deploy `docs/privacy.html` to GitHub Pages and update `Info.plist`, or (b) confirm Railway serves the privacy page at the referenced URL.

### Minor Observations (non-blocking)

1. **Report mechanism is email-based:** The primary report flow opens a `mailto:` link. While functional, Apple may prefer an in-app report submission. The server-side `POST /report` endpoint exists but the client currently uses email instead of calling it. Consider wiring the client report to hit the API endpoint as well, for a more robust audit trail.

2. **Block not on ContactProfileScreen:** Block is available via HomeScreen (long press + swipe) and ContactsScreen, but NOT on `ContactProfileScreen.tsx`. Apple reviewers may look for it there. Consider adding a Block button to the contact profile for completeness.

3. **ToS age minimum is 13, rating is 17+:** The ToS says "at least 13 years old" (`en.json:527`) but the app rating is 17+. These should be aligned — either update ToS to say 17+ or justify the discrepancy. Recommendation: update ToS to say 17+.

4. **No automated content moderation disclaimer:** Since messages are E2E encrypted and cannot be monitored server-side, consider adding a brief note in the app description or review notes clarifying this to Apple reviewers (as Signal and similar apps do).
