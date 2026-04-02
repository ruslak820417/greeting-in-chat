# Privacy Policy — Frontend Integration Report

**Agent:** frontend-engineer
**Date:** 2026-03-21

---

## 1. Settings Screen
- [x] Link Privacy Policy existent — updated URL
- [x] URL now language-aware (EN/RO/RU/FR)
- [x] accessibilityLabel uses translated `t('settings.privacyPolicy')`
- [x] accessibilityRole="link" already present
- [x] Icon: shield-checkmark-outline (already present)
- File modified: `src/screens/SettingsScreen.tsx` (line 488-491)

## 2. Support Screen
- [x] Link Privacy Policy existent — updated URL
- [x] URL now language-aware (EN/RO/RU/FR)
- [x] Added `i18n` to useTranslation destructuring
- File modified: `src/screens/SupportScreen.tsx` (lines 11, 31-35)

## 3. Translations
- [x] EN keys already present (`settings.privacyPolicy`, `support.privacyDesc`)
- [x] RO keys already present
- [x] RU keys already present (Cyrillic)
- [x] FR keys already present
- No new keys needed — existing translations cover the UI

## 4. Server Routes
- [x] `/privacy` — serves `docs/privacy.html` (EN) via sendFile
- [x] `/privacy.html` — served by express.static from docs/
- [x] `/privacy-ro.html` — served by express.static from docs/
- [x] `/privacy-ru.html` — served by express.static from docs/
- [x] `/privacy-fr.html` — served by express.static from docs/
- [x] Replaced old inline HTML with file-based serving
- File modified: `server/index.js` (lines 27, 304-307)

## 5. docs/index.html
- [x] Already redirects to `privacy.html` — no changes needed

## 6. URL Mapping by Language
| App Language | Privacy URL |
|---|---|
| EN | `https://exciting-success-production-d272.up.railway.app/privacy.html` |
| RO | `https://exciting-success-production-d272.up.railway.app/privacy-ro.html` |
| RU | `https://exciting-success-production-d272.up.railway.app/privacy-ru.html` |
| FR | `https://exciting-success-production-d272.up.railway.app/privacy-fr.html` |

## 7. TypeScript
- [x] `tsc --noEmit` passes with exit code 0

## Files Modified
1. `src/screens/SettingsScreen.tsx` — language-aware privacy URL
2. `src/screens/SupportScreen.tsx` — language-aware privacy URL + i18n destructuring
3. `server/index.js` — express.static for docs/ + sendFile for /privacy route
