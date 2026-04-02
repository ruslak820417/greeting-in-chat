# Mesaj de la network-engineer catre frontend-engineer

Deep link handler-ul este gata.

## Ce am implementat:
- `src/hooks/useInviteDeepLink.ts` — hook care intercepteaza invite URLs (cold start + warm start)
- `App.tsx` — adaugat hook `useInviteDeepLink(navReady)` + `onReady` callback pe AppNavigator
- `AppNavigator.tsx` — adaugat InviteAccept, CreateInvite, ShareInvite, InviteManagement in RootStackParamList + Stack.Screen entries + imports

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

## Note:
- Frontend-engineer a creat deja InviteAcceptScreen.tsx, CreateInviteScreen.tsx, ShareInviteScreen.tsx, InviteManagementScreen.tsx — le-am importat direct
- `onReady` prop adaugat pe AppNavigator interface (optional) si pasat la NavigationContainer
- linkSecret este REDACTAT din console.log-uri (securitate)
