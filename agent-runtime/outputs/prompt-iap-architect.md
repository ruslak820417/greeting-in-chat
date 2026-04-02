# Prompt: Architect — Apple IAP Integration Architecture

## Rol
Tu esti **architect** pentru QRChat. Sarcina ta este sa creezi serviciul `IAPService.ts`, tipurile TypeScript asociate, si sa integrezi IAP cu `LicensingService.ts` existent.

## Context proiect
- **Codebase:** `/Users/ruslanconstantinovici/QRChat`
- **Bundle ID:** `com.ruslan.qrchat`
- **Product ID:** `com.ruslan.qrchat.unlimited`
- **Tip produs:** Non-consumable ($2.99, one-time purchase, permanent unlock)
- **Versiune:** 4.1.0, React Native 0.84, TypeScript 5.8
- **Librarie IAP:** `react-native-iap` v14.7 (cu Nitro Modules, necesita si `react-native-nitro-modules`)

## Fisiere de citit OBLIGATORIU inainte de a incepe
1. `src/services/LicensingService.ts` — serviciul actual (promo codes, placeholder IAP)
2. `src/storage/Database.ts` — metode `isUnlimited()` / `setUnlimited()` (linia ~1494-1507)
3. `src/utils/constants.ts` — `API_BASE_URL`
4. `src/screens/UpgradeScreen.tsx` — ecranul curent de upgrade
5. `src/screens/SettingsScreen.tsx` — sectiunea QRCHAT UNLIMITED (linia ~369-400)
6. `src/i18n/locales/en.json` — sectiunea `upgrade` (linia ~447-471)

## Ce trebuie sa faci

### 1. Creaza `src/services/IAPService.ts`

Serviciu singleton care gestioneaza toata interactiunea cu App Store prin `react-native-iap` v14.7.

```typescript
// src/services/IAPService.ts

import {
  initConnection,
  endConnection,
  fetchProducts,
  requestPurchase,
  finishTransaction,
  getAvailablePurchases,
  purchaseUpdatedListener,
  purchaseErrorListener,
  type Product,
  type Purchase,
  type PurchaseError,
} from 'react-native-iap';

const PRODUCT_ID = 'com.ruslan.qrchat.unlimited';

interface IAPState {
  connected: boolean;
  product: Product | null;
  purchasing: boolean;
  restoring: boolean;
  error: string | null;
}

class IAPService {
  private state: IAPState = {
    connected: false,
    product: null,
    purchasing: false,
    restoring: false,
    error: null,
  };
  private purchaseUpdateSubscription: any = null;
  private purchaseErrorSubscription: any = null;

  /**
   * Initializeaza conexiunea cu App Store.
   * Apeleaza la pornirea app-ului (App.tsx useEffect).
   */
  async initialize(): Promise<void> {
    // 1. initConnection()
    // 2. Seteaza purchaseUpdatedListener — cand o achizitie se finalizeaza:
    //    a. Trimite receipt la server POST /validate-receipt
    //    b. Daca valid → Database.setUnlimited(true)
    //    c. Apeleaza finishTransaction({ purchase, isConsumable: false })
    // 3. Seteaza purchaseErrorListener
    // 4. Fetch product info: fetchProducts({ skus: [PRODUCT_ID], type: 'in-app' })
  }

  /**
   * Returneaza informatiile despre produs (pret, titlu, etc).
   * Pretul vine din App Store (localizat automat).
   */
  getProduct(): Product | null {
    return this.state.product;
  }

  /**
   * Returneaza pretul localizat (ex: "$2.99", "2,99 €").
   * Foloseste product.localizedPrice din App Store.
   */
  getLocalizedPrice(): string {
    return this.state.product?.localizedPrice ?? '$2.99';
  }

  /**
   * Initiaza cumpararea produsului.
   * Returneaza Promise care se rezolva cand tranzactia e completa.
   */
  async purchase(): Promise<{ success: boolean; error?: string }> {
    // 1. Verifica daca e deja unlimited → return success
    // 2. Verifica daca product e incarcat
    // 3. requestPurchase({
    //      request: { apple: { sku: PRODUCT_ID } },
    //      type: 'in-app',
    //    })
    // 4. Rezultatul vine prin purchaseUpdatedListener
  }

  /**
   * Restaureaza achizitiile anterioare.
   * Apple CERE ca fiecare app cu IAP sa aiba aceasta functionalitate.
   */
  async restorePurchases(): Promise<{ success: boolean; restored: boolean }> {
    // 1. getAvailablePurchases()
    // 2. Cauta PRODUCT_ID in lista
    // 3. Daca gasit → Database.setUnlimited(true) + notifica server
    // 4. Returneaza { success: true, restored: true/false }
  }

  /**
   * Verifica receipt-ul pe server (POST /validate-receipt).
   * Server-ul valideaza cu Apple si returneaza statusul.
   */
  private async validateReceipt(purchase: Purchase): Promise<boolean> {
    // POST la API_BASE_URL + '/validate-receipt'
    // Body: { transactionId, productId, purchaseToken, deviceId }
    // Server face validarea cu Apple
  }

  /**
   * Cleanup la inchiderea app-ului.
   */
  async destroy(): Promise<void> {
    // Remove listeners
    // endConnection()
  }
}

export default new IAPService();
```

### 2. Creaza `src/types/iap.ts`

```typescript
// src/types/iap.ts

export const IAP_PRODUCT_ID = 'com.ruslan.qrchat.unlimited';
export const IAP_PRODUCT_TYPE = 'in-app' as const; // non-consumable

export interface IAPPurchaseResult {
  success: boolean;
  error?: string;
  transactionId?: string;
}

export interface IAPRestoreResult {
  success: boolean;
  restored: boolean;
  error?: string;
}

export interface IAPProductInfo {
  productId: string;
  title: string;
  description: string;
  localizedPrice: string;
  price: number;
  currency: string;
}

export type LicenseSource = 'iap' | 'promo' | 'none';

export interface LicenseStatus {
  isUnlimited: boolean;
  source: LicenseSource;
  transactionId?: string;
  promoCode?: string;
}
```

### 3. Modifica `src/services/LicensingService.ts`

Integreaza IAP cu sistemul de promo codes existent. **Ambele metode coexista.**

Modificari necesare:

#### a. Import IAPService
```typescript
import IAPService from './IAPService';
```

#### b. Modifica metoda `isUnlimited()` — verifica AMBELE surse
```typescript
async isUnlimited(): Promise<boolean> {
  // 1. Verifica local (Database.isUnlimited()) — rapid, offline-first
  // 2. Daca true → return true (nu conteaza sursa)
  // 3. Daca false si online → verifica server (check-license)
  return Database.isUnlimited();
}
```

#### c. Inlocuieste metoda placeholder `activateWithReceipt()`
Sterge actualul placeholder (linia 124-127) si delega la IAPService:
```typescript
async activateWithReceipt(purchase: Purchase): Promise<{ success: boolean; message: string }> {
  // Delega la IAPService.validateReceipt() intern
  // Seteaza Database.setUnlimited(true) daca valid
}
```

#### d. Adauga metoda `getLicenseSource()`
```typescript
async getLicenseSource(): Promise<LicenseSource> {
  // Verifica AsyncStorage '@qrchat_license_source'
  // Returneaza 'iap' | 'promo' | 'none'
}
```

#### e. Adauga metoda `initializeIAP()`
```typescript
async initializeIAP(): Promise<void> {
  await IAPService.initialize();
}
```

### 4. Modifica `App.tsx` — initializeaza IAP la pornire

Adauga in `useEffect` de initializare (care ruleaza o singura data):
```typescript
// Dupa initializarea existenta (Database, MessagingService, etc.)
LicensingService.initializeIAP();
```

Si in cleanup:
```typescript
return () => {
  IAPService.destroy();
};
```

## Reguli stricte

1. **NU modifica** UpgradeScreen.tsx sau SettingsScreen.tsx — e treaba frontend-engineer
2. **NU modifica** server/licensing.js — e treaba backend-engineer
3. **NU modifica** ios/ project files — e treaba release-engineer
4. IAPService trebuie sa fie **singleton** (export default new IAPService())
5. Toate erorile trebuie catch-uite — app-ul nu trebuie sa crasheze niciodata din cauza IAP
6. Offline-first: daca nu e internet, foloseste valoarea din Database.isUnlimited()
7. `finishTransaction()` trebuie apelat INTOTDEAUNA dupa purchase — altfel Apple va rejecta
8. Foloseste `console.warn('[IAP] ...')` pentru logging (nu console.log)

## Dependente de alti agenti

- **backend-engineer** trebuie sa creeze endpoint-ul `POST /validate-receipt` pe server INAINTE ca IAPService sa poata valida receipts
- **release-engineer** trebuie sa adauge StoreKit capability in Xcode INAINTE ca initConnection() sa functioneze
- **frontend-engineer** va consuma IAPService din UpgradeScreen — coordoneaza-te prin tipuri clare

## Verificare finala

Dupa implementare, verifica:
- [ ] `IAPService.ts` exista si exporta singleton
- [ ] `src/types/iap.ts` exista cu toate tipurile
- [ ] `LicensingService.ts` importa si integreaza IAPService
- [ ] `App.tsx` apeleaza `initializeIAP()` in useEffect
- [ ] Nu sunt TypeScript errors noi (`npx tsc --noEmit`)
- [ ] Build pe simulator reuseste (`npx react-native run-ios --simulator "iPhone 16e"`)

## Deploy obligatoriu dupa modificari
```bash
# Simulator
xcrun simctl terminate CFBAFE20 com.ruslan.qrchat && xcrun simctl launch CFBAFE20 com.ruslan.qrchat
# Fizic
npx react-native run-ios --udid "00008140-00066CA02229801C"
```
