# Prompt: Release Engineer — Privacy Policy Rewrite (Legal-Grade HTML)

**Agent:** release-engineer
**Data:** 2026-03-21
**Prioritate:** CRITICA — blocheaza App Store submission
**Dependenta:** Asteapta `agent-runtime/outputs/privacy-security-audit.md` de la security-engineer
**Rezultat:** `/Users/ruslanconstantinovici/QRChat/docs/privacy.html` (fisierul final)

---

## Context

Privacy Policy-ul QRChat trebuie rescris de la zero pentru a fi conform cu 7 legislatii/standarde diferite. Aceasta e piesa centrala pentru App Store review si Google Play submission. Fiecare cuvant conteaza — afirmatii incorecte pot duce la respingere de catre Apple/Google sau la actiuni legale sub GDPR/CCPA.

**Developer:** Ruslan Constantinovici, Republica Moldova, Chisinau
**Email contact:** ruscon2001@gmail.com
**App:** QRChat — Encrypted Messenger (com.ruslan.qrchat)
**Server live:** https://exciting-success-production-d272.up.railway.app
**Versiune:** 4.0.0
**Data efectiva:** 2026-03-21

---

## Fisiere de citit INAINTE de a scrie

1. **`agent-runtime/outputs/privacy-security-audit.md`** — audit-ul de la security-engineer (OBLIGATORIU — asteapta pana exista)
2. **`/Users/ruslanconstantinovici/QRChat/docs/privacy.html`** — privacy policy existenta (baza de plecare)
3. **`agent-runtime/outputs/privacy-labels.md`** — App Store privacy labels deja pregatite
4. **`agent-runtime/outputs/encryption-compliance.md`** — documentatia de encryption compliance
5. **`agent-runtime/outputs/apple-review-notes.md`** — note pentru Apple Review

---

## Structura obligatorie a Privacy Policy-ului

Privacy Policy-ul trebuie sa contina TOATE sectiunile de mai jos. Fiecare sectiune include referinta la legislatia care o impune.

### Sectiunea 1: Introduction & Overview
- Numele aplicatiei, developer, data efectiva, ultima actualizare
- Bundle ID: com.ruslan.qrchat
- Principiul fundamental: privacy-first, E2E encryption, zero-knowledge architecture
- **Impus de:** Apple 5.1.1(i), Google Play User Data Policy

### Sectiunea 2: Data Controller Information
- **Numele complet:** Ruslan Constantinovici
- **Adresa:** Chisinau, Republica Moldova
- **Email de contact:** ruscon2001@gmail.com
- **Nota DPO:** Deoarece QRChat este dezvoltat de o persoana fizica si nu proceseaza date personale la scara mare, numirea unui DPO nu este obligatorie conform Art. 37 GDPR. Totusi, intrebarile legate de date se adreseaza la emailul de mai sus.
- **Impus de:** GDPR Art. 13(1)(a)(b), Legea RM 133/2011 Art. 12

### Sectiunea 3: What Data We Collect (and What We Do NOT Collect)

#### 3.1 Data Collected — tabela completa:

| Categorie | Date | Unde se stocheaza | Criptat? | Legat de identitate? |
|-----------|------|-------------------|----------|---------------------|
| User-provided | Display Name | Local (device only) | Da (SQLCipher AES-256) | Nu — nu pleaca de pe device |
| User-provided | Profile Photo (optional) | Local (device only) | Da (SQLCipher) | Nu — shared P2P encrypted |
| Auto-generated | Cryptographic Key Pair (X25519) | Private: iOS Keychain / Android Keystore. Public: server (in-memory only) | Private key: Keychain/Keystore protected. Public key: transmitted over TLS | Cheia publica serveste ca pseudonim |
| Auto-generated | Anonymous Mailbox ID | Server (JSON file) | Transmis over TLS | Nu — random 128-bit, nu e derivat din identitate |
| Auto-generated | APNs/FCM Device Token | Server (JSON file, mapped to mailbox ID) | Transmis over TLS | Nu — linked doar la mailbox ID, nu la user ID |
| Transient | Encrypted Pending Messages | Server (JSON file, max 48h) | Da — E2E encrypted, server nu poate decripta | Nu |
| Transient | TURN Relay Credentials | Metered.ca (per session) | Da — encrypted media streams | Nu |
| License | Hashed Device ID | Server (JSON file) | Hash only | Nu — nu e legat de user ID sau mesaje |

#### 3.2 Data NOT Collected — lista explicita:
- Message content (E2E encrypted, serverul nu poate decripta)
- Phone number, email address (no registration)
- Device address book / contacts (QR code only discovery)
- Location data (GPS, IP-based location)
- Analytics, usage statistics, crash reports
- Advertising identifiers (IDFA, IDFV, GAID)
- Browsing history, search queries
- Purchase history (StoreKit/Google Play Billing — handled by platform)
- Health, fitness, financial data
- Cookies, web tracking pixels, device fingerprints

**Impus de:** GDPR Art. 13(1)(d)(e), CCPA 1798.100(b), Apple 5.1.1(i), Google Play User Data Policy

### Sectiunea 4: Legal Basis for Processing (GDPR Art. 6)
Explica baza legala pentru fiecare categorie de date:

| Date | Baza legala (GDPR Art. 6) | Justificare |
|------|--------------------------|-------------|
| Public Key (pseudonym) | Art. 6(1)(b) — Contract performance | Necesar pentru a ruta mesajele catre destinatar |
| Mailbox ID + Push Token | Art. 6(1)(b) — Contract performance | Necesar pentru a livra notificari de mesaje offline |
| Encrypted Pending Messages | Art. 6(1)(b) — Contract performance | Necesar pentru a livra mesaje cand destinatarul e offline |
| Licensed Device ID | Art. 6(1)(b) — Contract performance | Necesar pentru verificarea licentei QRChat Unlimited |
| TURN Relay | Art. 6(1)(b) — Contract performance | Necesar cand conexiunea P2P directa nu e posibila |

**Nota importanta:** QRChat nu se bazeaza pe "consimtamant" (Art. 6(1)(a)) ca baza legala, ci pe "executarea contractului" (Art. 6(1)(b)), deoarece procesarea este strict necesara pentru functionalitatea serviciului. Utilizatorul accepta acest lucru prin utilizarea aplicatiei.

**Impus de:** GDPR Art. 6, Art. 13(1)(c)(d)

### Sectiunea 5: End-to-End Encryption
- Algoritmi: TweetNaCl library
  - Message encryption: XSalsa20-Poly1305 (nacl.box)
  - Key exchange: X25519 (Curve25519 Diffie-Hellman)
  - Signing: Ed25519
  - Key derivation: Double Ratchet protocol (daca e implementat — verifica audit-ul security-engineer)
- Local storage: SQLCipher (AES-256-CBC)
- Key storage: iOS Keychain (kSecAttrAccessibleWhenUnlockedThisDeviceOnly), Android Keystore
- Contact exchange: exclusively via QR code scanning (in-person key exchange)
- **Zero-knowledge architecture:** Serverul nu detine chei de decriptare si nu poate accesa continutul mesajelor
- **Impus de:** GDPR Art. 32, Apple 5.1, Google Play encryption disclosure

### Sectiunea 6: Data Storage & Retention

#### 6.1 On-Device Storage
- Mesaje, contacte, chei, setari, profil — stocate local in SQLCipher DB
- Stergerea app-ului sterge permanent toate datele locale
- iOS: NSFileProtectionCompleteUntilFirstUserAuthentication (sau verifica din audit)

#### 6.2 Server-Side Storage
- Hosting: Railway.app (data center: US — Oregon region)
- Ce se stocheaza pe server:
  - `qrchat_pending_messages.json` — mesaje criptate E2E pentru offline delivery (auto-delete dupa 48h)
  - `qrchat_push_tokens.json` — mapping mailboxId -> push token
  - `qrchat_user_mailboxes.json` — mapping userId -> mailboxId
  - `qrchat_licensed.json` — device IDs licentiati
- Ce NU se stocheaza pe server: profiluri, liste de contacte, istoric de mesaje, continut decriptat

#### 6.3 Retention Periods — tabel:

| Date | Perioada de retentie | Mecanism de stergere |
|------|---------------------|---------------------|
| Encrypted pending messages | Maximum 48 ore | Auto-purge (TTL check pe server) |
| Push tokens (APNs/FCM) | Pana cand tokenul devine invalid | Automatic cleanup (BadDeviceToken/Unregistered) |
| Mailbox IDs | Pana cand push token-ul asociat e invalidat | Cleanup automat impreuna cu push token |
| Licensed device IDs | Indefinit (necesar pentru verificare licenta continua) | La cererea utilizatorului |
| On-device data | Pana la dezinstalarea aplicatiei sau stergerea manuala | Actiune utilizator |

**Impus de:** GDPR Art. 5(1)(e), Art. 13(2)(a), CCPA/CPRA retention disclosure requirement (effective 1 Jan 2026)

### Sectiunea 7: Data Sharing & Third-Party Services
- **Declaratie explicita:** QRChat NU vinde, NU inchiriaza, NU tranzactioneaza, NU partajeaza date personale cu niciun tert pentru marketing, publicitate sau orice alt scop in afara prestarii serviciului.
- Third-party services:

#### 7.1 Apple Push Notification Service (APNs)
- **Furnizor:** Apple Inc.
- **Scop:** Notificari silent push pentru mesaje offline
- **Date partajate:** APNs device token + payload minimal (flag eveniment + public key expeditor — FARA continut mesaj)
- **Privacy Policy:** https://www.apple.com/legal/privacy/
- **Protectii echivalente:** Apple asigura protectia datelor conform propriului Privacy Policy — confirmat conform Apple 5.1.1(i)

#### 7.2 Google Firebase Cloud Messaging (FCM) — daca e implementat pentru Android
- **Furnizor:** Google LLC
- **Scop:** Push notifications pe Android
- **Date partajate:** FCM registration token + payload minimal
- **Privacy Policy:** https://policies.google.com/privacy

#### 7.3 Metered.ca (TURN Relay)
- **Furnizor:** Metered Video Inc.
- **Scop:** Relay criptat WebRTC cand conexiunea P2P directa nu e posibila
- **Date partajate:** Doar stream-uri media criptate E2E. Metered.ca nu poate decripta continutul. Credentiale TURN temporare generate per sesiune.
- **Privacy Policy:** https://www.metered.ca/privacy

#### 7.4 Railway.app (Server Hosting)
- **Furnizor:** Railway Corp.
- **Scop:** Hosting server de signaling QRChat
- **Date procesate:** Doar datele server-side descrise in Sectiunea 6.2
- **Privacy Policy:** https://railway.app/legal/privacy

- **SDK-uri ABSENTE:** QRChat nu contine SDKs de analytics (Firebase Analytics, Google Analytics), crash reporting (Sentry, Crashlytics), advertising (AdMob, Facebook Ads), social media, sau orice alt tracking.
- **Confirmarea echivalentei protectiei:** Fiecare tert cu acces la date ofera protectie egala sau superioara celei descrise in aceasta politica — conform Apple 5.1.1(i).

**Impus de:** GDPR Art. 13(1)(e)(f), Apple 5.1.1(i) third-party data sharing confirmation, Google Play Data Safety

### Sectiunea 8: International Data Transfers
- Serverul QRChat este gazduit pe Railway.app in **Statele Unite (Oregon)**
- Datele server-side (mailbox ID, push tokens, pending messages criptate) pot fi transferate in/din Statele Unite
- **Mecanism de protectie pentru transferuri EU -> US:** EU-US Data Privacy Framework (DPF), adoptat prin Decizia de adecvare a Comisiei Europene din 10 iulie 2023. Railway.app opereaza sub jurisdictie US si se supune protectiilor DPF.
- **Date afectate de transfer:** Exclusiv datele server-side descrise in Sectiunea 6.2 (toate minimale si pseudonimizate/criptate)
- **Protectii suplimentare:** Toate mesajele sunt E2E encrypted — chiar daca serverul e compromis, continutul ramane inaccesibil
- **Metered.ca:** TURN relay traffic este end-to-end encrypted; locatia serverelor TURN variaza geografic dar continutul este criptat
- **Impus de:** GDPR Art. 44-49, GDPR Art. 13(1)(f)

### Sectiunea 9: Your Rights

#### 9.1 Universal Rights (all users)
- **Acces:** Solicitati ce date stocheaza serverul asociate cu identificatorii vostri anonimi
- **Stergere:** Dezinstalati app-ul pentru stergerea datelor locale. Mesajele pending se sterg automat in 48h. Cereti stergerea datelor push token/mailbox prin email.
- **Portabilitate:** Mesajele si contactele sunt stocate local pe dispozitiv si pot fi accesate prin aplicatie

#### 9.2 For EU/EEA Residents (GDPR — Regulation (EU) 2016/679)
Sub GDPR, aveti drepturile suplimentare:
- **Dreptul la rectificare** (Art. 16) — Corectarea datelor inexacte. Nota: datele server-side sunt tehnice/pseudonime, deci nu exista "date inexacte" de corectat in mod practic.
- **Dreptul la restrictionarea procesarii** (Art. 18) — Puteti solicita restrictionarea procesarii in anumite circumstante.
- **Dreptul la opozitie** (Art. 21) — Puteti obiecta la procesarea bazata pe interes legitim. Nota: procesarea QRChat este bazata pe executarea contractului (Art. 6(1)(b)), nu pe interes legitim.
- **Dreptul de a depune plangere** la o autoritate de supraveghere. Autoritatea relevanta depinde de tara dvs. de rezidenta. Pentru Republica Moldova: Centrul National pentru Protectia Datelor cu Caracter Personal (NCPDP), Chisinau.
- **Dreptul la stergere (Art. 17)** — "Dreptul de a fi uitat." Dezinstalarea app-ului sterge toate datele locale. Contactati-ne pentru stergerea datelor server-side.
- **Dreptul la portabilitatea datelor (Art. 20)** — Datele dvs. sunt stocate local pe dispozitiv in formatul aplicatiei.
- **Timp de raspuns:** Vom raspunde la orice cerere in termen de 30 de zile calendaristice, conform Art. 12(3) GDPR.

#### 9.3 For California Residents (CCPA/CPRA — California Civil Code 1798.100 et seq.)
- **Right to Know** (1798.100): Puteti solicita categoriile si piesele specifice de date colectate.
- **Right to Delete** (1798.105): Puteti solicita stergerea datelor server-side.
- **Right to Opt-Out of Sale** (1798.120): QRChat **nu vinde** date personale. Nu exista "Do Not Sell" button deoarece nu exista vanzare de date.
- **Right to Non-Discrimination** (1798.125): Nu veti fi discriminat pentru exercitarea drepturilor CCPA.
- **No Targeted Advertising:** QRChat nu foloseste date pentru publicitate targetata.
- **Sensitive Personal Information:** QRChat nu colecteaza informatii personale sensibile asa cum sunt definite de CPRA (Social Security numbers, financial account, geolocation, etc.)
- **Disclosure:** In ultimele 12 luni, QRChat nu a vandut si nu a partajat informatii personale ale niciunui utilizator.

#### 9.4 For Republic of Moldova Residents (Legea Nr. 133/2011)
- Dreptul de acces la datele cu caracter personal
- Dreptul la rectificarea datelor inexacte
- Dreptul de a depune plangere la Centrul National pentru Protectia Datelor cu Caracter Personal (NCPDP), Chisinau, Republica Moldova
- Nota: Legea Nr. 195/2024 (noua lege a protectiei datelor, aliniata la GDPR) va intra in vigoare pe 23 august 2026 si va inlocui Legea 133/2011.

**Impus de:** GDPR Art. 13(2)(b)(c)(d), Art. 15-22, CCPA 1798.100-1798.199, Legea RM 133/2011

### Sectiunea 10: Children's Privacy
- QRChat are rating 17+ pe App Store (Frequent/Intense: Mature/Suggestive Themes)
- QRChat **nu este directat catre copii** sub 13 ani (COPPA) sau sub 16 ani (GDPR standard, unele state membre 13-16)
- QRChat **nu colecteaza cunostiin** informatii personale de la copii
- Deoarece QRChat nu necesita inregistrare si nu colecteaza date personale identificabile, riscul de colectare de date de la minori este minimal
- **Parenti/tutori:** Daca credeti ca un copil sub 13 ani foloseste QRChat, contactati-ne
- **COPPA Rule 2025 (updated April 2025, compliance deadline April 22, 2026):** QRChat respecta noile cerinte COPPA prin design — nu colecteaza date personale de la copii, nu necesita consimtamant parental deoarece nu se colecteaza PII.
- **Impus de:** COPPA (16 CFR Part 312), GDPR Art. 8, Apple 5.1.4, Google Play Families Policy

### Sectiunea 11: Cookies, Tracking & ePrivacy
- QRChat **nu foloseste cookies** (aplicatie mobila nativa, fara componenta web in-app)
- QRChat **nu foloseste tracking pixels, device fingerprinting, sau alte tehnologii de urmarire**
- QRChat **nu utilizeaza advertising identifiers** (IDFA, IDFV, GAID)
- QRChat **nu partajeaza date cu retele de advertising sau analytics third-party**
- Privacy policy webpage (docs/privacy.html) — nu seteaza cookies
- **ePrivacy Directive (2002/58/EC):** Nu se aplica in mod direct deoarece QRChat nu stocheaza si nu acceseaza informatii pe dispozitivul utilizatorului in scopuri de tracking. Toate stocarea pe device e strict functionala (mesaje, chei, setari).
- **Impus de:** ePrivacy Directive Art. 5(3), GDPR Recital 30

### Sectiunea 12: Security Measures
Lista completa de masuri tehnice de securitate:
- End-to-end encryption (TweetNaCl: XSalsa20-Poly1305, X25519, Ed25519)
- SQLCipher (AES-256) pentru baza de date locala
- iOS Keychain cu Secure Enclave / Android Keystore pentru chei private
- Arhitectura anonima mailbox (separare userId/mailboxId/pushToken in doua Map-uri distincte)
- Zero plaintext storage pe server (niciun mesaj nu e stocat in clar)
- WebSocket connections over TLS (wss://)
- Server-side message expiry (maximum 48 ore)
- Push notification throttling (max 1 per 30 secunde per mailbox)
- Pending message queue limits (max 1000 mesaje sau 50MB per user — DoS protection)
- No server-side logging of message content
- Contact exchange via QR code only (no server-side contact matching)
- **Impus de:** GDPR Art. 32, Apple 5.1 Guideline 1.6

### Sectiunea 13: Encryption Export Compliance
- QRChat foloseste encryption: TweetNaCl/NaCl, SQLCipher
- `ITSAppUsesNonExemptEncryption` = `YES` in Info.plist
- Encryption e folosita exclusiv pentru protejarea datelor utilizatorului (messaging E2E), nu pentru obscurarea comunicatiilor cu un server C2
- Aplicabila: US Export Administration Regulations (EAR), BIS Category 5 Part 2
- **Impus de:** Apple Export Compliance, US BIS regulations

### Sectiunea 14: Automated Decision-Making
- QRChat **nu utilizeaza** procesare automata a deciziilor sau profilare in sensul Art. 22 GDPR
- Nu exista algoritmi de recomandare, scoring, sau alte procese automatizate care afecteaza utilizatorii
- **Impus de:** GDPR Art. 13(2)(f), Art. 22

### Sectiunea 15: Changes to This Policy
- Vom actualiza aceasta politica cand e necesar
- Modificarile semnificative vor fi comunicate prin actualizarea datei "Last Updated" si/sau prin notificare in aplicatie
- Utilizarea continua a QRChat dupa modificari constituie acceptarea politicii actualizate
- Politica va fi revizuita cel putin anual (conform CCPA requirement)
- **Impus de:** Apple 5.1, CCPA annual update requirement, GDPR Art. 13(3)

### Sectiunea 16: Contact Information
- **Data controller:** Ruslan Constantinovici
- **Email:** ruscon2001@gmail.com
- **Adresa:** Chisinau, Republica Moldova
- **Raspuns garantat:** In termen de 30 de zile calendaristice
- **Limbile acceptate:** Engleza, Romana, Rusa, Franceza
- **Impus de:** GDPR Art. 13(1)(a)(b), CCPA 1798.130

### Sectiunea 17: Applicable Law & Jurisdiction
- Aceasta politica e guvernata de legislatia Republicii Moldova
- Pentru rezidentii UE/SEE, drepturile GDPR se aplica indiferent de jurisdictia politicii
- Pentru rezidentii California, drepturile CCPA/CPRA se aplica indiferent de jurisdictia politicii
- **Impus de:** GDPR Art. 3 (territorial scope), CCPA 1798.140(c)

---

## Cerinte de format HTML

### Design
- Pastreaza design-ul existent din `docs/privacy.html` (culorile QRChat: #FF6B00 orange, #1a1a2e dark)
- Font: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto (system fonts)
- Max-width: 720px, centered
- Responsive (mobile-first — multi utilizatori vor citi pe telefon)
- Tabele stilizate, highlight boxes pentru informatii importante
- Sectiune colapsabila (details/summary) pentru sectiuni lungi (optional, dar recomandat)
- Scroll-to-top button (optional)
- Limba: ENGLEZA (pagina principala). Versiuni traduse vor fi gestionate de frontend-engineer.

### SEO & Accessibility
- Heading hierarchy corecta (h1 > h2 > h3)
- `lang="en"` pe `<html>`
- `<meta name="description" content="QRChat Privacy Policy...">`
- Link-uri cu `rel="noopener noreferrer" target="_blank"` pentru link-uri externe
- Contrast suficient (WCAG AA)
- Skip-to-content link (optional)

### Hosting
- Fisierul final: `/Users/ruslanconstantinovici/QRChat/docs/privacy.html`
- Servit de serverul QRChat la ruta `/privacy` (deja configurat in index.js)
- URL public: `https://exciting-success-production-d272.up.railway.app/privacy`
- Trebuie sa fie accesibil fara autentificare, fara geoblock, fara PDF

---

## Criterii de succes

- [ ] Toate cele 17 sectiuni prezente si complete
- [ ] Fiecare afirmatie tehnica validata cu audit-ul security-engineer
- [ ] Conformitate GDPR Art. 13 — toate cele 14 puncte obligatorii incluse:
  1. Identitate controller
  2. Contact DPO (sau explicatie ca nu e necesar)
  3. Scopuri procesare + baza legala
  4. Interese legitime (daca aplicabil)
  5. Destinatari date
  6. Transferuri internationale
  7. Perioadele de retentie
  8. Drepturile data subject
  9. Dreptul de retragere consimtamant
  10. Dreptul de plangere la autoritate
  11. Obligativitatea furnizarii datelor
  12. Procesare automata/profilare
  13. Actualizari la politica
  14. Contact
- [ ] Conformitate CCPA/CPRA:
  - Categoriile de date colectate in ultimele 12 luni
  - Declaratia "We do not sell personal information"
  - Right to Know, Delete, Opt-Out, Non-Discrimination
  - Sensitive Personal Information disclosure
  - Data retention specifics (timeframes sau methodology)
- [ ] Conformitate Apple 5.1.1(i):
  - Ce date se colecteaza
  - Cum se colecteaza
  - Toate utilizarile
  - Third-party protectie egala confirmata
  - Retentie/deletion policies
  - Cum se revoca consimtamantul
- [ ] Conformitate Google Play User Data Policy:
  - Privacy policy la URL accesibil (non-PDF, non-geofenced)
  - Entitatea din Play Console listing apare in policy
  - Toate categoriile de date declarate
  - Encryption in transit mentionat
  - End-to-end encryption declarat
- [ ] Conformitate COPPA (updated April 2025)
- [ ] Conformitate Legea RM 133/2011
- [ ] Conformitate ePrivacy Directive (no cookies declaration)
- [ ] HTML valid, responsive, accesibil
- [ ] Email contact: ruscon2001@gmail.com (nu privacy@qrchat.app — domeniu inexistent)
- [ ] Data efectiva si "Last Updated" corecte
- [ ] Fiecare sectiune cu impunere legala marcata (pentru audit trail)
- [ ] Rezultatul scris in `/Users/ruslanconstantinovici/QRChat/docs/privacy.html`

---

## Dependente

- **Asteapta** `agent-runtime/outputs/privacy-security-audit.md` de la security-engineer inainte de a incepe scrierea.
- **Dupa finalizare**, notifica frontend-engineer prin `agent-runtime/messages/release-to-frontend.md` ca privacy.html e gata.
- **Dupa finalizare**, actualizeaza `agent-runtime/state/status.md`.
- **Deploy:** Dupa ce scrii fisierul, testeaza ca se serveste corect la `/privacy` pe server (local test sau prod).

---

## Referinte legislative (link-uri directe)

- GDPR full text: https://gdpr-info.eu/
- GDPR Art. 13: https://gdpr-info.eu/art-13-gdpr/
- CCPA statute: https://oag.ca.gov/privacy/ccpa
- CPRA regulations effective Jan 1, 2026: https://cppa.ca.gov/regulations/
- Apple App Store Review Guidelines 5.1: https://developer.apple.com/app-store/review/guidelines/#privacy
- Apple App Privacy Details: https://developer.apple.com/app-store/app-privacy-details/
- Google Play User Data Policy: https://support.google.com/googleplay/android-developer/answer/10144311
- Google Play Data Safety: https://support.google.com/googleplay/android-developer/answer/10787469
- COPPA Rule: https://www.ftc.gov/legal-library/browse/rules/childrens-online-privacy-protection-rule-coppa
- Moldova Law 133/2011: https://www.dlapiperdataprotection.com/index.html?t=law&c=MD
- Moldova Law 195/2024 (new, effective Aug 23, 2026): https://csometer.info/updates/moldova-new-data-protection-law-adopted
- ePrivacy Directive: https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=CELEX:32002L0058
- EU-US Data Privacy Framework: https://commission.europa.eu/law/law-topic/data-protection/international-dimension-data-protection/eu-us-data-transfers_en
- Signal Privacy Policy (reference model): https://signal.org/legal/
