# Prompt: frontend-engineer — Invite Link Screens (Faza 2)

## Obiectiv

Creeaza 4 ecrane noi pentru sistemul de invite links + i18n in 4 limbi + integrare in navigatie. Ecranele permit utilizatorilor sa creeze, partajeze, accepte si gestioneze invite links.

---

## Context codebase

### Pattern ecrane existente
Toate ecranele QRChat urmeaza acest pattern:
```typescript
import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, StatusBar, ScrollView } from 'react-native';
import { useTranslation } from 'react-i18next';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Ionicons from 'react-native-vector-icons/Ionicons';
import { useTheme, GradientBackground } from '../utils/ThemeContext';
import Database from '../storage/Database';
import type { UserProfile } from '../utils/types';

const ScreenName = ({ navigation, route }: any) => {
  const { theme: C } = useTheme();
  const { t } = useTranslation();
  const insets = useSafeAreaInsets();

  return (
    <View style={[styles.container, { backgroundColor: C.background }]}>
      <GradientBackground style={StyleSheet.absoluteFill}><View /></GradientBackground>
      <StatusBar barStyle={C.statusBarStyle as any} />
      {/* Header */}
      <View style={[styles.header, { paddingTop: insets.top + 10 }]}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Ionicons name="chevron-back" size={28} color={C.accent} />
        </TouchableOpacity>
        <Text style={[styles.title, { color: C.text }]}>{t('screen.title')}</Text>
        <View style={{ width: 28 }} />
      </View>
      {/* Content */}
    </View>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingBottom: 10,
  },
  title: { fontSize: 18, fontWeight: '700' },
});

export default ScreenName;
```

### Teme (ThemeColors) — acceseaza cu `const { theme: C } = useTheme()`
```
C.primary       — accent color (#FF6B00 light / #00A884 dark)
C.primaryLight  — lighter variant
C.background    — main background (#F2F2F7 light / #000000 dark)
C.surface       — card background (#FFFFFF light / #1C1C1E dark)
C.text          — main text (#1C1C1E light / #FFFFFF dark)
C.textSecondary — secondary text
C.textMuted     — muted/gray text
C.success       — green for success states
C.error         — red for errors
C.warning       — orange/yellow for warnings
C.border        — border color
C.accent        — accent (same as primary)
C.inputBg       — input background
C.gradient      — gradient colors array
C.statusBarStyle — 'light-content' | 'dark-content'
```

### i18n — locales la `src/i18n/locales/{en,ro,ru,fr}.json`
Folosire: `const { t } = useTranslation();` → `t('invite.createTitle')`
Cheile noi se adauga in TOATE cele 4 fisiere JSON.

### QR Code library
- `react-native-qrcode-svg` v6.3.21
- Pattern din QRGenerateScreen:
```tsx
import QRCode from 'react-native-qrcode-svg';
<QRCode value={qrData} size={240} backgroundColor="white" color="black" ecl="H" quietZone={10} />
```

### Share API (nativ React Native)
```typescript
import { Share, Platform } from 'react-native';
await Share.share(
  Platform.OS === 'ios'
    ? { url: fileUri }  // pentru imagine
    : { message: linkText }  // pentru text
);
// SAU simplu text share (ambele platforme):
await Share.share({ message: linkText });
```

### Clipboard
```typescript
import Clipboard from '@react-native-clipboard/clipboard';
Clipboard.setString(text);
```

### Haptic feedback
```typescript
import ReactNativeHapticFeedback from 'react-native-haptic-feedback';
ReactNativeHapticFeedback.trigger('impactLight');
```

### InviteLinkCrypto.ts (creat de security-engineer)
Locatie: `/Users/ruslanconstantinovici/QRChat/src/crypto/InviteLinkCrypto.ts`
```typescript
// Functii de care ai nevoie:
import {
  generateLinkSecret,       // () => Uint8Array (32 bytes)
  deriveLinkId,             // (linkSecret) => string (16 hex chars)
  encryptInvitePayload,     // (payload, linkSecret) => EncryptedInvite
  decryptInvitePayload,     // ({ciphertext, nonce, signature}, linkSecret) => InvitePayload | null
  createMyPayload,          // (displayName, fingerprint) => InvitePayload
  buildInviteURL,           // (linkId, linkSecret) => string (full URL)
  parseInviteURL,           // (url) => InviteURLParts | null
  getExpiresAt,             // (ttl: TTLOption) => Date
  isExpired,                // (expiresAt) => boolean
  getRemainingTime,         // (expiresAt) => { minutes, seconds, display } | null
} from '../crypto/InviteLinkCrypto';

import type {
  InvitePayload,    // { pub, signPub, name, fp }
  EncryptedInvite,  // { linkId, ciphertext, nonce, signature }
  TTLOption,        // '30m' | '1h' | '24h'
} from '../crypto/InviteLinkCrypto';
```

### InviteLinkService.ts (creat de backend-engineer)
Locatie: `/Users/ruslanconstantinovici/QRChat/src/services/InviteLinkService.ts`

**NOTA:** Acest fisier este in curs de creare de catre backend-engineer. Daca NU exista inca cand incepi, creeaza import-urile si presupune ca va avea aceste functii. Verifica daca fisierul exista inainte de a incepe.

```typescript
import {
  createInvite,          // (params) => Promise<CreateInviteResponse>
  validateInvite,        // (linkId) => Promise<ValidateInviteResponse>
  acceptInvite,          // (params) => Promise<AcceptInviteResponse>
  confirmInvite,         // (linkId) => Promise<ConfirmInviteResponse>
  revokeInvite,          // (linkId) => Promise<void>
  subscribeToInvite,     // (inviteId, onUpdate) => () => void (cleanup)
} from '../services/InviteLinkService';

// Tipuri:
// CreateInviteParams = { link_id, creator_encrypted_payload, creator_nonce, creator_signature, creator_display_name?, ttl_option }
// CreateInviteResponse = { invite: { id, link_id, status, ttl_option, created_at, expires_at } }
// ValidateInviteResponse = { valid, creator_display_name?, remaining_minutes?, invite_id?, reason? }
// AcceptInviteResponse = { success, creator: { encrypted_payload, nonce, signature, display_name? } }
// ConfirmInviteResponse = { success, acceptor: { encrypted_payload, nonce, signature, display_name? } }
```

### Navigatie params (de la network-engineer)
```typescript
// AppNavigator.tsx — RootStackParamList (ecranele noi):
InviteAccept: {
  linkId: string;
  linkSecretBase64: string;
  linkSecretArray: number[];   // ← FOLOSESTE ASTA pentru a reconstrui linkSecret
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
```

Reconstruieste linkSecret din params:
```typescript
const linkSecret = new Uint8Array(route.params.linkSecretArray);
```

### Database API existent
```typescript
import Database from '../storage/Database';
const profile = await Database.getProfile();  // UserProfile | null
const contacts = await Database.getContacts(); // Contact[]
await Database.addContact(contact);           // void
```

---

## Ecranele de creat (4)

---

### Ecran 1: CreateInviteScreen

**Fisier:** `/Users/ruslanconstantinovici/QRChat/src/screens/CreateInviteScreen.tsx`

**Scop:** Alice alege TTL-ul si creeaza un invite link.

**Layout:**
```
[< Back]          Create Invite

  Link expires after:
  [30m] [1h] [24h]        ← pill selector, default "1h" selectat

  ┌─────────────────────────────────┐
  │ End-to-end encrypted            │
  │ Only you and the recipient can  │  ← info banner, subtle
  │ read messages.                  │
  └─────────────────────────────────┘

  ╔═════════════════════════════════╗
  ║        Create Link              ║  ← primary CTA, full width
  ╚═════════════════════════════════╝
```

**Logica:**
```typescript
const handleCreate = async () => {
  setLoading(true);
  try {
    const profile = await Database.getProfile();
    if (!profile) throw new Error('Profile not found');

    // 1. Genereaza linkSecret
    const linkSecret = generateLinkSecret();
    const linkId = deriveLinkId(linkSecret);

    // 2. Creeaza payload cu cheile mele
    const payload = createMyPayload(profile.displayName, profile.fingerprint);

    // 3. Cripteaza payload
    const encrypted = encryptInvitePayload(payload, linkSecret);

    // 4. Trimite la server
    const response = await createInvite({
      link_id: encrypted.linkId,
      creator_encrypted_payload: encrypted.ciphertext,
      creator_nonce: encrypted.nonce,
      creator_signature: encrypted.signature,
      creator_display_name: profile.displayName,
      ttl_option: selectedTTL,
    });

    // 5. Navigheaza la ShareInviteScreen
    navigation.replace('ShareInvite', {
      linkId: linkId,
      linkSecretBase64: '', // legacy
      linkSecretArray: Array.from(linkSecret),
      inviteId: response.invite.id,
      expiresAt: response.invite.expires_at,
    });
  } catch (error) {
    Alert.alert(t('common.error'), error.message);
  } finally {
    setLoading(false);
  }
};
```

**TTL Pill Selector:**
- 3 butoane: "30m", "1h", "24h"
- Default selectat: "1h"
- Stil: buton selectat = background `C.primary` + text alb; butoane neselectate = background `C.surface` + text `C.textSecondary`

**Buton Create Link:**
- Plin, background `C.primary`, text alb, bold
- Cand loading → `ActivityIndicator` in loc de text
- Disabled cand loading

---

### Ecran 2: ShareInviteScreen

**Fisier:** `/Users/ruslanconstantinovici/QRChat/src/screens/ShareInviteScreen.tsx`

**Scop:** Alice vede QR-ul + link-ul si il partajeaza. Include countdown timer si Realtime subscription.

**Layout:**
```
[< Back]          Share Link

      ┌───────────┐
      │  QR CODE  │      ← 200x200, generat din URL complet
      │           │
      └───────────┘

  exciting-success-...   ← URL truncat, monospace, tappable
  Tap to copy

  Expires in 59m 45s     ← countdown, updates every second

  ┌─────────┐  ┌──────────┐
  │  Copy   │  │  Share   │    ← doua butoane egale
  └─────────┘  └──────────┘

  Waiting for someone     ← status text + ActivityIndicator
  to accept...

  ── Status: Pending ──   ← badge cu dot galben
```

**Logica:**
```typescript
// Construieste URL-ul complet
const linkSecret = new Uint8Array(route.params.linkSecretArray);
const inviteURL = buildInviteURL(route.params.linkId, linkSecret);

// QR Code: afiseaza URL-ul complet (inclusiv fragment)
<QRCode value={inviteURL} size={200} backgroundColor="white" color="black" ecl="H" quietZone={10} />

// Countdown timer
const [remaining, setRemaining] = useState(getRemainingTime(route.params.expiresAt));
useEffect(() => {
  const interval = setInterval(() => {
    const r = getRemainingTime(route.params.expiresAt);
    setRemaining(r);
    if (!r) clearInterval(interval); // Expired
  }, 1000);
  return () => clearInterval(interval);
}, []);

// Realtime subscription — Alice asteapta sa fie acceptat
useEffect(() => {
  const unsubscribe = subscribeToInvite(route.params.inviteId, (update) => {
    if (update.status === 'accepted') {
      // Bob a acceptat! Decripteaza payload-ul lui
      const acceptorPayload = decryptInvitePayload(
        {
          ciphertext: update.acceptor_encrypted_payload!,
          nonce: update.acceptor_nonce!,
          signature: update.acceptor_signature!,
        },
        linkSecret,
      );
      if (acceptorPayload) {
        // Navigheaza la ecran de confirmare sau adauga contact direct
        handleAcceptorFound(acceptorPayload, update.acceptor_display_name);
      }
    }
  });
  return unsubscribe;
}, []);

// Copy handler
const handleCopy = () => {
  Clipboard.setString(inviteURL);
  setCopied(true);
  ReactNativeHapticFeedback.trigger('impactLight');
  setTimeout(() => setCopied(false), 2000);
};

// Share handler
const handleShare = async () => {
  await Share.share({ message: inviteURL });
};
```

**Copy buton:** Text se schimba "Copy" → "Copied!" cu checkmark, revine dupa 2s.

**QR Code:** Foloseste `react-native-qrcode-svg` exact ca in QRGenerateScreen.

**Countdown:**
- \> 1h: verde, format "Xh Xm"
- 10m-60m: portocaliu, format "Xm Xs"
- < 10m: rosu, pulsare, format "Xm Xs"
- Expirat: text gri "Expired", buton "Create New"

---

### Ecran 3: InviteAcceptScreen

**Fisier:** `/Users/ruslanconstantinovici/QRChat/src/screens/InviteAcceptScreen.tsx`

**Scop:** Bob vede invitatia (cine l-a invitat) si accepta sau declina. Este ecranul care se deschide din deep link.

**Layout:**
```
      ┌─────────┐
      │  Alice   │      ← avatar placeholder (litera + culoare)
      │    A     │
      └─────────┘

      Alice               ← display name, mare, bold

  wants to connect        ← subtitle
  with you

  ┌─────────────────────┐
  │ End-to-end encrypted │  ← security badge, verde
  │ Messages are secured │
  │ with TweetNaCl       │
  └─────────────────────┘

  Expires in 45m          ← countdown

  ╔═════════════════════╗
  ║      Accept         ║  ← primary CTA verde/accent
  ╚═════════════════════╝

  ┌─────────────────────┐
  │      Decline        │  ← secondary, text-only
  └─────────────────────┘
```

**Logica (3 faze):**

**Faza A — Loading:** Valideaza link-ul pe server
```typescript
const [phase, setPhase] = useState<'loading' | 'valid' | 'error'>('loading');
const [creatorName, setCreatorName] = useState('');
const [remainingMin, setRemainingMin] = useState(0);

useEffect(() => {
  (async () => {
    try {
      const result = await validateInvite(route.params.linkId);
      if (result.valid) {
        setCreatorName(result.creator_display_name || t('invite.unknownUser'));
        setRemainingMin(result.remaining_minutes || 0);
        setPhase('valid');
      } else {
        setErrorReason(result.reason || 'unknown');
        setPhase('error');
      }
    } catch (err) {
      setErrorReason('network');
      setPhase('error');
    }
  })();
}, []);
```

**Faza B — Accept:** Bob trimite cheile lui criptate
```typescript
const handleAccept = async () => {
  setAccepting(true);
  try {
    const profile = await Database.getProfile();
    if (!profile) throw new Error('Profile not found');

    const linkSecret = new Uint8Array(route.params.linkSecretArray);

    // 1. Creeaza payload-ul lui Bob
    const myPayload = createMyPayload(profile.displayName, profile.fingerprint);

    // 2. Cripteaza cu acelasi linkSecret (Bob stie secretul din URL fragment)
    const encrypted = encryptInvitePayload(myPayload, linkSecret);

    // 3. Trimite la server si primeste payload-ul Alicei (criptat)
    const response = await acceptInvite({
      link_id: route.params.linkId,
      acceptor_encrypted_payload: encrypted.ciphertext,
      acceptor_nonce: encrypted.nonce,
      acceptor_signature: encrypted.signature,
      acceptor_display_name: profile.displayName,
    });

    // 4. Decripteaza payload-ul Alicei
    const creatorPayload = decryptInvitePayload(
      {
        ciphertext: response.creator.encrypted_payload,
        nonce: response.creator.nonce,
        signature: response.creator.signature,
      },
      linkSecret,
    );

    if (!creatorPayload) {
      Alert.alert(t('common.error'), t('invite.decryptionFailed'));
      return;
    }

    // 5. Adauga Alice ca contact
    const contactId = creatorPayload.fp.replace(/-/g, '').substring(0, 16);
    await Database.addContact({
      id: contactId,
      displayName: creatorPayload.name,
      publicKey: creatorPayload.pub,
      fingerprint: creatorPayload.fp,
      addedAt: Date.now(),
      lastSeen: Date.now(),
      isVerified: false,  // invite link, nu QR scan
      isOnline: false,
      avatarColor: getRandomAvatarColor(),
    });

    // 6. Navigheaza la chat
    navigation.reset({
      index: 1,
      routes: [
        { name: 'Home' },
        { name: 'Chat', params: { contactId, contactName: creatorPayload.name } },
      ],
    });
  } catch (error) {
    Alert.alert(t('common.error'), error.message);
  } finally {
    setAccepting(false);
  }
};
```

**Faza C — Error states:** Diferite ecrane in functie de `errorReason`:
- `'expired'` → icon ceas, "This invite has expired", sugestie "Ask the sender for a new link"
- `'revoked'` → icon bloc, "Invite withdrawn"
- `'accepted'` → icon check, "Link already used"
- `'not_found'` → icon semnul intrebarii, "Invalid invite link"
- `'network'` → icon antena, "Connection problem", buton "Try Again"

**Avatar placeholder:** Cerc 80pt, culoare generata din hash-ul numelui, litera mare a numelui in centru.

---

### Ecran 4: InviteManagementScreen

**Fisier:** `/Users/ruslanconstantinovici/QRChat/src/screens/InviteManagementScreen.tsx`

**Scop:** Alice vede lista tuturor invite links create (active, expirate, revocate).

**Layout:**
```
[< Back]       Invite Links

  Active (2)                ← section header

  ┌─────────────────────┐
  │ For Maria            │
  │ Created Mar 24 14:30 │
  │ Expires in 22h 15m   │  ← countdown
  │ Status: Pending      │  ← dot galben
  └─────────────────────┘

  ┌─────────────────────┐
  │ Conference Link      │
  │ Created Mar 24 09:00 │
  │ Expires in 5m 30s    │  ← countdown rosu, pulsare
  │ Status: Pending      │
  └─────────────────────┘

  Past (3)                  ← section header, collapsed

  ╔═════════════════════╗
  ║  + Create New Link  ║   ← buton la fund
  ╚═════════════════════╝
```

**Logica:**

**NOTA IMPORTANTA:** Deoarece serverul este zero-knowledge (nu stocheaza date in plaintext accesibil clientului fara linkSecret), InviteManagementScreen trebuie sa stocheze local datele invite-urilor create. Creeaza un storage local:

```typescript
import AsyncStorage from '@react-native-async-storage/async-storage';

interface LocalInvite {
  inviteId: string;        // UUID from server
  linkId: string;          // 16 hex chars
  linkSecretArray: number[]; // for reconstructing Uint8Array
  displayName: string;     // creator's name (self)
  ttlOption: TTLOption;
  createdAt: string;       // ISO string
  expiresAt: string;       // ISO string
  status: 'pending' | 'accepted' | 'expired' | 'revoked';
  acceptorName?: string;   // filled when accepted
}

const STORAGE_KEY = '@qrchat_invites';

async function loadLocalInvites(): Promise<LocalInvite[]> {
  const raw = await AsyncStorage.getItem(STORAGE_KEY);
  return raw ? JSON.parse(raw) : [];
}

async function saveLocalInvite(invite: LocalInvite): Promise<void> {
  const invites = await loadLocalInvites();
  invites.unshift(invite);
  await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(invites));
}

async function updateLocalInvite(inviteId: string, update: Partial<LocalInvite>): Promise<void> {
  const invites = await loadLocalInvites();
  const idx = invites.findIndex(i => i.inviteId === inviteId);
  if (idx !== -1) {
    invites[idx] = { ...invites[idx], ...update };
    await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(invites));
  }
}
```

**IMPORTANT:** `saveLocalInvite` trebuie apelat in `CreateInviteScreen.handleCreate()` DUPA ce primesti raspunsul de la server. Adauga:
```typescript
await saveLocalInvite({
  inviteId: response.invite.id,
  linkId: linkId,
  linkSecretArray: Array.from(linkSecret),
  displayName: profile.displayName,
  ttlOption: selectedTTL,
  createdAt: response.invite.created_at,
  expiresAt: response.invite.expires_at,
  status: 'pending',
});
```

**Card invite:**
- Status dot: galben (pending), verde (accepted), gri (expired), rosu (revoked)
- Countdown live (every second for active, every minute for > 1h)
- Swipe left: [Revoke] (rosu) — apeleaza `revokeInvite(linkId)`
- Tap pe card: navigheaza la ShareInviteScreen (re-share)

**Sectiuni:**
- "Active" — pending, sorted by expires_at ascending (cel mai aproape de expirare primul)
- "Past" — accepted/expired/revoked, collapsed by default, sorted by created_at descending

**Empty state:** Daca nu sunt invites, afiseaza ilustratie + text "No invite links yet" + buton "Create your first invite link"

---

## Fisiere i18n de modificat

Adauga aceste chei in TOATE cele 4 fisiere:

### `/Users/ruslanconstantinovici/QRChat/src/i18n/locales/en.json`
```json
{
  "invite": {
    "createTitle": "Create Invite",
    "expiresAfter": "Link expires after",
    "ttl30m": "30 min",
    "ttl1h": "1 hour",
    "ttl24h": "24 hours",
    "encryptedBanner": "End-to-end encrypted. Only you and the recipient can read messages.",
    "createButton": "Create Link",
    "creating": "Creating...",

    "shareTitle": "Share Link",
    "tapToCopy": "Tap to copy link",
    "expiresIn": "Expires in {{time}}",
    "expired": "Expired",
    "copy": "Copy",
    "copied": "Copied!",
    "share": "Share",
    "waitingAccept": "Waiting for someone to accept...",
    "statusPending": "Pending",
    "statusAccepted": "Accepted",
    "statusExpired": "Expired",
    "statusRevoked": "Revoked",
    "createNew": "Create New Link",

    "acceptTitle": "Invite",
    "wantsToConnect": "wants to connect with you",
    "securityBadge": "End-to-end encrypted",
    "securityDesc": "Messages are secured with strong encryption",
    "accept": "Accept",
    "decline": "Decline",
    "accepting": "Connecting...",
    "unknownUser": "Someone",
    "decryptionFailed": "Could not verify invite data. The link may be corrupted.",

    "errorExpiredTitle": "Invite Expired",
    "errorExpiredDesc": "This invite link is no longer valid. Ask the sender for a new link.",
    "errorRevokedTitle": "Invite Withdrawn",
    "errorRevokedDesc": "The sender cancelled this invitation.",
    "errorUsedTitle": "Already Used",
    "errorUsedDesc": "This invite link has already been accepted.",
    "errorInvalidTitle": "Invalid Link",
    "errorInvalidDesc": "This doesn't appear to be a valid QRChat invite.",
    "errorNetworkTitle": "Connection Problem",
    "errorNetworkDesc": "Could not verify this invite. Check your internet connection.",
    "tryAgain": "Try Again",
    "openApp": "Open QRChat",

    "managementTitle": "Invite Links",
    "activeSection": "Active",
    "pastSection": "Past",
    "noInvites": "No invite links yet",
    "noInvitesDesc": "Create an invite link to add contacts remotely",
    "createFirst": "Create your first invite link",
    "revoke": "Revoke",
    "reshare": "Share Again",
    "createdAt": "Created {{date}}",
    "acceptedBy": "Accepted by {{name}}",
    "revokeConfirm": "Revoke this invite link?",
    "revokeConfirmDesc": "The link will no longer work for anyone.",
    "cancel": "Cancel"
  }
}
```

### `/Users/ruslanconstantinovici/QRChat/src/i18n/locales/ro.json`
```json
{
  "invite": {
    "createTitle": "Creeaza invitatie",
    "expiresAfter": "Link-ul expira dupa",
    "ttl30m": "30 min",
    "ttl1h": "1 ora",
    "ttl24h": "24 ore",
    "encryptedBanner": "Criptat end-to-end. Doar tu si destinatarul puteti citi mesajele.",
    "createButton": "Creeaza link",
    "creating": "Se creeaza...",

    "shareTitle": "Partajeaza link",
    "tapToCopy": "Apasa pentru a copia",
    "expiresIn": "Expira in {{time}}",
    "expired": "Expirat",
    "copy": "Copiaza",
    "copied": "Copiat!",
    "share": "Partajeaza",
    "waitingAccept": "Se asteapta acceptarea...",
    "statusPending": "In asteptare",
    "statusAccepted": "Acceptat",
    "statusExpired": "Expirat",
    "statusRevoked": "Revocat",
    "createNew": "Creeaza link nou",

    "acceptTitle": "Invitatie",
    "wantsToConnect": "vrea sa se conecteze cu tine",
    "securityBadge": "Criptat end-to-end",
    "securityDesc": "Mesajele sunt securizate cu criptare puternica",
    "accept": "Accepta",
    "decline": "Refuza",
    "accepting": "Se conecteaza...",
    "unknownUser": "Cineva",
    "decryptionFailed": "Nu s-au putut verifica datele invitatiei. Link-ul poate fi corupt.",

    "errorExpiredTitle": "Invitatie expirata",
    "errorExpiredDesc": "Acest link nu mai este valid. Cere expeditorului un link nou.",
    "errorRevokedTitle": "Invitatie retrasa",
    "errorRevokedDesc": "Expeditorul a anulat aceasta invitatie.",
    "errorUsedTitle": "Deja utilizat",
    "errorUsedDesc": "Acest link a fost deja acceptat.",
    "errorInvalidTitle": "Link invalid",
    "errorInvalidDesc": "Acest link nu pare a fi o invitatie QRChat valida.",
    "errorNetworkTitle": "Problema de conexiune",
    "errorNetworkDesc": "Nu s-a putut verifica invitatia. Verifica conexiunea la internet.",
    "tryAgain": "Incearca din nou",
    "openApp": "Deschide QRChat",

    "managementTitle": "Link-uri de invitatie",
    "activeSection": "Active",
    "pastSection": "Trecute",
    "noInvites": "Nicio invitatie inca",
    "noInvitesDesc": "Creeaza un link de invitatie pentru a adauga contacte de la distanta",
    "createFirst": "Creeaza prima ta invitatie",
    "revoke": "Revoca",
    "reshare": "Partajeaza din nou",
    "createdAt": "Creat {{date}}",
    "acceptedBy": "Acceptat de {{name}}",
    "revokeConfirm": "Revoci acest link de invitatie?",
    "revokeConfirmDesc": "Link-ul nu va mai functiona pentru nimeni.",
    "cancel": "Anuleaza"
  }
}
```

### `/Users/ruslanconstantinovici/QRChat/src/i18n/locales/ru.json`
```json
{
  "invite": {
    "createTitle": "Создать приглашение",
    "expiresAfter": "Ссылка истекает через",
    "ttl30m": "30 мин",
    "ttl1h": "1 час",
    "ttl24h": "24 часа",
    "encryptedBanner": "Сквозное шифрование. Только вы и получатель можете читать сообщения.",
    "createButton": "Создать ссылку",
    "creating": "Создание...",

    "shareTitle": "Поделиться ссылкой",
    "tapToCopy": "Нажмите, чтобы скопировать",
    "expiresIn": "Истекает через {{time}}",
    "expired": "Истекло",
    "copy": "Копировать",
    "copied": "Скопировано!",
    "share": "Поделиться",
    "waitingAccept": "Ожидание принятия...",
    "statusPending": "Ожидание",
    "statusAccepted": "Принято",
    "statusExpired": "Истекло",
    "statusRevoked": "Отозвано",
    "createNew": "Создать новую ссылку",

    "acceptTitle": "Приглашение",
    "wantsToConnect": "хочет связаться с вами",
    "securityBadge": "Сквозное шифрование",
    "securityDesc": "Сообщения защищены надёжным шифрованием",
    "accept": "Принять",
    "decline": "Отклонить",
    "accepting": "Подключение...",
    "unknownUser": "Кто-то",
    "decryptionFailed": "Не удалось проверить данные приглашения. Ссылка может быть повреждена.",

    "errorExpiredTitle": "Приглашение истекло",
    "errorExpiredDesc": "Эта ссылка больше не действительна. Попросите отправителя создать новую.",
    "errorRevokedTitle": "Приглашение отозвано",
    "errorRevokedDesc": "Отправитель отменил это приглашение.",
    "errorUsedTitle": "Уже использовано",
    "errorUsedDesc": "Эта ссылка уже была принята.",
    "errorInvalidTitle": "Недействительная ссылка",
    "errorInvalidDesc": "Это не похоже на действительное приглашение QRChat.",
    "errorNetworkTitle": "Проблема с подключением",
    "errorNetworkDesc": "Не удалось проверить приглашение. Проверьте интернет-соединение.",
    "tryAgain": "Попробовать снова",
    "openApp": "Открыть QRChat",

    "managementTitle": "Ссылки-приглашения",
    "activeSection": "Активные",
    "pastSection": "Прошедшие",
    "noInvites": "Приглашений пока нет",
    "noInvitesDesc": "Создайте ссылку-приглашение для добавления контактов удалённо",
    "createFirst": "Создайте первое приглашение",
    "revoke": "Отозвать",
    "reshare": "Поделиться снова",
    "createdAt": "Создано {{date}}",
    "acceptedBy": "Принято {{name}}",
    "revokeConfirm": "Отозвать эту ссылку?",
    "revokeConfirmDesc": "Ссылка перестанет работать для всех.",
    "cancel": "Отмена"
  }
}
```

### `/Users/ruslanconstantinovici/QRChat/src/i18n/locales/fr.json`
```json
{
  "invite": {
    "createTitle": "Creer une invitation",
    "expiresAfter": "Le lien expire apres",
    "ttl30m": "30 min",
    "ttl1h": "1 heure",
    "ttl24h": "24 heures",
    "encryptedBanner": "Chiffrement de bout en bout. Seuls vous et le destinataire pouvez lire les messages.",
    "createButton": "Creer le lien",
    "creating": "Creation...",

    "shareTitle": "Partager le lien",
    "tapToCopy": "Appuyez pour copier",
    "expiresIn": "Expire dans {{time}}",
    "expired": "Expire",
    "copy": "Copier",
    "copied": "Copie !",
    "share": "Partager",
    "waitingAccept": "En attente d'acceptation...",
    "statusPending": "En attente",
    "statusAccepted": "Accepte",
    "statusExpired": "Expire",
    "statusRevoked": "Revoque",
    "createNew": "Creer un nouveau lien",

    "acceptTitle": "Invitation",
    "wantsToConnect": "veut se connecter avec vous",
    "securityBadge": "Chiffrement de bout en bout",
    "securityDesc": "Les messages sont securises par un chiffrement fort",
    "accept": "Accepter",
    "decline": "Refuser",
    "accepting": "Connexion...",
    "unknownUser": "Quelqu'un",
    "decryptionFailed": "Impossible de verifier les donnees d'invitation. Le lien est peut-etre corrompu.",

    "errorExpiredTitle": "Invitation expiree",
    "errorExpiredDesc": "Ce lien n'est plus valide. Demandez a l'expediteur un nouveau lien.",
    "errorRevokedTitle": "Invitation retiree",
    "errorRevokedDesc": "L'expediteur a annule cette invitation.",
    "errorUsedTitle": "Deja utilise",
    "errorUsedDesc": "Ce lien d'invitation a deja ete accepte.",
    "errorInvalidTitle": "Lien invalide",
    "errorInvalidDesc": "Ce lien ne semble pas etre une invitation QRChat valide.",
    "errorNetworkTitle": "Probleme de connexion",
    "errorNetworkDesc": "Impossible de verifier cette invitation. Verifiez votre connexion internet.",
    "tryAgain": "Reessayer",
    "openApp": "Ouvrir QRChat",

    "managementTitle": "Liens d'invitation",
    "activeSection": "Actifs",
    "pastSection": "Passes",
    "noInvites": "Aucune invitation pour le moment",
    "noInvitesDesc": "Creez un lien d'invitation pour ajouter des contacts a distance",
    "createFirst": "Creez votre premiere invitation",
    "revoke": "Revoquer",
    "reshare": "Partager a nouveau",
    "createdAt": "Cree le {{date}}",
    "acceptedBy": "Accepte par {{name}}",
    "revokeConfirm": "Revoquer ce lien d'invitation ?",
    "revokeConfirmDesc": "Le lien ne fonctionnera plus pour personne.",
    "cancel": "Annuler"
  }
}
```

---

## Integrare in navigatie existenta

### Buton in HomeScreen
Adauga un buton "Invite" sau un icon pe HomeScreen care duce la `CreateInviteScreen`:

Cauta in `src/screens/HomeScreen.tsx` zona header-ului (unde sunt butoanele [+], QR, etc). Adauga un buton nou:
```tsx
<TouchableOpacity onPress={() => navigation.navigate('CreateInvite')}>
  <Ionicons name="link-outline" size={24} color={C.accent} />
</TouchableOpacity>
```

SAU adauga in meniul contextual existent (daca exista un "+" menu cu optiuni).

### Buton in SettingsScreen
Adauga un rand "Invite Links" in Settings care duce la `InviteManagementScreen`:
```tsx
<TouchableOpacity onPress={() => navigation.navigate('InviteManagement')}>
  <Text>{t('invite.managementTitle')}</Text>
</TouchableOpacity>
```

---

## Fisiere de creat/modificat

| Fisier | Actiune |
|--------|---------|
| `src/screens/CreateInviteScreen.tsx` | **CREATE** |
| `src/screens/ShareInviteScreen.tsx` | **CREATE** |
| `src/screens/InviteAcceptScreen.tsx` | **CREATE** |
| `src/screens/InviteManagementScreen.tsx` | **CREATE** |
| `src/i18n/locales/en.json` | **MODIFY** — adauga bloc "invite" |
| `src/i18n/locales/ro.json` | **MODIFY** — adauga bloc "invite" |
| `src/i18n/locales/ru.json` | **MODIFY** — adauga bloc "invite" |
| `src/i18n/locales/fr.json` | **MODIFY** — adauga bloc "invite" |
| `src/screens/HomeScreen.tsx` | **MODIFY** — adauga buton Invite |
| `src/screens/SettingsScreen.tsx` | **MODIFY** — adauga link Invite Management |

---

## Reguli stricte

1. **NU modifica** fisiere crypto (`src/crypto/*`) — DOAR importa
2. **NU modifica** `InviteLinkService.ts` sau `SupabaseService.ts` — DOAR importa
3. **NU modifica** `App.tsx` — network-engineer face asta
4. **NU modifica** `AppNavigator.tsx` — network-engineer face asta (DOAR adauga import-uri daca ecranele tale nu sunt inca referentiate)
5. **Foloseste EXACT** pattern-ul ecranelor existente: `useTheme()`, `useTranslation()`, `useSafeAreaInsets()`, `GradientBackground`
6. **i18n OBLIGATORIU** — niciun string hardcodat in ecrane. Totul prin `t('invite.key')`
7. **Toate cele 4 limbi** — en, ro, ru, fr. Nu lasa nicio limba incompleta
8. **NU instala** pachete noi — foloseste ce exista deja in package.json
9. **Haptic feedback** la copy (daca `react-native-haptic-feedback` e in package.json; daca nu, sari peste)
10. **Dupa orice modificare:** deploy pe simulator + telefon fizic

---

## Output

Dupa ce ai terminat:

1. Actualizeaza `agent-runtime/state/status.md`:
   ```
   | frontend-engineer | DONE | 4 ecrane invite + i18n 4 limbi + navigatie | — |
   ```

2. Scrie in `agent-runtime/messages/frontend-to-qa.md`:
   ```
   # Mesaj de la frontend-engineer catre qa-engineer

   Ecranele invite link sunt gata.

   ## Ecrane noi:
   - CreateInviteScreen — selecteaza TTL, creeaza link
   - ShareInviteScreen — QR + link + share + countdown + Realtime
   - InviteAcceptScreen — accept/decline cu error states
   - InviteManagementScreen — lista invite-uri + revoke

   ## Navigatie:
   - HomeScreen → CreateInvite (buton link)
   - CreateInvite → ShareInvite (dupa creare)
   - Deep link → InviteAccept (automat)
   - Settings → InviteManagement
   - InviteManagement → ShareInvite (re-share)
   - InviteManagement → CreateInvite (buton +)

   ## i18n:
   - Bloc "invite" adaugat in en/ro/ru/fr
   - 45+ chei per limba

   ## De testat:
   - Flow complet: Create → Share → Accept → Chat
   - Error states: expired, revoked, used, invalid, network
   - Countdown timer accuracy
   - Copy + Share functionality
   - Realtime: accept notification
   - TTL options: 30m, 1h, 24h
   - Toate cele 4 limbi
   ```

---

## Dependente

- **Depinzi de**: security-engineer (InviteLinkCrypto.ts — GATA), backend-engineer (InviteLinkService.ts — in curs)
- **Depinzi de**: network-engineer (AppNavigator.tsx params, deep link handler — in paralel)
- **Te asteapta**: qa-engineer (teste pe ecrane)
- **Daca InviteLinkService.ts nu exista inca:** Creeaza ecranele cu import-uri si presupune functiile din sectiunea "InviteLinkService.ts" de mai sus. Pune un `// TODO: uncomment when InviteLinkService is ready` cu mock data pentru testare vizuala.
