# FIX: Cerere TOATE permisiunile la prima pornire (SetupScreen)

## PROBLEMA

Acum permisiunile se cer pe parcurs — notificari la initialize, microfon la primul apel, contacte la PhoneContactsScreen, camera la video call. Apple penalizeaza acest pattern — utilizatorul e bombardat cu popup-uri in momente nepotrivite, si poate refuza. Mai bine cerem totul o singura data, la setup, cu explicatii clare.

## CE TREBUIE FACUT

### Modificare SINGURA: `src/screens/SetupScreen.tsx`

Dupa ce utilizatorul isi seteaza numele si apasa "Continue/Start", INAINTE de generarea cheilor, adauga un pas nou de permisiuni.

**Flow nou:**
```
Pas 1: Nume + limba + tema (existent, neatins)
Pas 2: PERMISIUNI (NOU) — explica si cere toate permisiunile
Pas 3: Generare chei (existent, neatins)
```

### Pasul 2 — Ecran de permisiuni

Afiseaza o lista cu toggle-uri/butoane:

```
┌─────────────────────────────────────┐
│                                     │
│   QRChat needs your permission      │
│                                     │
│   🔔 Notifications                  │
│   For messages and call alerts      │
│   [Allow]                    ✅/❌  │
│                                     │
│   🎤 Microphone                     │
│   For voice and video calls         │
│   [Allow]                    ✅/❌  │
│                                     │
│   📷 Camera                         │
│   For video calls and QR scanning   │
│   [Allow]                    ✅/❌  │
│                                     │
│   📱 Contacts (optional)            │
│   To find friends who use QRChat    │
│   [Allow]                    ✅/❌  │
│                                     │
│        [Continue →]                 │
│                                     │
└─────────────────────────────────────┘
```

### Implementare tehnica:

In `SetupScreen.tsx`, adauga step `'permissions'` in state:
```typescript
const [step, setStep] = useState<'name' | 'permissions' | 'generating' | 'done'>('name');
```

Cand user-ul apasa "Continue" dupa nume, in loc de a genera cheile direct, trece la `setStep('permissions')`.

Pe ecranul de permisiuni, la apasarea fiecarui "Allow":

```typescript
// Notifications
import notifee from '@notifee/react-native';
const notifResult = await notifee.requestPermission();

// Microphone — iOS cere permisiunea cand apelezi getUserMedia
// Forteaza cererea acum:
import { mediaDevices } from '@livekit/react-native-webrtc';
try {
  const stream = await mediaDevices.getUserMedia({ audio: true });
  stream.getTracks().forEach(t => t.stop()); // opreste imediat
} catch (e) {} // user a refuzat — ok

// Camera
try {
  const stream = await mediaDevices.getUserMedia({ video: true });
  stream.getTracks().forEach(t => t.stop());
} catch (e) {}

// Contacts
import Contacts from 'react-native-contacts';
await Contacts.requestPermission();
```

Butonul "Continue" e mereu activ — permisiunile sunt optionale. User-ul poate refuza orice.

Dupa "Continue" → `setStep('generating')` → genereaza chei (cod existent).

### CE NU TREBUIE ATINS

- `handleSetup()` — nu modifica logica de generare chei/profil
- `App.tsx` — nu modifica
- `MessagingService.ts` — lasa `requestPermission()` la initialize (backup daca user-ul sare setup-ul)
- `NotificationService.ts` — nu modifica
- Orice fisier din `src/crypto/`, `src/storage/`, `server/`

### i18n

Adauga stringuri noi in `src/i18n/locales/en.json`, `ro.json`, `ru.json`, `fr.json`:
```json
{
  "setup": {
    "permissionsTitle": "QRChat needs your permission",
    "notificationsDesc": "For messages and call alerts",
    "microphoneDesc": "For voice and video calls",
    "cameraDesc": "For video calls and QR scanning",
    "contactsDesc": "To find friends who use QRChat",
    "contactsOptional": "(optional)",
    "allow": "Allow",
    "allowed": "Allowed",
    "denied": "Denied"
  }
}
```

### VERIFICARE

1. `npx tsc --noEmit` — zero erori
2. Build pe simulator
3. Prima deschidere → Setup → dupa nume, apare ecranul de permisiuni
4. Apasa Allow pe fiecare — popup-ul iOS apare
5. Continue → generare chei → app functional
6. A doua deschidere — NU mai cere permisiuni (sunt deja acordate)
7. Mesaje functioneaza, calls functioneaza, camera functioneaza

### COMMIT

```
git add src/screens/SetupScreen.tsx src/i18n/locales/*.json
git commit -m "Request all permissions at first launch during setup"
```
