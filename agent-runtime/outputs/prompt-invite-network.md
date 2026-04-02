# Prompt: network-engineer — Deep Link Handler pentru Invite Links (Faza 2)

## Obiectiv

Implementeaza deep link handling in QRChat astfel incat cand Bob deschide un URL de invite (`https://exciting-success-production-d272.up.railway.app/invite/LINK_ID#secret`), aplicatia:
1. Intercepteaza URL-ul (cold start SAU warm start)
2. Extrage `linkId` si `linkSecret` folosind `parseInviteURL()` din `InviteLinkCrypto.ts`
3. Navigheaza la `InviteAcceptScreen` cu parametrii corecti

**IMPORTANT:** Lucrezi DOAR pe partea JavaScript/TypeScript. NU modifica AppDelegate.swift, Info.plist, AndroidManifest.xml sau orice fisier nativ. Modificarile native se vor face separat.

---

## Context codebase

### App.tsx (structura actuala)
- Locatie: `/Users/ruslanconstantinovici/QRChat/App.tsx`
- Foloseste `NavigationContainer` din `@react-navigation/native`
- Are `ref={navigationRef}` pe NavigationContainer (din NavigationService)
- **NU are** prop `linking` — deep links NU sunt configurate acum
- Initializare: splash → loading → Welcome (user nou) sau Home (user existent)
- Gestioneaza incoming calls via EventBus ('incoming-call')

### NavigationService.ts (existent)
- Locatie: `/Users/ruslanconstantinovici/QRChat/src/services/NavigationService.ts`
```typescript
import { createRef } from 'react';
import { NavigationContainerRef } from '@react-navigation/native';

export const navigationRef = createRef<NavigationContainerRef<any>>();

export function navigate(name: string, params?: any) {
  if (navigationRef.current) {
    (navigationRef.current.navigate as any)(name, params);
  }
}
```

### AppNavigator.tsx (existent)
- Locatie: `/Users/ruslanconstantinovici/QRChat/src/navigation/AppNavigator.tsx`
- Foloseste `createNativeStackNavigator` cu `headerShown: false`
- **RootStackParamList** actual (21 ecrane):
```typescript
export type RootStackParamList = {
  Welcome: undefined;
  Setup: undefined;
  Home: undefined;
  Chat: { contactId: string; contactName: string; isGroup?: boolean };
  Call: { contactId: string; contactName: string; isVideo: boolean; isIncoming: boolean; offer?: any };
  QRGenerate: undefined;
  QRScan: undefined;
  Profile: undefined;
  Contacts: undefined;
  Settings: undefined;
  CreateGroup: undefined;
  GroupInfo: { groupId: string };
  ContactProfile: { contactId: string };
  MediaFiles: { contactId: string };
  PendingApproval: { mode: 'waiting' | 'deciding'; contactName: string; contactId: string; contactFingerprint?: string; request?: any; requestTimestamp: number };
  Upgrade: { contactCount?: number };
  ThemeEditor: { editThemeId: string };
  Terms: undefined;
  Support: undefined;
};
```

### InviteLinkCrypto.ts (creat de security-engineer)
- Locatie: `/Users/ruslanconstantinovici/QRChat/src/crypto/InviteLinkCrypto.ts`
- Functii relevante:
```typescript
// Parseaza URL-ul invite → extrage linkId si linkSecret
export function parseInviteURL(url: string): InviteURLParts | null;
// InviteURLParts = { linkId: string; linkSecret: Uint8Array }

// Verifica daca linkId din URL coincide cu cel derivat din linkSecret
// (validare criptografica — previne URL-uri falsificate)

// Verifica expirare
export function isExpired(expiresAt: string | Date): boolean;
```

### React Navigation versiuni instalate
- `@react-navigation/native` v7.1.31
- `@react-navigation/native-stack` v7.14.2
- `@react-navigation/bottom-tabs` v7.15.2

### Formatul URL
```
https://exciting-success-production-d272.up.railway.app/invite/LINK_ID#base64url(linkSecret)

Exemple:
https://exciting-success-production-d272.up.railway.app/invite/a1b2c3d4e5f6a1b2#KjHgFdSaPoIuYtReWqZxCvBnMlKjHgFdSaPoIuYtReWq
qrchat://invite/a1b2c3d4e5f6a1b2#KjHgFdSaPoIuYtReWqZxCvBnMlKjHgFdSaPoIuYtReWq
```

- `LINK_ID` = 16 hex chars (din path, dupa `/invite/`)
- `linkSecret` = 32 bytes base64url encoded (din fragment, dupa `#`)
- Fragment-ul (`#...`) NU este trimis la server — ramane local

---

## Fisiere de creat/modificat

### 1. CREEAZA: `/Users/ruslanconstantinovici/QRChat/src/hooks/useInviteDeepLink.ts`

Acest hook gestioneaza interceptarea deep links pentru invite-uri. Il foloseste App.tsx.

```typescript
/**
 * useInviteDeepLink — Intercepteaza invite link URLs si navigheaza la InviteAcceptScreen.
 *
 * Gestioneaza:
 * - Cold start: app deschisa din link (getInitialURL)
 * - Warm start: app deja deschisa, link primit (addEventListener)
 * - Validare criptografica: parseInviteURL verifica linkId == HKDF(linkSecret)
 */
import { useEffect, useRef, useCallback } from 'react';
import { Linking, Alert } from 'react-native';
import { parseInviteURL } from '../crypto/InviteLinkCrypto';
import { navigate } from '../services/NavigationService';
import type { InviteURLParts } from '../crypto/InviteLinkCrypto';

// Flag: previne procesarea aceluiasi URL de doua ori (cold start race condition)
let initialURLProcessed = false;

/**
 * Verifica daca un URL este un invite link valid.
 * Accepta ambele scheme: https:// si qrchat://
 */
function isInviteURL(url: string): boolean {
  return (
    url.includes('/invite/') &&
    url.includes('#')
  );
}

/**
 * Proceseaza un invite URL: parseaza, valideaza, navigheaza.
 */
function processInviteURL(url: string): void {
  console.log('[DeepLink] Processing invite URL:', url.replace(/#.*$/, '#[REDACTED]'));

  const parts: InviteURLParts | null = parseInviteURL(url);

  if (!parts) {
    console.warn('[DeepLink] Invalid invite URL — parseInviteURL returned null');
    Alert.alert(
      'Invalid Invite',
      'This invite link is invalid or has been tampered with.',
      [{ text: 'OK' }],
    );
    return;
  }

  console.log('[DeepLink] Parsed invite — linkId:', parts.linkId);

  // Navigheaza la InviteAcceptScreen cu linkId si linkSecret
  // linkSecret este Uint8Array — il transmitem ca base64 string in params
  // (React Navigation nu suporta Uint8Array in params)
  navigate('InviteAccept', {
    linkId: parts.linkId,
    linkSecretBase64: Array.from(parts.linkSecret)
      .map((b) => String.fromCharCode(b))
      .join(''),
    // Alternative: encode as comma-separated numbers for safer transport
    linkSecretArray: Array.from(parts.linkSecret),
  });
}

/**
 * Hook principal — apeleaza-l in App.tsx (ODATA, la root level).
 *
 * @param isReady - true cand NavigationContainer este ready (onReady callback)
 *                  Previne navigarea inainte ca navigator-ul sa fie montat.
 */
export function useInviteDeepLink(isReady: boolean): void {
  const isReadyRef = useRef(isReady);
  const pendingURLRef = useRef<string | null>(null);

  // Actualizeaza ref-ul cand isReady se schimba
  useEffect(() => {
    isReadyRef.current = isReady;

    // Daca avem un URL pending si navigator-ul e acum ready, proceseaza-l
    if (isReady && pendingURLRef.current) {
      const url = pendingURLRef.current;
      pendingURLRef.current = null;
      processInviteURL(url);
    }
  }, [isReady]);

  // Handler pentru URL-uri primite
  const handleURL = useCallback((url: string) => {
    if (!isInviteURL(url)) return;

    if (!isReadyRef.current) {
      // Navigator-ul nu e ready — pune URL-ul in pending
      console.log('[DeepLink] Navigator not ready, queuing URL');
      pendingURLRef.current = url;
      return;
    }

    processInviteURL(url);
  }, []);

  useEffect(() => {
    // ============================
    // COLD START: app deschisa din link
    // ============================
    if (!initialURLProcessed) {
      initialURLProcessed = true;
      Linking.getInitialURL()
        .then((url) => {
          if (url) {
            console.log('[DeepLink] Cold start URL detected');
            handleURL(url);
          }
        })
        .catch((err) => {
          console.error('[DeepLink] getInitialURL error:', err);
        });
    }

    // ============================
    // WARM START: app deja deschisa, link primit
    // ============================
    const subscription = Linking.addEventListener('url', ({ url }) => {
      console.log('[DeepLink] Warm start URL received');
      handleURL(url);
    });

    return () => {
      subscription.remove();
    };
  }, [handleURL]);
}

export default useInviteDeepLink;
```

### 2. MODIFICA: `/Users/ruslanconstantinovici/QRChat/App.tsx`

Adauga hook-ul `useInviteDeepLink` in componenta App. Trebuie:

**a) Adauga import-ul:**
```typescript
import { useInviteDeepLink } from './src/hooks/useInviteDeepLink';
```

Pune-l langa celelalte import-uri de hooks/services.

**b) Adauga state pentru navigation ready:**

In componenta App (functia principala), adauga:
```typescript
const [navReady, setNavReady] = useState(false);
```

**c) Apeleaza hook-ul:**

Dupa declararea state-ului, adauga:
```typescript
useInviteDeepLink(navReady);
```

**d) Adauga `onReady` pe NavigationContainer:**

Gaseste `<NavigationContainer` si adauga prop-ul `onReady`:
```tsx
<NavigationContainer
  ref={navigationRef}
  onReady={() => setNavReady(true)}
>
```

**ATENTIE:** NU modifica nimic altceva in App.tsx. NU sterge cod existent. NU modifica logica de initializare (splash, auth, incoming calls). Adaugi DOAR import-ul, state-ul, hook-ul si `onReady`.

### 3. MODIFICA: `/Users/ruslanconstantinovici/QRChat/src/navigation/AppNavigator.tsx`

Adauga `InviteAccept` la `RootStackParamList`:

```typescript
export type RootStackParamList = {
  // ... toate ecranele existente (NU sterge nimic) ...

  // Invite link screens (Faza 2)
  InviteAccept: {
    linkId: string;
    linkSecretBase64: string;
    linkSecretArray: number[];
  };
  CreateInvite: undefined;
  ShareInvite: {
    linkId: string;
    linkSecretBase64: string;
    linkSecretArray: number[];
    inviteId: string;
    expiresAt: string;
  };
  InviteManagement: undefined;
};
```

Adauga si ecranele in stack navigator (in JSX, dupa ultimul `<Stack.Screen>` existent):

```tsx
<Stack.Screen name="InviteAccept" component={InviteAcceptScreen} />
<Stack.Screen name="CreateInvite" component={CreateInviteScreen} />
<Stack.Screen name="ShareInvite" component={ShareInviteScreen} />
<Stack.Screen name="InviteManagement" component={InviteManagementScreen} />
```

Cu import-urile corespunzatoare:
```typescript
import InviteAcceptScreen from '../screens/InviteAcceptScreen';
import CreateInviteScreen from '../screens/CreateInviteScreen';
import ShareInviteScreen from '../screens/ShareInviteScreen';
import InviteManagementScreen from '../screens/InviteManagementScreen';
```

**NOTA:** Ecranele inca nu exista — frontend-engineer le creeaza in paralel. Adauga import-urile si `Stack.Screen`-urile, iar daca compilarea da eroare (fisier lipsa), creeaza un placeholder minimal:

```typescript
// Placeholder: /Users/ruslanconstantinovici/QRChat/src/screens/InviteAcceptScreen.tsx
import React from 'react';
import { View, Text } from 'react-native';
const InviteAcceptScreen = () => <View><Text>InviteAcceptScreen — placeholder</Text></View>;
export default InviteAcceptScreen;
```

(Creeaza placeholders DOAR daca frontend-engineer nu a terminat inca. Verifica intai daca fisierele exista.)

---

## Testare deep links

### Test cold start (simulator):
```bash
# iOS Simulator
xcrun simctl openurl booted "https://exciting-success-production-d272.up.railway.app/invite/a1b2c3d4e5f6a1b2#dGVzdHNlY3JldDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI"

# Android Emulator
adb shell am start -a android.intent.action.VIEW -d "https://exciting-success-production-d272.up.railway.app/invite/a1b2c3d4e5f6a1b2#dGVzdHNlY3JldDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI"
```

### Test warm start (app deja deschisa):
```bash
# iOS — trimite un URL catre app-ul care ruleaza
xcrun simctl openurl booted "qrchat://invite/a1b2c3d4e5f6a1b2#dGVzdHNlY3JldDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI"
```

### Ce trebuie sa verifici:
1. **Cold start:** App se deschide → navigheaza automat la InviteAcceptScreen cu params corecti
2. **Warm start:** App e deschisa pe HomeScreen → navigheaza la InviteAcceptScreen
3. **URL invalid (fara fragment):** Alert "Invalid Invite" apare, nu crash
4. **URL invalid (linkId gresit):** `parseInviteURL()` returneaza null → Alert
5. **Console logs:** Vezi `[DeepLink]` logs cu linkId (dar linkSecret e REDACTED din loguri)

---

## Reguli stricte

1. **NU modifica** AppDelegate.swift, AppDelegate.mm, Info.plist, AndroidManifest.xml — DOAR JS/TS
2. **NU modifica** NavigationService.ts — foloseste `navigate()` existent
3. **NU modifica** InviteLinkCrypto.ts — doar importa `parseInviteURL`
4. **NU crea** ecrane complete — doar placeholders daca e nevoie (frontend-engineer face ecranele)
5. **NU instala** pachete noi — totul e deja disponibil (`react-native` Linking API built-in)
6. **REDACTEAZA** linkSecret din console.log-uri — nu loga secretul complet
7. **Gestioneaza** cazul cand NavigationContainer nu e ready (cold start race condition)
8. **Pastreaza** logica existenta din App.tsx neatinsa

---

## Scenarii edge-case de gestionat

| Scenariu | Comportament expected |
|----------|----------------------|
| URL fara fragment (#) | `parseInviteURL` → null → Alert "Invalid Invite" |
| URL cu linkId invalid (nu 16 hex) | `parseInviteURL` → null → Alert |
| URL cu linkSecret corupt | `parseInviteURL` → null (linkId mismatch) → Alert |
| Cold start cu URL + user nu e logat | URL se pune in pending → dupa login, se proceseaza |
| Warm start pe ecran de chat | Navigheaza la InviteAcceptScreen (push pe stack) |
| Acelasi URL deschis de 2 ori | Navigheaza de 2 ori (acceptat — user decide) |

---

## Output

Dupa ce ai terminat:

1. Actualizeaza `agent-runtime/state/status.md`:
   ```
   | network-engineer | DONE | Deep link handler implementat (useInviteDeepLink + App.tsx + AppNavigator) | — |
   ```

2. Scrie in `agent-runtime/messages/network-to-frontend.md`:
   ```
   # Mesaj de la network-engineer catre frontend-engineer

   Deep link handler-ul este gata.

   ## Ce am implementat:
   - `src/hooks/useInviteDeepLink.ts` — hook care intercepteaza invite URLs
   - App.tsx — adaugat hook + onReady pe NavigationContainer
   - AppNavigator.tsx — adaugat InviteAccept, CreateInvite, ShareInvite, InviteManagement in RootStackParamList + Stack.Screen

   ## Parametrii pe care InviteAcceptScreen ii primeste:
   ```typescript
   route.params = {
     linkId: string,               // 16 hex chars
     linkSecretBase64: string,      // binary string (legacy)
     linkSecretArray: number[],     // array of bytes — FOLOSESTE ASTA
   }
   ```

   ## Cum reconstruiesti linkSecret din params:
   ```typescript
   const linkSecret = new Uint8Array(route.params.linkSecretArray);
   ```

   ## Navigatie:
   - Deep link → InviteAcceptScreen (automat)
   - CreateInviteScreen → ShareInviteScreen (dupa creare)
   - HomeScreen → InviteManagement (buton nou)
   - HomeScreen → CreateInvite (buton [+] sau Invite)
   ```

---

## Dependente

- **Depinzi de**: security-engineer (InviteLinkCrypto.ts — GATA)
- **Nu depinzi de**: backend-engineer (InviteLinkService.ts — nu e necesar pentru deep links)
- **Te asteapta**: frontend-engineer (ecranele primesc params de la tine)
- **Lucrati in paralel** cu frontend-engineer — tu faci plumbing-ul, el face ecranele
