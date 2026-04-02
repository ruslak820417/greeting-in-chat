# PROMPT 5 — Fix-uri tehnice pre-submission (frontend-engineer)

**Agent:** frontend-engineer
**Proiect:** `/Users/ruslanconstantinovici/QRChat`
**Prioritate:** CRITICA — aceste fix-uri pot cauza rejection la App Store Review

---

## Context

QRChat v3.0.6 se pregateste pentru submission la App Store. Trebuie corectate cateva probleme tehnice care pot cauza rejection instant la Apple Review. Apple verifica strict ca:
1. Usage descriptions din Info.plist sa corespunda functionalitatii reale a app-ului
2. TARGETED_DEVICE_FAMILY sa fie corect setat
3. Sa nu existe text placeholder/debug in productie
4. Link-urile din app sa fie functionale

---

## Sarcina 1 — Sterge NSSiriUsageDescription din Info.plist

**Fisier:** `ios/QRChat/Info.plist`
**Linia:** 82-83

Exista aceasta intrare:
```xml
<key>NSSiriUsageDescription</key>
<string>QRChat can use Siri to send messages hands-free</string>
```

**De ce trebuie stearsa:** QRChat NU are integrare Siri (nu exista SiriKit Intents, nu exista INExtension in proiect). Apple respinge app-uri care declara usage descriptions pentru capabilitati pe care nu le folosesc — este o violare a Guideline 5.1.1 (Data Collection and Storage). Declararea unei capabilitati nefolosite sugereaza fie ca app-ul colecteaza date fara motiv, fie ca developorul nu intelege ce face app-ul.

**Actiune exacta:**
1. Deschide `ios/QRChat/Info.plist`
2. Sterge complet liniile 82-83 (cheia `NSSiriUsageDescription` si valoarea ei)
3. Verifica ca XML-ul ramane valid dupa stergere

**ATENTIE:** Sterge DOAR NSSiriUsageDescription. NU sterge celelalte usage descriptions (NSCameraUsageDescription, NSMicrophoneUsageDescription, NSPhotoLibraryUsageDescription, etc.) — acestea sunt necesare.

---

## Sarcina 2 — Schimba TARGETED_DEVICE_FAMILY de la "1,2" la "1"

**Fisier:** `ios/QRChat.xcodeproj/project.pbxproj`
**Linii:** 298 si 331

Exista in doua locuri (Debug si Release):
```
TARGETED_DEVICE_FAMILY = "1,2";
```

**De ce trebuie schimbat:** Valoarea "1,2" inseamna iPhone + iPad. QRChat nu este optimizat pentru iPad — nu exista layout-uri adaptive, nu exista split view support, iar UI-ul este proiectat exclusiv pentru iPhone. Daca trimiti cu "1,2", Apple va testa pe iPad si va respinge daca experienta nu e buna.

**IMPORTANT:** Apple NU permite sa retragi suportul iPad daca app-ul a fost deja publicat cu suport iPad. Deoarece QRChat este la prima submisie, este OK sa setam doar iPhone. Daca app-ul ar fi fost deja pe store cu iPad support, ar trebui o strategie diferita.

**Actiune exacta:**
1. Deschide `ios/QRChat.xcodeproj/project.pbxproj`
2. Inlocuieste AMBELE aparitii:
   - Linia 298: `TARGETED_DEVICE_FAMILY = "1,2";` → `TARGETED_DEVICE_FAMILY = 1;`
   - Linia 331: `TARGETED_DEVICE_FAMILY = "1,2";` → `TARGETED_DEVICE_FAMILY = 1;`
3. Valoarea `1` = doar iPhone. (`2` = doar iPad, `1,2` = Universal)

**Optional dar recomandat:** In `Info.plist`, poti sterge si sectiunea `UISupportedInterfaceOrientations~ipad` (liniile 67-73) deoarece nu va mai fi relevanta:
```xml
<key>UISupportedInterfaceOrientations~ipad</key>
<array>
    <string>UIInterfaceOrientationLandscapeLeft</string>
    <string>UIInterfaceOrientationLandscapeRight</string>
    <string>UIInterfaceOrientationPortrait</string>
    <string>UIInterfaceOrientationPortraitUpsideDown</string>
</array>
```

---

## Sarcina 3 — Verifica ca nu exista text placeholder/lorem ipsum/coming soon

**Directorul:** `src/screens/`

Am verificat deja si rezultatele sunt:

**OK — fara probleme:**
- Toate aparitiile "placeholder" din screens sunt atribute React Native `placeholder=""` pe componente `TextInput` (e.g., "QRCHAT-XXXX-XXXX-XXXX", search placeholders). Acestea sunt CORECTE si necesare.
- Nu exista "lorem ipsum" sau "coming soon" nicaieri.

**De investigat:**
- `src/screens/UpgradeScreen.tsx` linia 58: exista un comentariu `// TODO: StoreKit 2 implementare`. Aceasta este doar un comentariu in cod, nu text vizibil pentru utilizator, deci NU va cauza rejection. Dar verifica ca ecranul Upgrade nu afiseaza text placeholder vizibil utilizatorului.

**Actiune exacta:**
1. Deschide fiecare fisier din `src/screens/` si cauta cu regex: `(?i)(lorem ipsum|coming soon|TODO.*text|placeholder.*text|test.*only|debug.*mode)`
2. Ignora: atributele `placeholder=` pe TextInput (sunt necesare), comentariile `// TODO` (nu sunt vizibile)
3. Raporteaza: orice text hardcodat vizibil care pare placeholder sau neterminat
4. Verifica vizual UpgradeScreen ca afiseaza continut real, nu stub

---

## Sarcina 4 — Verifica link-ul Privacy Policy din SettingsScreen

**Fisier:** `src/screens/SettingsScreen.tsx`

**Problema identificata:** SettingsScreen.tsx NU contine NICIUN link catre Privacy Policy! Am cautat "privacy" si "policy" in fisier si nu exista nicio referinta.

Info.plist contine `<key>privacyPolicyURL</key><string>https://qrchat.app/privacy</string>` dar acest link:
1. Nu este afisat nicaieri in UI
2. Probabil nu functioneaza (domeniul qrchat.app poate sa nu existe)

**Actiune exacta:**

### Pas 1: Adauga link Privacy Policy in SettingsScreen
In sectiunea "About" (dupa `aboutStrip`, inainte de butonul "Delete all data"), adauga un buton de Privacy Policy:

```tsx
<TouchableOpacity
  style={[styles.settingRow, { backgroundColor: C.surface, borderColor: C.border }]}
  onPress={() => Linking.openURL('https://qrchat.app/privacy')}
  accessibilityLabel="Privacy Policy"
  accessibilityRole="link"
>
  <View style={{ flexDirection: 'row', alignItems: 'center', flex: 1 }}>
    <Ionicons name="shield-checkmark-outline" size={20} color={C.accent} style={{ marginRight: 12 }} />
    <Text style={[styles.settingLabel, { color: C.text }]}>{t('settings.privacyPolicy', { defaultValue: 'Privacy Policy' })}</Text>
  </View>
  <Ionicons name="open-outline" size={16} color={C.textSecondary} />
</TouchableOpacity>
```

### Pas 2: Verifica daca URL-ul functioneaza
Testeaza: `curl -s -o /dev/null -w "%{http_code}" https://qrchat.app/privacy`
- Daca raspunde 200: OK, pastreaza URL-ul
- Daca raspunde 404/timeout/eroare: **coordoneaza-te cu release-engineer** care va crea pagina Privacy Policy (vezi Prompt 7). Intre timp, foloseste un URL temporar sau lasa URL-ul actual — release-engineer il va face functional.

### Pas 3: Verifica ca link-ul din Info.plist coincide
URL-ul din `ios/QRChat/Info.plist` linia 92 (`privacyPolicyURL`) trebuie sa fie identic cu cel din SettingsScreen. Daca release-engineer schimba URL-ul, actualizeaza si Info.plist.

---

## Sarcina 5 — Verifica ca nu exista alte link-uri broken

**Actiune rapida:**
```bash
grep -rn "https://" src/screens/ | grep -v node_modules | grep -v "\.map"
```

Verifica fiecare URL gasit ca:
1. Nu e un link de test/development
2. Raspunde cu HTTP 200

---

## Dupa finalizare

1. Ruleaza: `cd /Users/ruslanconstantinovici/QRChat && npx react-native run-ios --device` (deploy pe telefon fizic)
2. Ruleaza: `npx react-native run-ios --simulator="iPhone 16e"` (deploy pe simulator)
3. Verifica vizual ca SettingsScreen arata corect si link-ul Privacy Policy deschide browser-ul
4. Actualizeaza `agent-runtime/state/status.md`
