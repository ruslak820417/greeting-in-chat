# Audit i18n — QRChat v4.0.0

**Data auditului:** 2026-03-21
**Fisiere auditate:** en.json (referinta), ro.json, ru.json, fr.json
**Total chei per fisier:** ~220 chei (structura identica in toate 4 fisierele)

---

## Chei lipsa

| Cheie | Lipsa din |
|-------|-----------|
| *(niciuna)* | Toate 4 fisierele au structura identica de chei |

Toate fisierele au exact aceleasi sectiuni si chei. Nicio cheie lipsa.

---

## Texte in limba gresita

| Cheie | Fisier | Text gresit | Trebuia |
|-------|--------|-------------|---------|
| `home.unlimited` | ro.json | "Unlimited" (engleza) | "Nelimitat" |
| `home.unlimited` | ru.json | "Unlimited" (engleza) | "Безлимитный" |
| `home.unlimited` | fr.json | "Unlimited" (engleza) | "Illimite" |
| `chat.onlineRelay` | ro.json | "Online (Relay)" (engleza) | "Conectat (Relay)" |

**Re: ecranul PODDERJKA (Support) din ru.json:**
Cheile `settings.support`, `settings.contactSupport`, `settings.termsOfService`, `settings.privacyPolicy` din ru.json sunt CORECT traduse in rusa. Daca ecranul afiseaza texte in romana, cauza este probabil in codul componentei (texte hardcodate sau chei de traducere gresite referentiate in componenta Settings).

---

## Texte netraduse (copii din EN)

| Cheie | Fisier | Text identic cu EN |
|-------|--------|--------------------|
| `home.unlimited` | ro.json | "Unlimited" |
| `home.unlimited` | ru.json | "Unlimited" |
| `home.unlimited` | fr.json | "Unlimited" |
| `chat.p2pDirect` | ro.json | "P2P Direct" (posibil intentional — termen tehnic) |
| `chat.onlineRelay` | ro.json | "Online (Relay)" |

---

## Diacritice lipsa in RO (ro.json) — CRITIC

Multe stringuri din ro.json nu au diacriticele romanesti (a, i, s, t, a). Aceasta este o problema vizibila pentru utilizator.

| Cheie | Text curent (fara diacritice) | Text corect |
|-------|-------------------------------|-------------|
| `home.searchResult` | "Rezultat cautare" | "Rezultat cautare" |
| `home.openConversation` | "Deschide conversatia" | "Deschide conversatia" |
| `home.addContact` | "Adauga contact" | "Adauga contact" |
| `home.showQR` | "Arata codul meu QR" | "Arata codul meu QR" |
| `chat.removeImage` | "Sterge imaginea" | "Sterge imaginea" |
| `chat.scrollToBottom` | "Deruleaza in jos" | "Deruleaza in jos" |
| `chat.stopRecording` | "Opreste inregistrarea" | "Opreste inregistrarea" |
| `chat.discardRecording` | "Renunta la inregistrare" | "Renunta la inregistrare" |
| `chat.attach` | "Ataseaza fisier" | "Ataseaza fisier" |
| `chat.takePhoto` | "Fotografiaza" | "Fotografiaza" |
| `chat.report` | "Raporteaza" | "Raporteaza" |
| `chat.reportTitle` | "Raporteaza mesaj" | "Raporteaza mesaj" |
| `chat.reportHarassment` | "Hartuire" | "Hartuire" |
| `chat.reportInappropriate` | "Continut inadecvat" | "Continut inadecvat" |
| `chat.deleteImageConfirm` | "Stergi aceasta imagine?" | "Stergi aceasta imagine?" |
| `contactProfile.reportUser` | "Raporteaza utilizator" | "Raporteaza utilizator" |
| `contactProfile.reportTitle` | "Raporteaza utilizator" | "Raporteaza utilizator" |
| `settings.contactSupport` | "Contacteaza suportul" | "Contacteaza suportul" |
| `settings.privacyPolicy` | "Politica de confidentialitate" | "Politica de confidentialitate" |
| `setup.agreeToTerms` | "...si Politica de Confidentialitate" | "...si Politica de Confidentialitate" |
| `setup.termsRequiredDesc` | "Trebuie sa accepti..." | "Trebuie sa accepti..." |
| `terms.*` | **Intreaga sectiune terms** lipseste diacritice | Necesita rescriere completa cu diacritice |

**Total stringuri afectate in RO: ~35+** (intreaga sectiune `terms` are ~15 chei fara diacritice)

---

## Accente lipsa in FR (fr.json) — CRITIC

Multe stringuri din fr.json nu au accentele franceze (e, e, e, a, a, i, etc.).

| Cheie | Text curent (fara accente) | Text corect |
|-------|----------------------------|-------------|
| `home.searchResult` | "Resultat de recherche" | "Resultat de recherche" |
| `chat.videoCall` | "Appel video" | "Appel video" |
| `chat.scrollToBottom` | "Defiler vers le bas" | "Defiler vers le bas" |
| `chat.stopRecording` | "Arreter l'enregistrement" | "Arreter l'enregistrement" |
| `chat.reportHarassment` | "Harcelement" | "Harcelement" |
| `chat.reportInappropriate` | "Contenu inapproprie" | "Contenu inapproprie" |
| `settings.privacyPolicy` | "Politique de confidentialite" | "Politique de confidentialite" |
| `setup.agreeToTerms` | "...Politique de confidentialite" | "...Politique de confidentialite" |
| `terms.lastUpdated` | "Derniere mise a jour" | "Derniere mise a jour" |
| `terms.acceptanceBody` | "En telechargeant...d'etre lie..." | Lipsesc accente pe tot textul |
| `terms.descriptionBody` | "...chiffree..." | Lipsesc accente pe tot textul |
| `terms.eligibilityTitle` | "3. Eligibilite" | "3. Eligibilite" |
| `terms.privacyTitle` | "4. Confidentialite et donnees" | "4. Confidentialite et donnees" |
| `terms.terminationTitle` | "6. Resiliation" | "6. Resiliation" |
| `terms.disclaimerTitle` | "7. Clause de non-responsabilite" | "7. Clause de non-responsabilite" |
| `terms.*Body` | **Toate body-urile din terms** lipsesc accente | Necesita rescriere completa cu accente |

**Total stringuri afectate in FR: ~30+** (intreaga sectiune `terms` are ~15 chei fara accente)

---

## Inconsistente de stil — Tu vs. Vous / Ty vs. Vy

### FR (fr.json) — Amestec tutoiement/vouvoiement

| Sectiune | Forma folosita | Exemplu |
|----------|---------------|---------|
| welcome, setup, home, chat, contacts, qrScan | **tu/toi/tes** (informal) | "Scanne un QR code", "Es-tu sur..." |
| approval | **vous/votre** (formal) | "votre demande de connexion" |
| upgrade | **vous/vos** (formal) | "Vous avez {{count}} contacts" |
| phoneContacts | **vous/vos** (formal) | "Autorisez QRChat a acceder a vos contacts" |
| terms | **vous** (formal) | Corect — textul legal trebuie sa fie formal |

**Problema:** approval si upgrade ar trebui sa fie consistente cu restul aplicatiei (tu/toi). Doar terms poate ramane formal.

### RU (ru.json) — Amestec ty/vy

| Sectiune | Forma folosita | Exemplu |
|----------|---------------|---------|
| welcome, setup, home, chat, contacts, qrScan | **ty/tvoy** (informal) | "Tvoy QR-kod", "Ty uveren..." |
| setup.termsRequiredDesc | **Vy** (formal) | "Vy dolzhny prinyat'" |
| approval | **vy/vash** (formal) | "vashego zaprosa", "Vy prinyali" |
| upgrade | **vy** (formal) | "U vas {{count}} kontaktov" |
| phoneContacts | **vy** (formal) | "Razreshite QRChat dostup..." |
| terms | **vy** (formal) | Corect — text legal |

**Problema:** Aceeasi inconsistenta — approval si upgrade ar trebui sa fie informal (ty) ca restul app-ului.

---

## Placeholder-uri {{...}}

| Status | Detalii |
|--------|---------|
| **OK** | Toate placeholder-urile ({{name}}, {{count}}, {{limit}}, {{size}}, {{time}}, {{date}}, {{current}}, {{total}}) sunt identice in toate 4 fisierele |

Verificate toate cele ~25 de chei cu placeholder-uri. Nicio discrepanta.

---

## Alte probleme

### 1. Brand consistency
- `home.unlimited` = "Unlimited" in toate limbile — daca e brand name, OK; daca nu, trebuie tradus

### 2. Sectiunea `terms` — calitate scazuta in RO si FR
Intreaga sectiune `terms` in ro.json si fr.json pare tradusa fara diacritice/accente. Aceasta sugereaza o traducere automata sau copy-paste dintr-un context fara suport diacritice. **Necesita rescriere completa.**

### 3. Support screen — investigare necesara in cod
Daca ecranul Support afiseaza texte amestecate (rus + romana), problema NU este in fisierele de traducere — cheile din ru.json sunt corect traduse. Cauza posibila:
- Texte hardcodate in componenta SettingsScreen
- Fallback la alta limba in loc de rusa
- Chei de traducere gresite referentiate in componenta de suport

**Recomandare:** Verificati fisierele din `src/screens/SettingsScreen.tsx` sau componenta Support pentru texte hardcodate.

---

## Sumar

| Categorie | Severitate | Numar probleme |
|-----------|-----------|----------------|
| Chei lipsa | - | 0 |
| Texte in limba gresita | **MEDIE** | 4 |
| Texte netraduse (EN) | **MEDIE** | 3-5 |
| Diacritice lipsa RO | **CRITICA** | ~35 stringuri |
| Accente lipsa FR | **CRITICA** | ~30 stringuri |
| Inconsistenta tu/vous (FR) | **MEDIE** | ~15 stringuri |
| Inconsistenta ty/vy (RU) | **MEDIE** | ~15 stringuri |
| Placeholder-uri | OK | 0 |

**Prioritate de corectare:**
1. **URGENT:** Diacritice RO + Accente FR (afecteaza vizibil calitatea)
2. **IMPORTANT:** Traducerea `home.unlimited` in toate limbile
3. **IMPORTANT:** Unificarea tu/vous in FR si ty/vy in RU
4. **INVESTIGARE:** Ecranul Support — verificare cod componenta
