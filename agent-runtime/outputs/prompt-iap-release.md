# Prompt: Release Engineer — iOS Project IAP Configuration

## Rol
Tu esti **release-engineer** pentru QRChat. Sarcina ta este sa configurezi proiectul iOS pentru Apple In-App Purchase: capability StoreKit, entitlements, Podfile update, si StoreKit Configuration File.

## Context proiect
- **Codebase:** `/Users/ruslanconstantinovici/QRChat`
- **Bundle ID:** `com.ruslan.qrchat`
- **Team ID:** `FK7BU478KX`
- **Product ID:** `com.ruslan.qrchat.unlimited`
- **Tip produs:** Non-consumable ($2.99)
- **Versiune:** 4.1.0 (build 16)
- **React Native:** 0.84
- **Xcode project:** `ios/QRChat.xcodeproj`
- **Certificate:** "Apple Development: ruscon2002@mail.ru (2NYSSGS5Y2)"

## Fisiere de citit OBLIGATORIU
1. `ios/QRChat.xcodeproj/project.pbxproj` — Xcode project config
2. `ios/QRChat/QRChat.entitlements` — entitlements actuale (daca exista)
3. `ios/Podfile` — CocoaPods config
4. `package.json` — dependente (react-native-iap NU exista inca!)

## Ce trebuie sa faci

### 1. Instaleaza `react-native-iap` si `react-native-nitro-modules`

```bash
cd /Users/ruslanconstantinovici/QRChat
npm install react-native-iap react-native-nitro-modules
cd ios && pod install
```

**IMPORTANT:** `react-native-nitro-modules` este peer dependency obligatorie pentru `react-native-iap` v14.4+.

Verifica dupa instalare:
- `package.json` contine `"react-native-iap"` si `"react-native-nitro-modules"` in dependencies
- `ios/Podfile.lock` contine `RNIap` pod
- Nu sunt erori la `pod install`

### 2. Adauga StoreKit capability in Xcode project

Aceasta se face prin modificarea `project.pbxproj`. Sunt 2 metode:

#### Metoda A — Prin Xcode (recomandata)

1. Deschide `ios/QRChat.xcworkspace` in Xcode
2. Selecteaza target QRChat
3. Tab "Signing & Capabilities"
4. Click "+" → cauta "In-App Purchase" → adauga
5. Xcode va modifica automat `project.pbxproj` si va crea/actualiza entitlements

#### Metoda B — Manual (daca Xcode nu e disponibil)

##### a. Creaza/actualizeaza `ios/QRChat/QRChat.entitlements`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.developer.in-app-payments</key>
    <array>
        <string>merchant.com.ruslan.qrchat</string>
    </array>
</dict>
</plist>
```

**IMPORTANT:** Daca fisierul entitlements exista deja cu alte chei, ADAUGA cheia de mai sus — nu suprascrie fisierul!

##### b. Actualizeaza `project.pbxproj`

In `project.pbxproj`, cauta sectiunea `buildSettings` pentru target QRChat si adauga (daca nu exista deja):

```
CODE_SIGN_ENTITLEMENTS = QRChat/QRChat.entitlements;
```

Aceasta linie trebuie adaugata in AMBELE sectiuni `buildSettings` (Debug si Release).

Daca nu exista sectiunea `SystemCapabilities`, cauta `attributes = {` si adauga:

```
SystemCapabilities = {
    com.apple.InAppPurchase = {
        enabled = 1;
    };
};
```

### 3. Creaza StoreKit Configuration File (pentru testare locala)

Creaza `ios/QRChat/StoreKitConfig.storekit`:

```json
{
  "identifier" : "com.ruslan.qrchat.storekit",
  "type" : "com.apple.product-type.storekit-configuration",
  "version" : 1,
  "products" : [
    {
      "displayPrice" : "2.99",
      "familyShareable" : false,
      "internalID" : "1",
      "localizations" : [
        {
          "description" : "Unlock unlimited contacts in QRChat",
          "displayName" : "QRChat Unlimited",
          "locale" : "en_US"
        },
        {
          "description" : "Deblocheaza contacte nelimitate in QRChat",
          "displayName" : "QRChat Unlimited",
          "locale" : "ro"
        },
        {
          "description" : "Ouvrez un nombre illimite de contacts dans QRChat",
          "displayName" : "QRChat Unlimited",
          "locale" : "fr"
        },
        {
          "description" : "Разблокируйте неограниченные контакты в QRChat",
          "displayName" : "QRChat Unlimited",
          "locale" : "ru"
        }
      ],
      "productID" : "com.ruslan.qrchat.unlimited",
      "referenceName" : "QRChat Unlimited",
      "type" : "NonConsumable"
    }
  ],
  "settings" : {
    "_failTransactionsEnabled" : false,
    "_storeKitErrors" : [],
    "_timeRate" : 0
  }
}
```

**Nota:** Acest fisier permite testare locala pe simulator FARA App Store Connect configurat. Xcode il va folosi automat cand rulezi pe simulator.

### 4. Configureaza StoreKit Configuration in Xcode scheme

Pentru ca StoreKit Configuration File sa fie activ in development:

1. Xcode → Product → Scheme → Edit Scheme
2. Run → Options → StoreKit Configuration → selecteaza `StoreKitConfig.storekit`
3. Confirma

Sau manual, in `ios/QRChat.xcscheme` (daca exista), adauga in sectiunea `<LaunchAction>`:
```xml
<StoreKitConfigurationFileReference
   identifier = "../../QRChat/StoreKitConfig.storekit">
</StoreKitConfigurationFileReference>
```

### 5. Verifica Podfile

Dupa `pod install`, verifica ca `ios/Podfile` nu are probleme. Asigura-te ca:
- Minimum iOS deployment target este iOS 15.0+ (necesar pentru StoreKit 2)
- Pod `RNIap` apare in `Podfile.lock`

Daca deployment target este < 15:
```ruby
# In Podfile, la inceputul fisierului:
platform :ios, '15.0'
```

**IMPORTANT:** React Native 0.84 suporta minim iOS 15.1, deci NU ar trebui sa fie o problema. Verifica totusi.

### 6. Actualizeaza versiunea pentru IAP submission

In `project.pbxproj`:
- `MARKETING_VERSION` = 4.1.0 (sau 4.2.0 daca se decide increment)
- `CURRENT_PROJECT_VERSION` = 17 (increment de la 16)

### 7. App Store Connect Setup (documentatie, nu automatizare)

Scrie in `agent-runtime/outputs/appstore-iap-setup.md` instructiunile pentru Ruslan:

```markdown
# App Store Connect — IAP Setup Instructions

## Pasi in App Store Connect (manual, necesita cont developer):

1. Login la https://appstoreconnect.apple.com
2. My Apps → QRChat → Features → In-App Purchases
3. Click "+" → Non-Consumable
4. Product ID: com.ruslan.qrchat.unlimited
5. Reference Name: QRChat Unlimited
6. Price: Tier 1 ($0.99) — NU! Selecteaza manual $2.99 (Tier 3)
7. Localizations:
   - EN: "QRChat Unlimited" / "Unlock unlimited contacts"
   - RO: "QRChat Unlimited" / "Deblocheaza contacte nelimitate"
   - RU: "QRChat Unlimited" / "Разблокируйте неограниченные контакты"
   - FR: "QRChat Unlimited" / "Contacts illimites"
8. Review screenshot: screenshot din UpgradeScreen (pe simulator)
9. Status: Ready to Submit
```

## Reguli stricte

1. **NU modifica** fisiere din `src/` — acelea sunt pentru architect/frontend
2. **NU modifica** `server/` — e treaba backend-engineer
3. Dupa `npm install` si `pod install`, verifica ca build-ul reuseste:
   ```bash
   cd /Users/ruslanconstantinovici/QRChat
   npx react-native run-ios --simulator "iPhone 16e"
   ```
4. **NU face push la git** fara aprobarea lead-ului
5. Pastreaza codul de semnare existent — nu modifica team ID sau certificate
6. StoreKit Configuration File e DOAR pentru testare — nu afecteaza productia

## Dependente de alti agenti

- **architect** va crea `IAPService.ts` care apeleaza `initConnection()` — functioneaza doar DUPA ce tu adaugi StoreKit capability
- **frontend-engineer** va importa `IAPService` — functioneaza doar DUPA ce tu instalezi `react-native-iap`

**Tu trebuie sa fii PRIMUL care ruleaza** — ceilalti depind de npm install + pod install.

## Ordinea corecta a operatiilor

1. `npm install react-native-iap react-native-nitro-modules`
2. `cd ios && pod install`
3. Adauga StoreKit capability (entitlements + project.pbxproj)
4. Creaza StoreKit Configuration File
5. Build test: `npx react-native run-ios --simulator "iPhone 16e"`
6. Verifica ca build reuseste FARA erori
7. Scrie instructiunile App Store Connect
8. Actualizeaza status in `agent-runtime/state/status.md`

## Verificare finala

- [ ] `react-native-iap` si `react-native-nitro-modules` in `package.json` dependencies
- [ ] `pod install` a reusit fara erori
- [ ] `ios/QRChat/QRChat.entitlements` contine `com.apple.developer.in-app-payments`
- [ ] `project.pbxproj` contine `CODE_SIGN_ENTITLEMENTS`
- [ ] `StoreKitConfig.storekit` creat cu product `com.ruslan.qrchat.unlimited`
- [ ] Build pe simulator reuseste
- [ ] Build pe device fizic reuseste
- [ ] Instructiuni App Store Connect scrise
- [ ] Versiune incrementata (build 17)

## Deploy obligatoriu dupa modificari
```bash
# Simulator
npx react-native run-ios --simulator "iPhone 16e"
# Fizic
npx react-native run-ios --udid "00008140-00066CA02229801C"
```
