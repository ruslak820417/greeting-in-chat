# Apple App Store Audit — Section 3 (Business) & Section 5 (Legal)

**App:** QRChat v3.0.6 (preparing v4.0.0)
**Bundle ID:** com.ruslanconstantinovici.QRChat
**Auditor:** apple-legal agent
**Date:** 2026-03-22
**Server:** https://exciting-success-production-d272.up.railway.app

---

## EXECUTIVE SUMMARY

| Area | Verdict | Risk |
|------|---------|------|
| 3.1 In-App Purchase | FAIL — BLOCKER | REJECTION GUARANTEED |
| 3.2 Other Business Models | PASS | LOW |
| 5.2 Intellectual Property | PASS (with notes) | LOW |
| 5.5 Developer Code of Conduct | PASS | NONE |
| Export Compliance | PARTIAL — needs fix | MEDIUM |
| Terms of Service | PASS | LOW |
| Review Notes | PASS (with notes) | LOW |

**Overall: NOT READY FOR SUBMISSION** — 1 guaranteed rejection blocker, 2 medium-risk issues.

---

## 3.1 PAYMENTS — IN-APP PURCHASE

### CRITICAL BLOCKER: StoreKit/IAP NOT IMPLEMENTED

**Verdict: FAIL — GUARANTEED REJECTION**

QRChat has a paid upgrade feature ("QRChat Unlimited" at $2.99) that unlocks unlimited contacts (free tier: 10 contacts). This is a **digital content/feature unlock** and MUST use Apple In-App Purchase per guideline 3.1.

**Evidence:**

1. **UpgradeScreen.tsx:57-63** — The "Purchase" button is a dead placeholder:
   ```typescript
   const handlePurchase = () => {
     // TODO: StoreKit 2 implementare
     Alert.alert(t('upgrade.purchaseTitle'), t('upgrade.purchaseNotReady'));
   };
   ```
   The button displays $2.99 but shows "not ready" alert when tapped.

2. **LicensingService.ts:11-12** — Explicitly marked as TODO:
   ```
   * 2. Apple In-App Purchase (StoreKit 2) — TODO
   ```

3. **LicensingService.ts:124-127** — `activateWithReceipt()` is a non-functional stub:
   ```typescript
   async activateWithReceipt(_receiptData: string): Promise<...> {
     return { success: false, message: 'In-App Purchase not yet available' };
   }
   ```

4. **package.json** — No IAP library installed:
   - `react-native-iap` — NOT FOUND
   - `react-native-purchases` (RevenueCat) — NOT FOUND
   - `expo-in-app-purchases` — NOT FOUND
   - No StoreKit bridge of any kind.

5. **server/licensing.js** — The ONLY working activation method is server-side promo codes, which completely bypass Apple IAP.

### Why This Causes Rejection

- **Guideline 3.1**: "If you want to unlock features or functionality within your app, you must use in-app purchase."
- **Guideline 3.1.1**: "In-App Purchase: Digital content or services consumed within the app must be purchased through IAP."
- Unlimited contacts = digital feature unlock = MUST be IAP.
- The promo code system (`server/licensing.js`) activates the paid feature without Apple seeing any revenue. Apple takes 30% commission on all digital goods — this system gives them 0%.
- Even if the Purchase button shows "not ready," submitting an app with a $2.99 price displayed and a non-functional purchase flow is itself a rejection reason (broken functionality, guideline 2.1).

### Required Actions

- [ ] Install `react-native-iap` or `react-native-purchases` (RevenueCat recommended for simpler integration)
- [ ] Create Non-Consumable IAP product in App Store Connect ($2.99 "QRChat Unlimited")
- [ ] Implement StoreKit 2 purchase flow in `UpgradeScreen.tsx`
- [ ] Implement receipt validation (server-side recommended via `server/licensing.js`)
- [ ] Add "Restore Purchases" button (required by Apple for non-consumable IAP)
- [ ] Keep promo code system as secondary method (Apple allows promo codes alongside IAP, but IAP must be primary)
- [ ] Add EULA / Licensed Agreement URL in App Store Connect

### 3.1.1 In-App Purchase (Subchecks)

| Check | Status |
|-------|--------|
| Digital content/features via IAP | FAIL — not implemented |
| Physical goods/services via other methods | N/A |
| Non-consumable IAP (one-time unlock) | NOT CONFIGURED |
| "Restore Purchases" button | MISSING |
| Receipt validation | NOT IMPLEMENTED |

### 3.1.2 Subscriptions

N/A — QRChat uses one-time purchase, not subscription.

---

## 3.2 OTHER BUSINESS MODEL ISSUES

**Verdict: PASS**

| Check | Status | Notes |
|-------|--------|-------|
| External payment links | NONE FOUND | No Stripe/PayPal/web payment URLs in source |
| "Buy on website" buttons | NONE FOUND | Clean |
| Links to external stores | NONE FOUND | No redirects to external payment |
| Promo code as bypass | CAUTION | Promo codes are acceptable alongside IAP, but currently they're the ONLY method |

**External URLs found in app** (none are payment-related):
- `mailto:ruscon2001@gmail.com` — Support email (OK)
- `https://...railway.app/privacy*.html` — Privacy Policy (OK)
- `https://...railway.app/faq*.html` — FAQ (OK)
- `https://apps.apple.com/app/qrchat/id0000000000` — App Store rating link (OK, but placeholder ID)

---

## 5.2 INTELLECTUAL PROPERTY

**Verdict: PASS (with advisory notes)**

| Check | Status | Notes |
|-------|--------|-------|
| "QRChat" trademark | NOT REGISTERED | No evidence of trademark registration. Low risk for indie app but recommended to do a TESS search |
| Trademark conflicts | LOW RISK | "QRChat" is relatively unique. No major known conflicts |
| Copyright | CLEAN | `LICENSE` file: "Copyright (c) 2026 Ruslan Constantinovici. All rights reserved." |
| Third-party IP | CLEAN | Uses open-source libraries (TweetNaCl, React Native, etc.) with appropriate licenses |
| Copyrighted material | NONE FOUND | No unauthorized images, icons, or content |

**Advisory:**
- Consider registering "QRChat" as a trademark (USPTO or EUIPO) before scaling
- The LICENSE file is proprietary — ensure this doesn't conflict with any open-source dependencies' license requirements
- Contact email in LICENSE (`privacy@qrchat.app`) — ensure this domain is actually owned/active

---

## 5.3 GAMING, GAMBLING, LOTTERIES

N/A — QRChat is a messaging app with no gaming/gambling features.

---

## 5.4 VPN APPS

**Verdict: N/A (with preparedness note)**

QRChat is NOT a VPN app. However, it uses:
- End-to-end encryption (TweetNaCl)
- Peer-to-peer WebRTC connections
- Relay server for offline message delivery

**Prepared explanation for reviewer:**
> "QRChat is an encrypted messenger, not a VPN. Encryption is used solely to protect user-to-user messages and calls. The relay server temporarily holds encrypted messages for offline delivery (max 48h) and cannot decrypt them. No network tunneling, IP masking, or traffic routing is performed."

---

## 5.5 DEVELOPER CODE OF CONDUCT

**Verdict: PASS**

| Check | Status |
|-------|--------|
| Real developer identity | YES — Ruslan Constantinovici, Moldova |
| Single developer account | YES |
| Not a bot/spam factory | CONFIRMED — legitimate indie developer |
| Accurate metadata | YES — app description matches functionality |

---

## EXPORT COMPLIANCE

**Verdict: PARTIAL — 2 issues to fix**

### What's Correct

| Check | Status |
|-------|--------|
| ITSAppUsesNonExemptEncryption = YES | CORRECT (Info.plist:36-37) |
| Algorithms documented | YES — TweetNaCl (XSalsa20-Poly1305, X25519, Ed25519), SQLCipher (AES-256) |
| BIS Self-Classification document | EXISTS (`build/BIS_Self_Classification_QRChat.pdf`) |
| Encryption compliance report | EXISTS (`agent-runtime/outputs/encryption-compliance.md`) |
| ECCN classification | 5D002, License Exception ENC 740.17(b)(1) |

### Issues Found

**Issue 1: ITSEncryptionExportComplianceCode is EMPTY**
```xml
<!-- Info.plist:38-39 -->
<key>ITSEncryptionExportComplianceCode</key>
<string></string>
```

This key should either:
- Contain a valid compliance code from App Store Connect, OR
- Be removed entirely if you're answering the export compliance questions manually in App Store Connect each submission

**Action:** Either obtain the export compliance code from App Store Connect after first answering the questionnaire, or remove the empty key.

**Issue 2: Annual BIS Self-Classification Filing**
- Per EAR 742.15(b), if using non-exempt encryption, an annual self-classification report must be filed with BIS by February 1 each year.
- The compliance document references this requirement. Ensure it was filed for 2026 (or will be filed before Feb 1, 2027).

---

## TERMS OF SERVICE

**Verdict: PASS**

| Check | Status | Location |
|-------|--------|----------|
| ToS exists in app | YES | `src/screens/TermsScreen.tsx` — full multi-section ToS |
| Checkbox at onboarding | YES | `src/screens/SetupScreen.tsx:33,204-208` — `agreedToTerms` checkbox, button disabled until checked |
| ToS blocks setup if not agreed | YES | `SetupScreen.tsx:51-52` — Alert if not agreed |
| ToS accessible from Support | YES | `SupportScreen.tsx:23-25` — navigates to Terms screen |
| ToS accessible from Settings | NOT DIRECTLY | Settings links to Privacy Policy but not Terms. Terms is accessible via Settings > Support > Terms |

**Minor recommendation:** Add direct Terms link in SettingsScreen alongside Privacy Policy for easier access.

### ToS Content Sections (via i18n keys):
1. Acceptance of Terms
2. Service Description
3. Eligibility
4. Privacy
5. Prohibited Use
6. Termination
7. Disclaimer
8. Contact Information

All standard sections present.

---

## REVIEW NOTES (APP_STORE_METADATA.md)

**Verdict: PASS**

| Check | Status |
|-------|--------|
| Testing instructions clear | YES — step-by-step with 2 devices |
| Explains 2-device requirement | YES — explicitly stated |
| Explains no login/demo account | YES — "Not applicable — QRChat has no login system" |
| Explains QR scanning flow | YES — 7-step test procedure |
| Explains encryption purpose | YES — relay server role explained |
| Permission usage explained | YES — camera, microphone, photos |

**Minor notes:**
- App Store review link uses placeholder ID `id0000000000` — needs real App Store ID after first submission
- "What's New" section references v4.0.0 — ensure this matches the version being submitted

---

## PRIORITY ACTION LIST

### BLOCKERS (must fix before submission)

| # | Issue | Section | Severity |
|---|-------|---------|----------|
| 1 | **Implement Apple In-App Purchase for $2.99 Unlimited upgrade** | 3.1 | CRITICAL — guaranteed rejection |
| 2 | **Add "Restore Purchases" button** | 3.1 | CRITICAL — required for non-consumable IAP |

### HIGH PRIORITY (should fix before submission)

| # | Issue | Section | Severity |
|---|-------|---------|----------|
| 3 | Fix empty `ITSEncryptionExportComplianceCode` in Info.plist | Export | HIGH |
| 4 | Ensure BIS annual self-classification is filed | Export | HIGH |

### LOW PRIORITY (recommended improvements)

| # | Issue | Section | Severity |
|---|-------|---------|----------|
| 5 | Add direct Terms link in SettingsScreen | ToS | LOW |
| 6 | Replace App Store placeholder ID `id0000000000` | Review Notes | LOW |
| 7 | Consider trademark registration for "QRChat" | 5.2 | LOW |
| 8 | Verify `privacy@qrchat.app` domain is active | 5.2 | LOW |

---

## APPENDIX: Files Reviewed

| File | Purpose |
|------|---------|
| `src/screens/UpgradeScreen.tsx` | Purchase UI — $2.99 button with TODO stub |
| `src/services/LicensingService.ts` | Licensing logic — promo codes + IAP placeholder |
| `server/licensing.js` | Server licensing — promo code generation/redemption |
| `src/screens/TermsScreen.tsx` | Terms of Service screen |
| `src/screens/SetupScreen.tsx` | Onboarding with ToS checkbox |
| `src/screens/SupportScreen.tsx` | Support screen with ToS link |
| `src/screens/SettingsScreen.tsx` | Settings — Privacy Policy link |
| `ios/QRChat/Info.plist` | Encryption export compliance keys |
| `APP_STORE_METADATA.md` | Review notes and metadata |
| `LICENSE` | Proprietary license |
| `build/BIS_Self_Classification_QRChat.pdf` | Export compliance document |
| `package.json` | Dependencies (no IAP library) |
