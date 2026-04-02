# Custom Sounds Architecture — QRChat

## Obiectiv

Permite utilizatorului sa aleaga sunete personalizate (din telefon) pentru apeluri si mesaje, in loc de lista fixa de system sounds. Melodia de apel se reda COMPLET (toata durata), apoi se repeta de la inceput — nu se taie la 3 secunde.

---

## Starea Curenta (Ce Exista)

### Flux actual
1. **SettingsScreen.tsx** — afiseaza lista fixa din `soundOptions.ts` (RINGTONE_OPTIONS / MESSAGE_TONE_OPTIONS)
2. **soundOptions.ts** — array static cu iOS System Sound IDs (1005, 1007, etc.)
3. **NotificationService.ts** — reda sunetul selectat:
   - Message: `SystemSoundModule.playSystemSound(soundId)` — sunet scurt, o data
   - Call: `SystemSoundModule.playAudioFileLoop(path)` pt fisiere custom, sau `playSystemSound` in loop la 3s pt system sounds
4. **SystemSoundModule.swift** (iOS) — `playSystemSound`, `playAudioFileLoop` (AVAudioPlayer cu numberOfLoops=-1), `stopLoop`
5. **SystemSoundModule.kt** (Android) — `playSystemSound` (RingtoneManager), `playAudioFileLoop` (MediaPlayer cu isLooping=true), `stopLoop`
6. **Database** — `contacts` table are `customRingtone TEXT, customMessageTone TEXT`; `settings` are `callRingtone`, `messageTone`

### Problema
- System sounds (AudioServicesPlaySystemSound) sunt scurte (~1-3s) si nu au loop nativ
- Apelul repeta la interval de 3s cu setInterval — sunetul se taie si nu e continuu
- Nu exista picker pentru fisiere audio din telefonul utilizatorului

---

## Arhitectura Noua

### Conventie de stocare

Valorile salvate in `settings.callRingtone`, `settings.messageTone`, `contact.customRingtone`, `contact.customMessageTone`:

| Valoare | Semnificatie |
|---------|-------------|
| `'1005'` | System sound ID (iOS) — comportament existent |
| `'0'` | No sound |
| `'file:custom_ringtone_1679012345.m4a'` | Fisier custom din app storage |

Fisierele custom sunt stocate in `DocumentDirectoryPath/custom-sounds/`.

### Librarii Necesare

| Librarie | Scop | Nota |
|----------|------|------|
| `react-native-document-picker` (v9.x) | Deschide picker nativ pentru fisiere audio | Deja proven, stabil, suporta UTType pe iOS |
| `react-native-fs` (RNFS) | Copiaza fisierul selectat in app storage | Daca nu e deja instalat |

**NU avem nevoie de:** react-native-ringtone-manager, expo-music-picker, react-native-audio-picker. Document picker e suficient si suporta ambele platforme.

---

## Algoritmul Complet

### 1. Picker — Selectare Fisier Audio

```
Utilizatorul apasa "Choose from phone" in lista de sunete
  -> Platform.OS check
  -> iOS: DocumentPicker.pick({ type: ['public.audio'] })
  -> Android: DocumentPicker.pick({ type: ['audio/*'] })
  -> Rezultat: { uri, name, size, type }
```

### 2. Copiere in App Storage

```
Dupa selectare:
  1. Creeaza directorul: RNFS.DocumentDirectoryPath + '/custom-sounds/'
  2. Genereaza filename unic: `custom_${type}_${Date.now()}.${ext}`
     - type = 'ringtone' | 'message'
     - ext = extensia fisierului original (m4a, mp3, wav, etc.)
  3. Copiaza: RNFS.copyFile(uri, destinationPath)
  4. Verifica: RNFS.exists(destinationPath)
  5. Sterge fisierul vechi daca exista (cleanup)
  6. Salveaza in settings/contact: `file:${filename}`
```

### 3. Playback — Mesaj Incoming

```
NotificationService.showMessageNotification():
  soundId = contact.customMessageTone || settings.messageTone || '1007'

  DACA soundId.startsWith('file:'):
    path = DocumentDirectoryPath + '/custom-sounds/' + soundId.substring(5)
    iOS: SystemSoundModule.playAudioFile(path)     // AVAudioPlayer, numberOfLoops=0 (o data)
    Android: SystemSoundModule.playAudioFile(path)  // MediaPlayer, isLooping=false (o data)
  ALTFEL:
    SystemSoundModule.playSystemSound(parseInt(soundId))
```

### 4. Playback — Apel Incoming (Loop Complet)

```
NotificationService.playCallSound():
  soundId = contact.customRingtone || settings.callRingtone || '1005'

  DACA soundId.startsWith('file:'):
    path = DocumentDirectoryPath + '/custom-sounds/' + soundId.substring(5)
    iOS: SystemSoundModule.playAudioFileLoop(path)   // AVAudioPlayer, numberOfLoops=-1
    Android: SystemSoundModule.playAudioFileLoop(path) // MediaPlayer, isLooping=true
    // MELODIA SE REDA COMPLET, APOI SE REPETA!
  ALTFEL:
    // System sound — comportament existent (repeat la 3s)
    SystemSoundModule.playSystemSound(parseInt(soundId))
    setInterval(() => playSystemSound(...), 3000)
```

### 5. Preview in Settings

```
Cand utilizatorul selecteaza un sunet custom, reda 5 secunde ca preview:
  1. playAudioFile(path) — fara loop
  2. setTimeout(5000) -> stopLoop()
  3. Sau: utilizatorul apasa alt sunet -> stopLoop() si reda noul sunet
```

---

## Modificari Native Necesare

### iOS — SystemSoundModule.swift

Adauga metoda noua `playAudioFile` (fara loop, pentru mesaje si preview):

```swift
@objc
func playAudioFile(_ path: String) {
    DispatchQueue.main.async { [weak self] in
        self?.stopLoopInternal()
        let cleanPath = path.replacingOccurrences(of: "file://", with: "")
        let url = URL(fileURLWithPath: cleanPath)
        do {
            try AVAudioSession.sharedInstance().setCategory(.playback, mode: .default, options: [.mixWithOthers])
            try AVAudioSession.sharedInstance().setActive(true)
            let player = try AVAudioPlayer(contentsOf: url)
            player.numberOfLoops = 0  // O SINGURA DATA (nu loop)
            player.play()
            self?.audioPlayer = player
        } catch {
            print("[SystemSoundModule] playAudioFile error: \(error)")
        }
    }
}
```

**Metoda `playAudioFileLoop` existenta** functioneaza corect (numberOfLoops = -1).

Actualizeaza bridge-ul in SystemSoundModule.m:
```objc
RCT_EXTERN_METHOD(playAudioFile:(NSString *)path)
```

### Android — SystemSoundModule.kt

**Modifica `playAudioFileLoop`** sa foloseasca path-ul real in loc de ringtone default:

```kotlin
@ReactMethod
fun playAudioFileLoop(path: String) {
    stopLoop()
    try {
        val cleanPath = path.removePrefix("file://")
        loopPlayer = MediaPlayer().apply {
            setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_NOTIFICATION_RINGTONE)
                    .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                    .build()
            )
            setDataSource(cleanPath)  // FISIERUL REAL, nu default ringtone!
            isLooping = true
            prepare()
            start()
        }
    } catch (e: Exception) {
        loopPlayer = null
    }
}
```

Adauga metoda noua `playAudioFile` (fara loop):

```kotlin
@ReactMethod
fun playAudioFile(path: String) {
    stopLoop()
    try {
        val cleanPath = path.removePrefix("file://")
        loopPlayer = MediaPlayer().apply {
            setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_NOTIFICATION)
                    .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                    .build()
            )
            setDataSource(cleanPath)
            isLooping = false
            prepare()
            start()
        }
    } catch (e: Exception) {
        loopPlayer = null
    }
}
```

---

## Modificari UI (SettingsScreen.tsx)

### Buton "Choose from Phone" la sfarsitul listei

In lista de sunete (ringtone si message tone), adauga ultima optiune:

```typescript
// La sfarsitul RINGTONE_OPTIONS si MESSAGE_TONE_OPTIONS:
{
  id: 'custom_pick',
  nameKey: 'settings.chooseFromPhone',
  soundId: -1,  // Marker special
  isCustomPicker: true
}
```

### Afisare sunet custom selectat

Daca setarea curenta e `file:...`, afiseaza:
- Numele fisierului (fara extensie, fara prefix `custom_ringtone_`)
- Sau un label generic: "Custom Sound"
- Cu buton "Change" si "Remove" (revine la default)

### Flow complet UI

```
1. User apasa "Choose from Phone"
2. DocumentPicker se deschide
3. User selecteaza fisier audio
4. Fisierul se copiaza in app storage
5. Se reda preview 5 secunde
6. Se salveaza ca `file:custom_ringtone_1679012345.m4a`
7. Lista se inchide, optiunea curenta arata "Custom Sound" cu filename
8. La urmatorul apel/mesaj, se reda acest fisier
```

---

## Modificari soundOptions.ts

```typescript
import RNFS from 'react-native-fs';
import { Platform } from 'react-native';

export const CUSTOM_SOUNDS_DIR = `${RNFS.DocumentDirectoryPath}/custom-sounds`;

export interface SoundOption {
  id: string;
  name?: string;
  nameKey?: string;
  soundId: number;
  isCustomPicker?: boolean;
  isCustomFile?: boolean;
  filePath?: string;
}

// Optiune speciala adaugata la sfarsitul fiecarei liste:
export const CUSTOM_PICK_OPTION: SoundOption = {
  id: 'custom_pick',
  nameKey: 'settings.chooseFromPhone',
  soundId: -1,
  isCustomPicker: true,
};

// Functie helper pentru a genera optiunea custom curenta
export function getCustomSoundOption(settingValue: string): SoundOption | null {
  if (!settingValue.startsWith('file:')) return null;
  const filename = settingValue.substring(5);
  const displayName = filename
    .replace(/^custom_(ringtone|message)_\d+\./, '')
    .replace(/\.[^.]+$/, '')
    || 'Custom Sound';
  return {
    id: settingValue,
    name: displayName,
    soundId: -2,
    isCustomFile: true,
    filePath: `${CUSTOM_SOUNDS_DIR}/${filename}`,
  };
}
```

---

## NotificationService.ts — Modificari

### playCallSound (liniile 124-181)

Logica pentru `file:` exista deja (liniile 153-167). Trebuie doar verificat ca:
1. Path-ul se construieste corect: `RNFS.DocumentDirectoryPath + '/custom-sounds/' + soundId.substring(5)`
2. Se verifica daca fisierul exista inainte de a-l reda
3. Fallback la default daca fisierul lipseste

### showMessageNotification (liniile 57-121)

Adauga suport pentru `file:` (similar cu apelul):

```typescript
if (soundId.startsWith('file:')) {
  const filename = soundId.substring(5);
  const path = `${RNFS.DocumentDirectoryPath}/custom-sounds/${filename}`;
  const exists = await RNFS.exists(path);
  if (exists) {
    SystemSoundModule?.playAudioFile?.(path);
  } else {
    // Fallback: sunet default
    SystemSoundModule?.playSystemSound(1007);
  }
} else {
  const parsedSoundId = parseInt(soundId, 10);
  if (parsedSoundId > 0) {
    SystemSoundModule?.playSystemSound(parsedSoundId);
  }
}
```

---

## Ordinea Implementarii

### Faza 1 — iOS (Prioritate)

1. Instaleaza `react-native-document-picker` (daca nu exista)
2. Instaleaza `react-native-fs` (daca nu exista) + `cd ios && pod install`
3. Adauga `playAudioFile` in SystemSoundModule.swift + .m
4. Modifica soundOptions.ts
5. Modifica SettingsScreen.tsx — adauga picker + UI custom sound
6. Modifica NotificationService.ts — suport `file:` in mesaje
7. Testare pe simulator + iPhone fizic

### Faza 2 — Android

1. Verifica `react-native-document-picker` functioneaza pe Android
2. Fix `playAudioFileLoop` in SystemSoundModule.kt — sa foloseasca path-ul real
3. Adauga `playAudioFile` in SystemSoundModule.kt
4. Permisiuni Android: `READ_MEDIA_AUDIO` (Android 13+) sau `READ_EXTERNAL_STORAGE` (< 13)
5. Testare pe emulator + telefon fizic

---

## Securitate

- Fisierele audio sunt copiate IN app storage (sandbox) — nu se acceseaza din locatia originala
- Nu se stocheaza path-uri absolute din afara app-ului
- Cleanup: cand utilizatorul schimba sunetul, stergem fisierul vechi cu `RNFS.unlink()`
- Limitare marime: max 10MB per fisier audio (previne abuz)
- Tipuri acceptate: audio/* (mp3, m4a, wav, aac, ogg)

---

## Traduceri Necesare (i18n)

```json
{
  "settings.chooseFromPhone": "Choose from Phone",
  "settings.customSound": "Custom Sound",
  "settings.removeCustomSound": "Remove custom sound",
  "settings.changeCustomSound": "Change",
  "settings.soundTooLarge": "File too large (max 10MB)",
  "settings.soundCopyError": "Failed to save sound file",
  "settings.soundFormatError": "Unsupported audio format"
}
```

---

## Diagrama Flow

```
User -> Settings -> Sounds -> "Choose from Phone"
  |
  v
DocumentPicker.pick({ type: ['public.audio'] / ['audio/*'] })
  |
  v
RNFS.mkdir(custom-sounds/) -> RNFS.copyFile(uri, dest)
  |
  v
Database.saveSettings({ callRingtone: 'file:custom_ringtone_xxx.m4a' })
  |
  v
[Later] Incoming call -> NotificationService.playCallSound()
  -> soundId = 'file:custom_ringtone_xxx.m4a'
  -> path = DocumentDir/custom-sounds/custom_ringtone_xxx.m4a
  -> SystemSoundModule.playAudioFileLoop(path)
  -> AVAudioPlayer(numberOfLoops: -1) / MediaPlayer(isLooping: true)
  -> MELODIA SE REDA COMPLET, APOI REPETA!
```
