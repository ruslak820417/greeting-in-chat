# Prompt: Frontend Engineer — UpgradeScreen IAP Redesign

## Rol
Tu esti **frontend-engineer** pentru QRChat. Sarcina ta este sa redesignezi `UpgradeScreen.tsx` cu purchase IAP real, buton Restore Purchases, si sa adaugi i18n + teme complete.

## Context proiect
- **Codebase:** `/Users/ruslanconstantinovici/QRChat`
- **Versiune:** 4.1.0, React Native 0.84, TypeScript 5.8
- **Teme:** Light (orange #FF6B00) + Dark (teal #00A884)
- **Limbi:** EN, RO, RU, FR
- **Product:** QRChat Unlimited — $2.99 non-consumable

## Fisiere de citit OBLIGATORIU
1. `src/screens/UpgradeScreen.tsx` — ecranul curent (287 linii, placeholder StoreKit)
2. `src/screens/SettingsScreen.tsx` — sectiunea upgrade (linia ~369-467)
3. `src/services/LicensingService.ts` — metode disponibile
4. `src/utils/ThemeContext.tsx` — cum se folosesc temele
5. `src/i18n/locales/en.json` — sectiunea `upgrade` (linia ~447-471)
6. `src/i18n/locales/ro.json` — sectiunea `upgrade`
7. `src/i18n/locales/ru.json` — sectiunea `upgrade`
8. `src/i18n/locales/fr.json` — sectiunea `upgrade`

## Ce trebuie sa faci

### 1. Redesign complet `src/screens/UpgradeScreen.tsx`

Inlocuieste intregul fisier cu implementare IAP reala.

#### Structura ecranului (de sus in jos):

```
[Header] — "QRChat Unlimited" cu buton back
[Icon] — Rocket icon in cerc colorat
[Title] — "QRChat Unlimited"
[Subtitle] — "You have X contacts..." (doar daca nu e unlimited)
[Features Card] — 4 features cu iconite
[Purchase Button] — PRET REAL din App Store (nu hardcodat!)
  └─ Loading state in timpul achizitiei
  └─ Disabled daca purchasing in progres
[Restore Purchases] — Link text sub buton (OBLIGATORIU APPLE)
[Divider] — "or use a code"
[Promo Code Section] — Collapse/expand cu input
[Free Info] — Text mic la final
[Success State] — Daca deja unlimited: afiseaza checkmark + "Active"
```

#### Cod complet:

```tsx
import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  Alert,
  ActivityIndicator,
  StatusBar,
  ScrollView,
} from 'react-native';
import { useTranslation } from 'react-i18next';
import { useTheme } from '../utils/ThemeContext';
import LicensingService from '../services/LicensingService';
import IAPService from '../services/IAPService';
import Icon from 'react-native-vector-icons/Ionicons';

interface UpgradeScreenProps {
  navigation: any;
  route?: any;
}

export default function UpgradeScreen({ navigation, route }: UpgradeScreenProps) {
  const { t } = useTranslation();
  const { theme: colors } = useTheme();

  // State
  const [isUnlimited, setIsUnlimited] = useState(false);
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [purchasing, setPurchasing] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [showCodeInput, setShowCodeInput] = useState(false);
  const [price, setPrice] = useState('$2.99'); // fallback

  const contactCount = route?.params?.contactCount ?? 0;

  useEffect(() => {
    checkStatus();
    loadPrice();
  }, []);

  const checkStatus = async () => {
    const unlimited = await LicensingService.isUnlimited();
    setIsUnlimited(unlimited);
  };

  const loadPrice = () => {
    // Preia pretul real din App Store (localizat)
    const localizedPrice = IAPService.getLocalizedPrice();
    if (localizedPrice) setPrice(localizedPrice);
  };

  // ── Purchase Handler ──
  const handlePurchase = async () => {
    if (purchasing) return;
    setPurchasing(true);
    try {
      const result = await IAPService.purchase();
      if (result.success) {
        setIsUnlimited(true);
        Alert.alert(
          t('upgrade.successTitle'),
          t('upgrade.purchaseSuccess'),
          [{ text: 'OK', onPress: () => navigation.goBack() }],
        );
      } else {
        // Nu afisa eroare daca user-ul a anulat
        if (result.error && !result.error.includes('cancel')) {
          Alert.alert(t('upgrade.errorTitle'), result.error);
        }
      }
    } catch (e: any) {
      Alert.alert(t('upgrade.errorTitle'), e.message || t('upgrade.purchaseError'));
    } finally {
      setPurchasing(false);
    }
  };

  // ── Restore Handler ──
  const handleRestore = async () => {
    if (restoring) return;
    setRestoring(true);
    try {
      const result = await IAPService.restorePurchases();
      if (result.restored) {
        setIsUnlimited(true);
        Alert.alert(
          t('upgrade.successTitle'),
          t('upgrade.restoreSuccess'),
          [{ text: 'OK', onPress: () => navigation.goBack() }],
        );
      } else {
        Alert.alert(t('upgrade.restoreTitle'), t('upgrade.restoreNotFound'));
      }
    } catch (e: any) {
      Alert.alert(t('upgrade.errorTitle'), e.message || t('upgrade.restoreError'));
    } finally {
      setRestoring(false);
    }
  };

  // ── Promo Code Handler ── (existent, pastrat)
  const handleRedeemPromo = async () => {
    // ... (pastreaza logica existenta din UpgradeScreen)
  };

  // ── Already Unlimited ──
  if (isUnlimited) {
    return (
      <View style={[styles.container, { backgroundColor: colors.background }]}>
        <StatusBar barStyle={colors.statusBarStyle} />
        {/* Header identic */}
        <ScrollView contentContainerStyle={styles.content}>
          <View style={[styles.iconCircle, { backgroundColor: colors.success + '15' }]}>
            <Icon name="checkmark-circle" size={60} color={colors.success} />
          </View>
          <Text style={[styles.title, { color: colors.text }]}>
            {t('upgrade.unlimitedActive')}
          </Text>
          <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
            {t('upgrade.alreadyUnlimited')}
          </Text>
        </ScrollView>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <StatusBar barStyle={colors.statusBarStyle} />

      {/* Header */}
      <View style={[styles.header, { backgroundColor: colors.headerBg }]}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}
          accessibilityLabel={t('common.back')} accessibilityRole="button">
          <Icon name="arrow-back" size={24} color={colors.primary} />
        </TouchableOpacity>
        <Text style={[styles.headerTitle, { color: colors.text }]}>QRChat Unlimited</Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        {/* Icon */}
        <View style={[styles.iconCircle, { backgroundColor: colors.primary + '15' }]}>
          <Icon name="rocket" size={60} color={colors.primary} />
        </View>

        {/* Title + Subtitle */}
        <Text style={[styles.title, { color: colors.text }]}>
          {t('upgrade.title')}
        </Text>
        <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
          {t('upgrade.subtitle', { count: contactCount, limit: 10 })}
        </Text>

        {/* Features Card */}
        <View style={[styles.featuresCard, { backgroundColor: colors.surface }]}>
          {/* ... (pastreaza features-urile existente) */}
        </View>

        {/* Purchase Button — PRET DIN APP STORE */}
        <TouchableOpacity
          style={[styles.purchaseBtn, {
            backgroundColor: purchasing ? colors.border : colors.primary,
          }]}
          onPress={handlePurchase}
          disabled={purchasing}
          accessibilityLabel={t('upgrade.purchaseAccessibility', { price })}
          accessibilityRole="button"
        >
          {purchasing ? (
            <ActivityIndicator color="#FFF" />
          ) : (
            <>
              <Text style={styles.purchaseBtnText}>{t('upgrade.purchaseBtn')}</Text>
              <Text style={styles.purchasePrice}>{price}</Text>
            </>
          )}
        </TouchableOpacity>

        {/* RESTORE PURCHASES — OBLIGATORIU APPLE */}
        <TouchableOpacity
          onPress={handleRestore}
          disabled={restoring}
          style={styles.restoreBtn}
          accessibilityLabel={t('upgrade.restorePurchases')}
          accessibilityRole="button"
        >
          {restoring ? (
            <ActivityIndicator size="small" color={colors.primary} />
          ) : (
            <Text style={[styles.restoreText, { color: colors.primary }]}>
              {t('upgrade.restorePurchases')}
            </Text>
          )}
        </TouchableOpacity>

        {/* Divider + Promo Code (pastrat ca inainte) */}
        {/* ... */}

        {/* Free Info */}
        <Text style={[styles.freeInfo, { color: colors.textMuted }]}>
          {t('upgrade.freeInfo')}
        </Text>
      </ScrollView>
    </View>
  );
}
```

**IMPORTANT:** Codul de mai sus este un schelet. Pastreaza stilurile existente din UpgradeScreen.tsx si adauga doar elementele noi (restore button, price dinamic, purchase real). Nu rescrie ce functioneaza deja — doar extinde.

### 2. Adauga "Restore Purchases" in SettingsScreen.tsx

In `src/screens/SettingsScreen.tsx`, dupa sectiunea QRCHAT UNLIMITED (linia ~400), adauga:

```tsx
{/* Restore Purchases — vizibil doar daca NU e unlimited */}
{!isUnlimited && (
  <TouchableOpacity
    style={[styles.settingRow, { backgroundColor: C.surface }]}
    onPress={async () => {
      // Refoloseste logica de restore din UpgradeScreen
      // sau naviga la UpgradeScreen
      navigation.navigate('Upgrade', { contactCount });
    }}
    accessibilityLabel={t('upgrade.restorePurchases')}
    accessibilityRole="button"
  >
    <View style={{ flexDirection: 'row', alignItems: 'center', flex: 1 }}>
      <View style={{ width: 32, height: 32, borderRadius: 16, backgroundColor: C.primary + '20', justifyContent: 'center', alignItems: 'center', marginRight: 12 }}>
        <Ionicons name="refresh" size={18} color={C.primary} />
      </View>
      <Text style={[styles.settingLabel, { color: C.text }]}>
        {t('upgrade.restorePurchases')}
      </Text>
    </View>
    <Ionicons name="chevron-forward" size={18} color={C.textMuted} />
  </TouchableOpacity>
)}
```

### 3. Adauga i18n — TOATE 4 limbile

#### `src/i18n/locales/en.json` — sectiunea `upgrade`

Adauga cheile noi (pastreaza cele existente, adauga doar cele lipsa):

```json
{
  "upgrade": {
    "title": "QRChat Unlimited",
    "sectionTitle": "QRCHAT UNLIMITED",
    "unlimitedActive": "QRChat Unlimited",
    "upgradeButton": "Upgrade",
    "subtitle": "You have {{count}} contacts. The free plan allows up to {{limit}}. Upgrade to add unlimited contacts.",
    "featureContacts": "Unlimited contacts",
    "featureSecurity": "Same E2E encryption",
    "featureLifetime": "One-time payment, lifetime access",
    "featureSupport": "Support independent development",
    "purchaseBtn": "Upgrade for",
    "purchaseTitle": "In-App Purchase",
    "purchaseNotReady": "Apple In-App Purchase will be available soon. Use an activation code for now.",
    "purchaseSuccess": "QRChat Unlimited is now active. Enjoy unlimited contacts!",
    "purchaseError": "Purchase could not be completed. Please try again.",
    "purchaseAccessibility": "Purchase QRChat Unlimited for {{price}}",
    "restorePurchases": "Restore Purchases",
    "restoreTitle": "Restore Purchases",
    "restoreSuccess": "Your purchase has been restored! QRChat Unlimited is now active.",
    "restoreNotFound": "No previous purchases found for this Apple ID.",
    "restoreError": "Could not restore purchases. Please try again.",
    "alreadyUnlimited": "You have unlimited contacts. Thank you for your support!",
    "orCode": "or use a code",
    "haveCode": "I have a promo code",
    "enterCode": "Enter your promo code",
    "activate": "Redeem",
    "successTitle": "Redeemed!",
    "successMessage": "QRChat Unlimited is now active. Enjoy unlimited contacts!",
    "errorTitle": "Error",
    "invalidCode": "The promo code is incomplete or incorrect. Please check and try again.",
    "freeInfo": "Free plan: up to 10 contacts. QRChat Unlimited: one-time purchase.",
    "contactLimit": "Contact limit reached",
    "contactLimitDesc": "You have reached the free limit of 10 contacts. Upgrade to QRChat Unlimited to add more."
  }
}
```

#### `src/i18n/locales/ro.json` — sectiunea `upgrade`

```json
{
  "upgrade": {
    "purchaseSuccess": "QRChat Unlimited este acum activ. Bucura-te de contacte nelimitate!",
    "purchaseError": "Achizitia nu a putut fi finalizata. Te rugam sa incerci din nou.",
    "purchaseAccessibility": "Cumpara QRChat Unlimited pentru {{price}}",
    "restorePurchases": "Restaureaza achizitiile",
    "restoreTitle": "Restaureaza achizitiile",
    "restoreSuccess": "Achizitia ta a fost restaurata! QRChat Unlimited este acum activ.",
    "restoreNotFound": "Nu s-au gasit achizitii anterioare pentru acest Apple ID.",
    "restoreError": "Nu s-au putut restaura achizitiile. Te rugam sa incerci din nou.",
    "alreadyUnlimited": "Ai contacte nelimitate. Multumim pentru sustinere!"
  }
}
```

#### `src/i18n/locales/ru.json` — sectiunea `upgrade`

```json
{
  "upgrade": {
    "purchaseSuccess": "QRChat Unlimited теперь активен. Наслаждайтесь неограниченными контактами!",
    "purchaseError": "Не удалось завершить покупку. Пожалуйста, попробуйте снова.",
    "purchaseAccessibility": "Купить QRChat Unlimited за {{price}}",
    "restorePurchases": "Восстановить покупки",
    "restoreTitle": "Восстановить покупки",
    "restoreSuccess": "Ваша покупка восстановлена! QRChat Unlimited теперь активен.",
    "restoreNotFound": "Предыдущие покупки для этого Apple ID не найдены.",
    "restoreError": "Не удалось восстановить покупки. Пожалуйста, попробуйте снова.",
    "alreadyUnlimited": "У вас неограниченные контакты. Спасибо за поддержку!"
  }
}
```

#### `src/i18n/locales/fr.json` — sectiunea `upgrade`

```json
{
  "upgrade": {
    "purchaseSuccess": "QRChat Unlimited est maintenant actif. Profitez de contacts illimites !",
    "purchaseError": "L'achat n'a pas pu etre finalise. Veuillez reessayer.",
    "purchaseAccessibility": "Acheter QRChat Unlimited pour {{price}}",
    "restorePurchases": "Restaurer les achats",
    "restoreTitle": "Restaurer les achats",
    "restoreSuccess": "Votre achat a ete restaure ! QRChat Unlimited est maintenant actif.",
    "restoreNotFound": "Aucun achat precedent trouve pour cet identifiant Apple.",
    "restoreError": "Impossible de restaurer les achats. Veuillez reessayer.",
    "alreadyUnlimited": "Vous avez des contacts illimites. Merci pour votre soutien !"
  }
}
```

**IMPORTANT:** Cheile noi se ADAUGA la cele existente — nu sterge cheile care sunt deja acolo! Mergi la sectiunea `"upgrade"` din fiecare fisier JSON si adauga cheile care lipsesc.

### 4. Stiluri noi de adaugat in StyleSheet

```typescript
// Adauga in styles la sfarsitul fisierului UpgradeScreen.tsx:
restoreBtn: {
  paddingVertical: 12,
  alignItems: 'center',
  marginBottom: 20,
},
restoreText: {
  fontSize: 14,
  fontWeight: '600',
},
successContainer: {
  flex: 1,
  alignItems: 'center',
  justifyContent: 'center',
  padding: 24,
},
```

## Reguli stricte

1. **NU modifica** `IAPService.ts` sau `LicensingService.ts` — e treaba architect-ului
2. **NU modifica** `server/` — e treaba backend-engineer
3. **NU modifica** `ios/` — e treaba release-engineer
4. Pretul din butonul Purchase trebuie sa vina din `IAPService.getLocalizedPrice()` — NICIODATA hardcodat
5. Butonul "Restore Purchases" este OBLIGATORIU — Apple va REJECTA fara el
6. Toate string-urile noi trebuie in TOATE 4 limbile (en, ro, ru, fr)
7. Respecta pattern-ul de teme existent: `colors.background`, `colors.primary`, etc.
8. Toate elementele interactive trebuie sa aiba `accessibilityLabel` si `accessibilityRole`
9. Loading states pe ambele butoane (Purchase + Restore) — nu permite double-tap
10. Nu afisa eroare daca user-ul anuleaza purchase-ul (verifica error code)

## Dependente de alti agenti

- **architect** trebuie sa creeze `IAPService.ts` cu metodele `purchase()`, `restorePurchases()`, `getLocalizedPrice()` INAINTE ca tu sa poti importa si folosi serviciul
- Daca IAPService nu e inca gata, poti folosi placeholder-uri care apeleaza `Alert.alert('Coming soon')`

## Verificare finala

- [ ] UpgradeScreen afiseaza pretul real din App Store
- [ ] Butonul Purchase apeleaza `IAPService.purchase()`
- [ ] Butonul "Restore Purchases" exista si apeleaza `IAPService.restorePurchases()`
- [ ] SettingsScreen are link "Restore Purchases" cand nu e unlimited
- [ ] Daca e deja unlimited, ecranul arata checkmark + "Active"
- [ ] i18n complet in toate 4 limbile (en, ro, ru, fr)
- [ ] Ambele teme (Light + Dark) arata corect
- [ ] Accessibility labels pe toate elementele interactive
- [ ] Loading spinners pe Purchase si Restore buttons
- [ ] Nu sunt TypeScript errors

## Deploy obligatoriu dupa modificari
```bash
# Simulator
xcrun simctl terminate CFBAFE20 com.ruslan.qrchat && xcrun simctl launch CFBAFE20 com.ruslan.qrchat
# Fizic
npx react-native run-ios --udid "00008140-00066CA02229801C"
```
