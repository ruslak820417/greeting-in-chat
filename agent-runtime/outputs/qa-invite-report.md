# QA Report — Invite Links System

**Agent:** qa-engineer
**Date:** 2026-03-24
**Status:** REVIEW NEEDED — 2 blockers, 4 medium, 5 low issues

---

## 1. TypeScript Compilation (`npx tsc --noEmit`)

**Result: FAIL — 2 errors**

| File | Line | Error |
|------|------|-------|
| `src/screens/ShareInviteScreen.tsx` | 17 | `Cannot find module '@react-native-clipboard/clipboard'` |
| `src/screens/ShareInviteScreen.tsx` | 18 | `Cannot find module 'react-native-haptic-feedback'` |

**Fix required:**
```bash
npm install @react-native-clipboard/clipboard react-native-haptic-feedback
cd ios && pod install
```

**Severity: BLOCKER** — Build will fail until these dependencies are installed.

---

## 2. InviteLinkCrypto.ts — Crypto Logic Audit

**File:** `src/crypto/InviteLinkCrypto.ts` (431 lines)

### Verdict: PASS (solid crypto design)

**Strengths:**
- Zero-knowledge server model — linkSecret never leaves the URL fragment (`#`)
- HKDF key derivation with separate info strings for linkId vs encKey (proper domain separation)
- XSalsa20-Poly1305 (nacl.secretbox) — industry standard AEAD
- Ed25519 detached signatures on ciphertext — proves creator identity
- Random 24-byte nonces via `nacl.randomBytes()`
- URL parsing validates linkSecret length (32 bytes) AND re-derives linkId to verify integrity (line 332)
- Base64URL encoding (URL-safe, no padding) — correct for URL fragments

**Notes (acceptable):**
- HKDF uses empty salt (line 121) — allowed by RFC 5869, domain separation via info strings is sufficient
- Decrypt-then-verify order (line 214-241) — necessary because signer's pubkey is inside the encrypted payload. Architecturally correct.
- String comparison for linkId (line 333) — not constant-time, but linkId is a public identifier, not a secret. No timing side-channel risk.
- `hmacSha512` uses `nacl.hash` (SHA-512) for HMAC construction — correct implementation.

**One minor note:**
- Commented-out `_selfTest()` at bottom (line 409-430) — marked "remove before production". Should be removed for production build.

---

## 3. InviteLinkService.ts — API Calls Audit

**File:** `src/services/InviteLinkService.ts` (250 lines)

### Verdict: PASS with 1 MEDIUM issue

**Strengths:**
- `createInvite()` uses `supabase.functions.invoke()` — sends JWT auth token automatically
- `validateInvite()` uses raw fetch with anon key — correct, this is a public endpoint (`--no-verify-jwt`)
- `acceptInvite()` uses raw fetch with anon key — correct, acceptor is anonymous
- Realtime subscription via `postgres_changes` on `invite_links` table — clean implementation
- Cleanup function returned from `subscribeToInvite()` — prevents memory leaks
- Error handling extracts error body from Supabase edge function responses

**MEDIUM — Auth concern on `confirmInvite` and `revokeInvite`:**

| Function | Auth | Risk |
|----------|------|------|
| `confirmInvite()` (line 159) | Anon key only | If server doesn't verify caller === creator, anyone with linkId can confirm |
| `revokeInvite()` (line 186) | Anon key only | If server doesn't verify caller === creator, anyone with linkId can revoke |

**Recommendation:** Verify that the Supabase edge functions `invite-confirm` and `invite-revoke` implement server-side authorization (e.g., check that the request comes from the invite creator by matching some stored identifier). If they use `--no-verify-jwt`, this is a **security issue**. If they require JWT, then these calls will fail — switch to `supabase.functions.invoke()`.

---

## 4. Screen Audits

### 4.1 CreateInviteScreen.tsx

**File:** `src/screens/CreateInviteScreen.tsx` (227 lines)

**Verdict: PASS**

- Correctly reads profile, generates linkSecret, derives linkId, encrypts payload
- Saves invite locally via AsyncStorage for management screen
- Passes `linkSecretArray` (not the Uint8Array itself) to ShareInvite — correct since React Navigation can't serialize Uint8Array
- Loading state prevents double-tap
- Error displayed via Alert

**LOW — `linkSecretBase64: ''` passed as empty string (line 83):** The param is typed as required in `RootStackParamList` but passed as empty. This is dead code — only `linkSecretArray` is used. Should be removed from the type and the call.

### 4.2 ShareInviteScreen.tsx

**File:** `src/screens/ShareInviteScreen.tsx` (339 lines)

**Verdict: PASS with 2 issues**

**Strengths:**
- QR code generation with high error correction (`ecl="H"`)
- Live countdown timer with color-coded urgency (green/yellow/red)
- Realtime subscription for acceptor detection
- Double handshake: decrypts acceptor payload, then calls confirmInvite
- Adds contact to DB and navigates to Chat on success
- Copy, Share, and truncated URL display

**MEDIUM — `linkSecret` recreated every render (line 37):**
```ts
const linkSecret = new Uint8Array(route.params.linkSecretArray);
```
This creates a new `Uint8Array` object on every render. It's in the dependency array of `handleAcceptorFound` useCallback (line 115), causing the callback to be recreated every render, defeating the memoization. Should be wrapped in `useMemo`.

**LOW — useEffect empty deps reference route.params (lines 55, 66):**
Both `useEffect` hooks have `[]` dependency arrays but access `route.params.expiresAt` and `route.params.inviteId`. Functionally correct (route params don't change), but ESLint `react-hooks/exhaustive-deps` rule would flag this.

### 4.3 InviteAcceptScreen.tsx

**File:** `src/screens/InviteAcceptScreen.tsx` (349 lines)

**Verdict: PASS**

**Strengths:**
- Phase-based UI (loading/valid/error) — clean state machine
- 5 distinct error states with appropriate icons and messages
- Retry button only shown for network errors
- Security badge explaining E2E encryption
- Countdown display with remaining minutes
- Accept/Decline buttons with loading state

**LOW — Dead `hashColor`/`AVATAR_COLORS` (lines 31-39):**
The screen defines its own `hashColor` function using a local `AVATAR_COLORS` array for the on-screen avatar display (line 195), but uses `getRandomAvatarColor()` (imported from helpers, line 113) when saving the contact. This means the avatar color shown on the accept screen won't match the saved contact's avatar color. Minor UX inconsistency.

**LOW — Duplicate validation logic (lines 134-153):**
The `handleRetry` function duplicates the validation logic from the initial `useEffect`. Should extract to a shared function.

### 4.4 InviteManagementScreen.tsx

**File:** `src/screens/InviteManagementScreen.tsx` (418 lines)

**Verdict: PASS with 1 issue**

**Strengths:**
- Auto-expires pending invites on load and via 1-second interval
- Active/Past sections with collapsible past section
- Live countdown on active cards
- Revoke with confirmation dialog
- Tap card to re-open ShareInvite screen
- Empty state with "Create first invite" CTA
- Navigation focus listener reloads data

**LOW — FlatList misuse (line 258):**
```ts
<FlatList data={[1]} keyExtractor={() => 'sections'} ...>
```
Uses FlatList with a single-item array just for scrolling. Should use `ScrollView` instead — simpler and avoids FlatList overhead.

---

## 5. useInviteDeepLink.ts — Hook Audit

**File:** `src/hooks/useInviteDeepLink.ts` (131 lines)

### Verdict: PASS with 1 MEDIUM issue

**Strengths:**
- Handles both cold start (`getInitialURL`) and warm start (`addEventListener`)
- Navigator-ready gate: queues URL if navigator isn't mounted yet
- Module-level `initialURLProcessed` flag prevents double-processing on cold start
- Logs redacted URLs (replaces fragment with `#[REDACTED]`) — good security practice
- Validates URLs with `parseInviteURL()` which checks HKDF derivation

**MEDIUM — Hardcoded English in Alert (lines 39-43):**
```ts
Alert.alert('Invalid Invite', 'This invite link is invalid or has been tampered with.');
```
This is a module-level function, not a React component, so it can't use `useTranslation()`. However, the user-facing alert is in English only. Should use `i18next.t()` directly (the i18next instance, not the hook) for consistency.

**LOW — `linkSecretBase64` misnomer (lines 53-56):**
```ts
linkSecretBase64: Array.from(parts.linkSecret).map((b) => String.fromCharCode(b)).join('')
```
This produces a binary-to-string conversion, NOT base64 encoding. The field is never actually used (screens only use `linkSecretArray`). Dead code with misleading name.

---

## 6. i18n Strings Verification

### Verdict: PASS — All 4 locales complete and matching

| Locale | Keys | Status |
|--------|------|--------|
| en.json | 56 keys | Complete |
| ro.json | 56 keys | Complete |
| ru.json | 56 keys | Complete |
| fr.json | 56 keys | Complete |

All interpolation variables (`{{time}}`, `{{date}}`, `{{name}}`) are consistent across locales.

**Unused keys in locale files (present but never referenced in code):**
- `invite.creating` — not used anywhere
- `invite.acceptTitle` — not used anywhere
- `invite.accepting` — not used anywhere
- `invite.openApp` — not used anywhere
- `invite.reshare` — not used anywhere

These 5 keys are dead strings. Low priority but should be cleaned up or wired into the UI.

---

## 7. AppNavigator.tsx — Screen Registration

**File:** `src/navigation/AppNavigator.tsx` (123 lines)

### Verdict: PASS — Complete

| Screen | Registered | Type Params | Import |
|--------|-----------|-------------|--------|
| InviteAccept | line 114 | `{ linkId, linkSecretBase64, linkSecretArray }` | line 26 |
| CreateInvite | line 115 | `undefined` | line 27 |
| ShareInvite | line 116 | `{ linkId, linkSecretBase64, linkSecretArray, inviteId, expiresAt }` | line 28 |
| InviteManagement | line 117 | `undefined` | line 29 |

All 4 screens imported, registered, and typed in `RootStackParamList`.

---

## Summary of Issues

### BLOCKER (2) — Must fix before build

| # | Issue | File | Fix |
|---|-------|------|-----|
| B1 | Missing `@react-native-clipboard/clipboard` | ShareInviteScreen.tsx:17 | `npm install` |
| B2 | Missing `react-native-haptic-feedback` | ShareInviteScreen.tsx:18 | `npm install` |

### MEDIUM (4) — Should fix before release

| # | Issue | File | Fix |
|---|-------|------|-----|
| M1 | `confirmInvite`/`revokeInvite` use anon key — verify server-side auth | InviteLinkService.ts:159,186 | Verify edge function auth or switch to `supabase.functions.invoke()` |
| M2 | `linkSecret` recreated every render, defeats useCallback memoization | ShareInviteScreen.tsx:37 | Wrap in `useMemo` |
| M3 | Hardcoded English in deep link Alert | useInviteDeepLink.ts:39-43 | Use `i18next.t()` directly |
| M4 | 5 unused i18n keys (dead strings) | All locale files | Remove or wire into UI |

### LOW (5) — Nice to fix

| # | Issue | File | Fix |
|---|-------|------|-----|
| L1 | `linkSecretBase64` dead param (empty string/misnomer) | CreateInviteScreen.tsx:83, useInviteDeepLink.ts:54 | Remove from types and params |
| L2 | Avatar color mismatch: display vs saved | InviteAcceptScreen.tsx:195 vs 113 | Use same color source |
| L3 | Duplicate validation logic in handleRetry | InviteAcceptScreen.tsx:134-153 | Extract shared function |
| L4 | FlatList with single item instead of ScrollView | InviteManagementScreen.tsx:258 | Replace with ScrollView |
| L5 | Commented-out _selfTest marked "remove before production" | InviteLinkCrypto.ts:409-430 | Remove |

---

## Architecture Assessment

The Invite Links System follows a **zero-knowledge server model** with solid cryptographic foundations:

- **Key derivation:** HKDF(linkSecret) → linkId + encKey — deterministic, domain-separated
- **Encryption:** XSalsa20-Poly1305 (nacl.secretbox) — AEAD with 24-byte random nonces
- **Authentication:** Ed25519 detached signatures on ciphertext
- **Privacy:** linkSecret in URL fragment (`#`) — never sent to server by HTTP spec
- **Exchange:** Double handshake (create → accept → confirm) with encrypted payloads both ways
- **Realtime:** Supabase Postgres changes subscription for instant accept notification

The crypto is correct and well-structured. The primary risks are operational (missing deps, auth on server endpoints) rather than cryptographic.

---

*Report generated by qa-engineer agent — 2026-03-24*
