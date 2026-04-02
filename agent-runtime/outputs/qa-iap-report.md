# QA Report: IAP Implementation Audit

**Date:** 2026-03-22
**QA Engineer:** qa-engineer
**Project:** QRChat v3.0.6
**Scope:** In-App Purchase (IAP) full-stack verification

---

## 1. TypeScript Check (`npx tsc --noEmit`)

**Result: PASS (0 errors)**

Exit code 0. No type errors anywhere in the codebase.

---

## 2. Jest Tests (`npx jest --no-cache --verbose`)

**Result: PARTIAL PASS (8/8 tests pass, 1 suite fails)**

| Suite | Status | Details |
|-------|--------|---------|
| LicensingService.test.ts | PASS | All tests pass |
| server/index.test.js | PASS | All tests pass |
| App.test.tsx | FAIL | `react-native-iap` not mocked/transformed |

**Issue:** `App.test.tsx` fails because `react-native-iap` uses ESM `import` syntax, and Jest's `transformIgnorePatterns` does not include `react-native-iap`.

**Fix needed:** Add `react-native-iap` to `transformIgnorePatterns` in `jest.config.js`:
```js
transformIgnorePatterns: [
  'node_modules/(?!(react-native|@react-native|react-native-iap)/)',
]
```
Or add a mock file at `__mocks__/react-native-iap.js`.

**Severity: MEDIUM** - Blocks App.test.tsx suite, but no runtime impact.

---

## 3. IAPService.ts Audit

**File:** `src/services/IAPService.ts` (269 lines)

| Check | Status | Notes |
|-------|--------|-------|
| `initConnection()` | PASS | Called in `initialize()`, sets `state.connected = true` |
| `fetchProducts()` | PASS | Fetches `IAP_PRODUCT_ID` with correct type |
| `requestPurchase()` | PASS | Uses apple-specific SKU format `{ apple: { sku } }` |
| `finishTransaction()` | PASS | Called with `isConsumable: false` (correct for non-consumable) |
| `getAvailablePurchases()` | PASS | Used in `restorePurchases()` |
| Product ID | PASS | Uses `IAP_PRODUCT_ID` constant = `com.ruslan.qrchat.unlimited` |
| Error handling | PASS | All async methods wrapped in try/catch, no crashes |
| Singleton pattern | PASS | `export default new IAPService()` |
| `destroy()` cleanup | PASS | Removes listeners, ends connection, resets state |
| `purchaseUpdatedListener` | PASS | Validates receipt, finishes transaction, resolves promise |
| `purchaseErrorListener` | PASS | Captures error, resets purchasing state, resolves promise |
| `validateReceipt()` | PASS | Posts to server, gracefully handles offline (trusts Apple) |
| `getLocalizedPrice()` | PASS | Returns `displayPrice` or fallback `$2.99` |

**No issues found.** Service is well-structured with proper lifecycle management.

---

## 4. LicensingService.ts Audit

**File:** `src/services/LicensingService.ts` (156 lines)

| Check | Status | Notes |
|-------|--------|-------|
| `purchaseUnlimited()` | PASS | Delegates to `IAPService.purchase()` |
| `restorePurchases()` | PASS | Delegates to `IAPService.restorePurchases()`, handles restored/not-found |
| `getLocalizedPrice()` | PASS | Delegates to `IAPService.getLocalizedPrice()` |
| `initializeIAP()` | PASS | Delegates to `IAPService.initialize()` |
| IAP + promo coexistence | PASS | Promo via `redeemPromo()`, IAP via `purchaseUnlimited()`, both set `Database.setUnlimited(true)` |
| `getLicenseSource()` | PASS | Returns `'iap'`, `'promo'`, or `'none'` from AsyncStorage |
| `checkLicenseOnServer()` | PASS | Validates license on startup, graceful offline fallback |

**No issues found.**

---

## 5. UpgradeScreen.tsx Audit

**File:** `src/screens/UpgradeScreen.tsx` (410 lines)

| Check | Status | Notes |
|-------|--------|-------|
| Dynamic price (not hardcoded) | PASS | `loadPrice()` reads `IAPService.getLocalizedPrice()`, state `price` |
| Purchase button with loading | PASS | `ActivityIndicator` shown when `purchasing === true` |
| Restore Purchases button | PASS | Lines 227-241, prominent, with loading state |
| Success state (unlimited) | PASS | Lines 136-161, shows checkmark + "already unlimited" |
| Promo code section | PASS | Lines 252-302, expandable input with validation |
| Accessibility labels | PASS | All buttons have `accessibilityLabel` + `accessibilityRole` |
| `useTheme()` | PASS | Line 26, all styles use `colors.*` |
| Cancel handling | PASS | Line 66 - skips alert if error contains "cancel" |

**No issues found.** Apple-compliant layout with all required elements.

---

## 6. SettingsScreen.tsx Audit

**File:** `src/screens/SettingsScreen.tsx` (744 lines)

| Check | Status | Notes |
|-------|--------|-------|
| "Restore Purchases" link | PASS | Lines 479-496, navigates to UpgradeScreen |
| Upgrade section | PASS | Lines 370-400, shows license status |
| Promo code input | PASS | Lines 403-476, inline redemption |

**No issues found.**

---

## 7. i18n Verification

All IAP keys present in all 4 locale files:

| Key | en | ro | ru | fr |
|-----|----|----|----|----|
| `upgrade.title` | PASS | PASS | PASS | PASS |
| `upgrade.purchaseBtn` | PASS | PASS | PASS | PASS |
| `upgrade.purchaseSuccess` | PASS | PASS | PASS | PASS |
| `upgrade.purchaseError` | PASS | PASS | PASS | PASS |
| `upgrade.purchaseAccessibility` | PASS | PASS | PASS | PASS |
| `upgrade.restorePurchases` | PASS | PASS | PASS | PASS |
| `upgrade.restoreTitle` | PASS | PASS | PASS | PASS |
| `upgrade.restoreSuccess` | PASS | PASS | PASS | PASS |
| `upgrade.restoreNotFound` | PASS | PASS | PASS | PASS |
| `upgrade.restoreError` | PASS | PASS | PASS | PASS |
| `upgrade.freeInfo` | PASS | PASS | PASS | PASS |
| `upgrade.contactLimit` | PASS | PASS | PASS | PASS |
| `upgrade.contactLimitDesc` | PASS | PASS | PASS | PASS |

**All 4 locales (en/ro/ru/fr) have complete IAP key coverage.**

---

## 8. Server Endpoint

**File:** `server/index.js`, line 239

| Check | Status | Notes |
|-------|--------|-------|
| `POST /validate-receipt` exists | PASS | Line 239 |
| Input validation | PASS | Checks transactionId, productId, deviceId |
| Product ID check | PASS | Validates against `com.ruslan.qrchat.unlimited` |
| Idempotent handling | PASS | Re-validates already registered transactions |
| Transaction format validation | PASS | Checks numeric format for StoreKit 2 |
| Error responses | PASS | 400 for invalid input, JSON responses |

**No issues found.**

---

## 9. App.tsx IAP Initialization

**File:** `App.tsx`

| Check | Status | Notes |
|-------|--------|-------|
| IAPService imported | PASS | Line 32 |
| IAP initialized on startup | PASS | `LicensingService.initializeIAP()` at line 274 |
| IAP destroyed on unmount | PASS | `IAPService.destroy()` at line 94 |
| Error handling | PASS | `.catch()` on init prevents crash |

**No issues found.**

---

## 10. StoreKit Configuration

### QRChat.entitlements
**File:** `ios/QRChat/QRChat.entitlements`

| Check | Status | Notes |
|-------|--------|-------|
| IAP entitlement | WARNING | Has `com.apple.developer.in-app-payments` (Apple Pay merchant), NOT StoreKit IAP |

**Note:** StoreKit In-App Purchases do NOT require a separate entitlement — they are enabled via App Store Connect configuration. The `com.apple.developer.in-app-payments` entitlement is for Apple Pay / merchant payments, which is a different feature. This is **not a blocker** for IAP but may be unnecessary unless Apple Pay is also planned.

### StoreKitConfig.storekit
**File:** `ios/QRChat/StoreKitConfig.storekit`

| Check | Status | Notes |
|-------|--------|-------|
| Product ID | PASS | `com.ruslan.qrchat.unlimited` matches code |
| Type | PASS | `NonConsumable` (correct for lifetime purchase) |
| Price | PASS | `2.99` |
| Localizations | PASS | en_US, ro, fr, ru — all 4 languages |
| Family shareable | PASS | `false` (appropriate) |
| Reference name | PASS | `QRChat Unlimited` |

**StoreKit config is correct and complete.**

---

## Summary

### Overall Score: 9/10

### Issues Found

| # | Severity | Issue | Component |
|---|----------|-------|-----------|
| 1 | MEDIUM | App.test.tsx fails — `react-native-iap` not in Jest transform/mock config | Jest config |
| 2 | LOW | Entitlements has Apple Pay merchant ID but no StoreKit IAP entitlement needed (informational) | iOS config |

### What Works Well
- IAPService is clean, singleton, proper lifecycle (init/destroy)
- Full purchase flow: purchase -> validate receipt -> activate -> finish transaction
- Restore Purchases implemented correctly (Apple mandatory requirement)
- Dynamic pricing from App Store (not hardcoded)
- All 4 i18n locales have complete IAP key coverage
- Server-side receipt validation with idempotency
- Graceful offline handling (trusts Apple's client-side validation)
- Proper error handling everywhere (no crash paths)
- Accessibility labels on all interactive elements
- IAP + promo code coexistence works correctly

### Required Fix Before Submission
1. **Jest config**: Add `react-native-iap` to `transformIgnorePatterns` or create a mock to fix App.test.tsx

### Recommended (Non-blocking)
2. Consider removing `com.apple.developer.in-app-payments` from entitlements if Apple Pay is not needed (avoid reviewer confusion)
