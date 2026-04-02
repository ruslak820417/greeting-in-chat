# Prompt: Frontend Engineer — Privacy Policy Integration in App

**Agent:** frontend-engineer
**Data:** 2026-03-21
**Prioritate:** INALTA — necesar pentru App Store submission
**Dependenta:** Asteapta release-engineer sa finalizeze `/Users/ruslanconstantinovici/QRChat/docs/privacy.html`
**Rezultat:** Cod in QRChat + `agent-runtime/outputs/privacy-frontend-integration.md`

---

## Context

Release-engineer va rescrie Privacy Policy-ul QRChat in `docs/privacy.html`. Tu, frontend-engineer, trebuie sa te asiguri ca:

1. Privacy Policy este accesibila din aplicatie (Apple 5.1.1(i) si Google Play User Data Policy impun asta)
2. Link-urile din app duc la URL-ul corect
3. Ecranul de Settings afiseaza link-ul corect
4. Onboarding-ul mentioneaza privacy policy (daca exista un flow de onboarding)
5. Versiunile traduse sunt disponibile in cele 4 limbi (EN, RO, RU, FR)

**Developer:** Ruslan Constantinovici
**App:** QRChat — Encrypted Messenger (com.ruslan.qrchat)
**Privacy Policy URL:** https://exciting-success-production-d272.up.railway.app/privacy
**Limbi suportate:** Engleza, Romana, Rusa, Franceza

---

## Fisiere de citit INAINTE de a incepe

1. `/Users/ruslanconstantinovici/QRChat/docs/privacy.html` — privacy policy finala (asteapta release-engineer)
2. `/Users/ruslanconstantinovici/QRChat/screens/SettingsScreen.tsx` — ecranul de setari (unde trebuie sa fie link-ul)
3. `/Users/ruslanconstantinovici/QRChat/utils/ThemeContext.tsx` — theme context (pentru dark/light mode consistency)
4. `/Users/ruslanconstantinovici/QRChat/utils/i18n.ts` sau echivalent — fisierul de internationalizare
5. Fisierele de traduceri:
   - `/Users/ruslanconstantinovici/QRChat/locales/en.json` (sau unde sunt stocate)
   - `/Users/ruslanconstantinovici/QRChat/locales/ro.json`
   - `/Users/ruslanconstantinovici/QRChat/locales/ru.json`
   - `/Users/ruslanconstantinovici/QRChat/locales/fr.json`
6. `/Users/ruslanconstantinovici/QRChat/screens/SetupScreen.tsx` — ecranul de setup/onboarding
7. `/Users/ruslanconstantinovici/QRChat/App.tsx` — entry point (verifica navigarea)
8. `/Users/ruslanconstantinovici/QRChat/ios/QRChat/Info.plist` — pentru NSPrivacyPolicy URL daca exista

---

## Sarcini concrete

### Task 1: Verifica si updateaza link-ul Privacy Policy in Settings

Deschide `SettingsScreen.tsx` si verifica:

1. **Exista deja un link "Privacy Policy"?** Daca da, verifica ca URL-ul este corect:
   - URL corect: `https://exciting-success-production-d272.up.railway.app/privacy`
   - Implementare: `Linking.openURL(url)` — deschide in browser extern (Safari/Chrome)

2. **Daca NU exista**, adauga un item in Settings:
   ```
   Privacy Policy -> tap -> Linking.openURL('https://exciting-success-production-d272.up.railway.app/privacy')
   ```

3. **Pozitionare:** La sfarsitul listei de setari, in sectiunea "About" sau "Legal" (langa "Version", "Licenses", etc.)

4. **Accessibility:**
   - `accessibilityLabel` tradus in cele 4 limbi
   - `accessibilityRole="link"`
   - `accessibilityHint` — "Opens the privacy policy in your browser" (tradus)

5. **Icon:** Foloseste un icon potrivit (shield-lock, document, privacy — din iconset-ul deja folosit in app)

**Impus de:** Apple 5.1.1(i) — "All apps must include a link to their privacy policy [...] within the app in an easily accessible manner"

### Task 2: Verifica link-ul Privacy Policy in onboarding/setup

Deschide `SetupScreen.tsx` si verifica:

1. **Exista un text/link la Privacy Policy in ecranul de setup?** Daca nu, adauga unul:
   - Text recomandat: "By using QRChat, you agree to our [Privacy Policy]" (link clickable)
   - Sau: un text mic sub butonul de "Get Started" / "Continue"
   - NU trebuie sa fie un checkbox obligatoriu (nu e necesar consimtamant explicit sub GDPR Art. 6(1)(b) — procesarea e bazata pe contract, nu pe consimtamant)

2. **Stil:** Text mic, gri, centrat sub CTA button. Link in culoarea QRChat orange (#FF6B00).

3. **Accessibility:**
   - Text tradus in cele 4 limbi
   - Link cu accessibilityRole="link"

**Impus de:** Apple 5.1.1(i), Google Play — privacy policy must be accessible from within the app

### Task 3: Adauga/verifica traducerile Privacy Policy-related

Verifica si adauga in fisierele de traduceri urmatoarele key-uri:

#### EN (English):
```json
{
  "settings.privacy_policy": "Privacy Policy",
  "settings.privacy_policy_hint": "Opens the privacy policy in your browser",
  "setup.privacy_agreement": "By using QRChat, you agree to our",
  "setup.privacy_policy_link": "Privacy Policy",
  "settings.terms_of_service": "Terms of Service",
  "settings.legal_section": "Legal",
  "settings.about_section": "About"
}
```

#### RO (Romanian):
```json
{
  "settings.privacy_policy": "Politica de confidentialitate",
  "settings.privacy_policy_hint": "Deschide politica de confidentialitate in browser",
  "setup.privacy_agreement": "Prin utilizarea QRChat, acceptati",
  "setup.privacy_policy_link": "Politica de confidentialitate",
  "settings.terms_of_service": "Termeni si conditii",
  "settings.legal_section": "Legal",
  "settings.about_section": "Despre"
}
```

#### RU (Russian):
```json
{
  "settings.privacy_policy": "Politika konfidencialnosti",
  "settings.privacy_policy_hint": "Otkryvaet politiku konfidencialnosti v brauzere",
  "setup.privacy_agreement": "Ispolzuja QRChat, vy soglashaetes s nashej",
  "setup.privacy_policy_link": "Politikoj konfidencialnosti",
  "settings.terms_of_service": "Uslovija ispolzovanija",
  "settings.legal_section": "Juridicheskaja informacija",
  "settings.about_section": "O prilozhenii"
}
```

**ATENTIE:** Traducerile de mai sus in rusa sunt transliterate din cauza limitarilor de encoding. In fisierele reale, foloseste caractere chirilice corecte:
- "Политика конфиденциальности"
- "Открывает политику конфиденциальности в браузере"
- "Используя QRChat, вы соглашаетесь с нашей"
- "Политикой конфиденциальности"
- "Условия использования"
- "Юридическая информация"
- "О приложении"

#### FR (French):
```json
{
  "settings.privacy_policy": "Politique de confidentialite",
  "settings.privacy_policy_hint": "Ouvre la politique de confidentialite dans votre navigateur",
  "setup.privacy_agreement": "En utilisant QRChat, vous acceptez notre",
  "setup.privacy_policy_link": "Politique de confidentialite",
  "settings.terms_of_service": "Conditions d'utilisation",
  "settings.legal_section": "Juridique",
  "settings.about_section": "A propos"
}
```

**Nota:** Verifica cum sunt structurate fisierele de traduceri existente (flat JSON, nested, namespace-uri) si adapteaza key-urile la conventia existenta.

### Task 4: Verifica App Store Connect metadata

Verifica ca urmatoarele sunt configurate:

1. **App Store Connect > App Information > Privacy Policy URL:**
   - Trebuie sa fie: `https://exciting-success-production-d272.up.railway.app/privacy`
   - Aceasta se configureaza in App Store Connect, dar verifica si documenteaza in output

2. **Google Play Console > Store listing > Privacy policy:**
   - Trebuie sa fie acelasi URL
   - Documenteaza in output

3. **Info.plist (iOS):**
   - Verifica daca exista un key `ITSAppUsesNonExemptEncryption` (deja setat la YES)
   - Verifica daca exista referinta la privacy policy URL in Info.plist (optional dar recomandat)

### Task 5: Verifica ca privacy.html se serveste corect

Dupa ce release-engineer finalizeaza privacy.html, verifica:

1. **Local test:** Porneste serverul local si acceseaza `http://localhost:PORT/privacy`
   - Pagina trebuie sa se incarce fara erori
   - Pagina trebuie sa fie responsive (testeaza la 375px width — iPhone SE)
   - Toate link-urile externe trebuie sa functioneze

2. **In-app test:** Din Settings screen, click pe "Privacy Policy"
   - Se deschide browser-ul extern (Safari pe iOS)
   - Pagina se incarca corect
   - Inapoi in app functioneaza normal

3. **Accessibility test:**
   - VoiceOver citeste corect link-urile si sectiunile
   - Contrast suficient (WCAG AA — minimum 4.5:1 text, 3:1 large text)
   - Headings hierarchy corecta (VoiceOver rotor)

### Task 6: Dark mode compatibility (optional dar recomandat)

Verifica daca privacy.html ar trebui sa suporte dark mode:

- Daca pagina se deschide in Safari/Chrome, browserul aplica dark mode automat DACA CSS-ul contine `prefers-color-scheme: dark`
- Recomandat: Adauga `@media (prefers-color-scheme: dark)` in CSS-ul privacy.html
- Daca implementezi, coordoneaza cu release-engineer (el scrie HTML-ul)

---

## Legislatia relevanta pentru frontend

### Apple App Store Guidelines 5.1.1(i)
> "All apps must include a link to their privacy policy in the App Store Connect metadata field and within the app in an easily accessible manner."
- **In App Store Connect:** Privacy Policy URL field
- **In app:** Settings screen, cu un link clar catre privacy policy

### Google Play User Data Policy
> "Your app must post a privacy policy link in the designated field within Play Console, and a privacy policy link or text within the app itself."
- **In Play Console:** Privacy policy URL
- **In app:** Link sau text in Settings

### GDPR Art. 12(1) — Transparency
> "The controller shall take appropriate measures to provide any information referred to in Articles 13 and 14 [...] in a concise, transparent, intelligible and easily accessible form, using clear and plain language."
- Privacy policy trebuie sa fie **usor accesibila** din app
- Nu trebuie ascunsa in sub-sub-meniuri

### CCPA 1798.130(a)(5)
> "A business that operates exclusively online and has a direct relationship with a consumer [...] shall make the general description of the consumer's opt-out rights more prominently available."
- Link-ul Privacy Policy trebuie sa fie vizibil in Settings

---

## Format rezultat

Scrie rezultatul in `agent-runtime/outputs/privacy-frontend-integration.md` cu urmatoarea structura:

```markdown
# Privacy Policy — Frontend Integration Report

## 1. Settings Screen
- [x/todo] Link Privacy Policy existent / adaugat
- [x/todo] URL corect
- [x/todo] Accessibility labels
- [x/todo] Icon potrivit
- Fisier modificat: [path]

## 2. Setup/Onboarding Screen
- [x/todo] Link Privacy Policy existent / adaugat
- [x/todo] Text tradus in 4 limbi
- Fisier modificat: [path]

## 3. Translations
- [x/todo] EN keys adaugate
- [x/todo] RO keys adaugate
- [x/todo] RU keys adaugate
- [x/todo] FR keys adaugate
- Fisiere modificate: [paths]

## 4. App Store / Play Store Configuration
- Privacy Policy URL: [url]
- Status: [documented / verified]

## 5. Testing Results
- [x/todo] Local server test
- [x/todo] In-app link test
- [x/todo] Accessibility test (VoiceOver)
- [x/todo] Responsive test (mobile width)

## 6. Dark Mode
- Status: [implemented / skipped / coordinated with release-engineer]
```

---

## Criterii de succes

- [ ] Privacy Policy accesibila din Settings cu un singur tap
- [ ] Privacy Policy accesibila din Setup/Onboarding screen
- [ ] URL corect: `https://exciting-success-production-d272.up.railway.app/privacy`
- [ ] Traduceri in cele 4 limbi (EN, RO, RU, FR)
- [ ] Accessibility labels pe toate elementele interactive
- [ ] VoiceOver test passed
- [ ] Link deschide browser-ul extern (Safari/Chrome), nu un WebView intern
- [ ] Inapoi in app dupa vizitarea privacy policy functioneaza normal
- [ ] Privacy policy URL documentat pentru App Store Connect si Google Play Console
- [ ] Deploy pe simulator si telefon fizic dupa modificari
- [ ] Rezultatul scris in `agent-runtime/outputs/privacy-frontend-integration.md`

---

## Dependente

- **Asteapta** release-engineer sa finalizeze `/Users/ruslanconstantinovici/QRChat/docs/privacy.html` inainte de a testa link-urile.
- **Poti incepe** Task 1, 2, 3 imediat (nu depind de HTML-ul final — doar de URL).
- **Task 5** (testare) necesita HTML-ul finalizat.
- **Dupa finalizare**, actualizeaza `agent-runtime/state/status.md`.
- **Deploy obligatoriu** pe simulator si telefon fizic dupa orice modificare de cod.

---

## Note suplimentare

- **NU rescrie** privacy.html — aceasta este responsabilitatea release-engineer
- **NU modifica** server/index.js — aceasta este responsabilitatea backend-engineer
- Daca descoperi ca lipsesc fisiere de traduceri sau ca structura i18n e diferita de ce ai asteptat, adapteaza-te si documenteaza in output
- Daca SetupScreen.tsx nu exista sau onboarding-ul are alta structura, documenteaza ce ai gasit si adapteaza
- Verifica daca exista deja un `PrivacyPolicyScreen` sau `WebViewScreen` care ar putea afisa policy-ul in-app (unele apps fac asta). Daca exista, actualizeaza URL-ul si acolo. Dar recomandat de Apple: link extern catre browser.
