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

## Configurare locala completata

- `react-native-iap` v14.7.17 instalat
- `react-native-nitro-modules` v0.35.2 instalat
- StoreKit capability adaugat in project.pbxproj
- QRChat.entitlements creat cu com.apple.developer.in-app-payments
- StoreKitConfig.storekit creat pentru testare locala pe simulator
- Build version: 4.1.0 (build 17)

## StoreKit Configuration File

Fisierul `ios/QRChat/StoreKitConfig.storekit` permite testare IAP pe simulator fara App Store Connect.

Pentru a-l activa in Xcode:
1. Xcode → Product → Scheme → Edit Scheme
2. Run → Options → StoreKit Configuration → selecteaza `StoreKitConfig.storekit`
3. Confirma
