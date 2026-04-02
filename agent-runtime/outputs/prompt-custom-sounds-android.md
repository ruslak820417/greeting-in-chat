# Prompt: Custom Sounds — Android Implementation

## Obiectiv

Implementeaza selectarea de sunete personalizate din telefonul utilizatorului pentru apeluri si mesaje in QRChat Android. Melodia de apel se reda COMPLET (toata durata), apoi se repeta de la inceput. Nu se taie.

**PREREQUISIT:** Implementarea iOS trebuie sa fie completa inainte! Fisierele TypeScript (soundOptions.ts, SettingsScreen.tsx, NotificationService.ts) sunt deja modificate de implementarea iOS. Acest prompt se concentreaza pe modificarile native Android si pe ajustarile Platform.OS-specific.

## Proiect: `/Users/ruslanconstantinovici/QRChat-Android`

---

## PASUL 0 — Citeste Aceste Fisiere Inainte de Orice

```
CITESTE OBLIGATORIU:
1. android/app/src/main/java/com/qrchat/SystemSoundModule.kt  — modulul nativ Android curent
2. src/screens/SettingsScreen.tsx          — UI settings (deja modificat de iOS impl)
3. src/utils/soundOptions.ts              — sound options (deja modificat de iOS impl)
4. src/services/NotificationService.ts    — notification service (deja modificat de iOS impl)
5. src/screens/ContactProfileScreen.tsx   — per-contact sounds (deja modificat de iOS impl)
6. android/app/src/main/AndroidManifest.xml — permisiuni
7. android/app/build.gradle               — dependinte Android
```

**IMPORTANT:** Verifica daca fisierele TS sunt deja modificate (au import DocumentPicker, RNFS, CUSTOM_PICK_OPTION). Daca NU — aplica intai prompt-ul iOS care modifica acele fisiere!

---

## PASUL 1 — Verifica Dependinte

```bash
cd /Users/ruslanconstantinovici/QRChat-Android

# Verifica ca react-native-document-picker si react-native-fs exista
grep -E "react-native-document-picker|react-native-fs" package.json

# Daca lipsesc (nu ar trebui daca iOS e deja implementat):
npm install react-native-document-picker react-native-fs
```

**React Native 0.84+ autolink:** Nu trebuie manual linking — `npx react-native run-android` face autolink.

---

## PASUL 2 — Permisiuni Android

**Fisier:** `android/app/src/main/AndroidManifest.xml`

Adauga permisiunile necesare INAINTE de `<application`:

```xml
<!-- Custom sounds: acces la fisiere audio -->
<!-- Android 13+ (API 33+) -->
<uses-permission android:name="android.permission.READ_MEDIA_AUDIO" />
<!-- Android < 13 -->
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE"
    android:maxSdkVersion="32" />
```

**Nota:** `react-native-document-picker` cu `copyTo: 'documentDirectory'` copiaza fisierul in sandbox-ul aplicatiei. Permisiunea trebuie doar pentru picker-ul initial sa citeasca fisierele din telefonul utilizatorului. Dupa copiere, permisiunea nu mai e necesara.

---

## PASUL 3 — Modifica SystemSoundModule.kt

**Fisier:** `android/app/src/main/java/com/qrchat/SystemSoundModule.kt`

### 3a. FIX CRITIC: `playAudioFileLoop` — sa foloseasca path-ul real

Metoda curenta ignora parametrul `path` si reda DOAR default ringtone! FIX:

```kotlin
/**
 * Play an audio file in a loop (used for incoming call ringtone).
 * MELODIA SE REDA COMPLET, APOI SE REPETA DE LA INCEPUT.
 */
@ReactMethod
fun playAudioFileLoop(path: String) {
    stopLoop()
    try {
        val cleanPath = path.removePrefix("file://").removePrefix("file:")
        loopPlayer = MediaPlayer().apply {
            setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_NOTIFICATION_RINGTONE)
                    .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                    .build()
            )
            setDataSource(cleanPath)  // FISIERUL REAL — nu default ringtone!
            isLooping = true          // Loop infinit — melodia completa se repeta
            prepare()
            start()
        }
    } catch (e: Exception) {
        // Fallback: daca fisierul nu poate fi redat, reda default ringtone
        loopPlayer = null
        try {
            val uri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE) ?: return
            loopPlayer = MediaPlayer().apply {
                setAudioAttributes(
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_NOTIFICATION_RINGTONE)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                        .build()
                )
                setDataSource(reactApplicationContext, uri)
                isLooping = true
                prepare()
                start()
            }
        } catch (e2: Exception) {
            loopPlayer = null
        }
    }
}
```

### 3b. Adauga metoda `playAudioFile` (fara loop — pentru mesaje si preview)

Adauga DUPA `playAudioFileLoop`:

```kotlin
/**
 * Play an audio file ONCE (no loop) — for message tones and sound preview.
 */
@ReactMethod
fun playAudioFile(path: String) {
    // Opreste orice playback anterior
    try {
        loopPlayer?.stop()
        loopPlayer?.release()
    } catch (_: Exception) {}
    loopPlayer = null
    try { currentRingtone?.stop() } catch (_: Exception) {}
    currentRingtone = null

    try {
        val cleanPath = path.removePrefix("file://").removePrefix("file:")
        loopPlayer = MediaPlayer().apply {
            setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_NOTIFICATION)
                    .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                    .build()
            )
            setDataSource(cleanPath)
            isLooping = false  // O SINGURA DATA — nu loop!
            prepare()
            start()
            // Auto-release cand se termina
            setOnCompletionListener { mp ->
                mp.release()
                if (loopPlayer === mp) loopPlayer = null
            }
        }
    } catch (e: Exception) {
        loopPlayer = null
    }
}
```

### 3c. Codul complet SystemSoundModule.kt dupa modificari

```kotlin
package com.qrchat

import android.media.AudioAttributes
import android.media.AudioManager
import android.media.MediaPlayer
import android.media.RingtoneManager
import android.media.ToneGenerator
import android.os.Handler
import android.os.Looper
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod

class SystemSoundModule(reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

    private var loopPlayer: MediaPlayer? = null
    private var currentRingtone: android.media.Ringtone? = null
    private var toneGenerator: ToneGenerator? = null
    private var ringbackHandler: Handler? = null
    private var ringbackRunnable: Runnable? = null

    override fun getName(): String = "SystemSoundModule"

    /**
     * Play a short notification/ringtone sound.
     */
    @ReactMethod
    fun playSystemSound(soundId: Double) {
        val id = soundId.toInt()
        if (id <= 0) return

        try {
            try { currentRingtone?.stop() } catch (_: Exception) {}

            val type = if (id >= 1005 && id <= 1041) {
                RingtoneManager.TYPE_RINGTONE
            } else {
                RingtoneManager.TYPE_NOTIFICATION
            }

            val uri = RingtoneManager.getDefaultUri(type) ?: return
            currentRingtone = RingtoneManager.getRingtone(reactApplicationContext, uri)
            currentRingtone?.play()
        } catch (e: Exception) {
            // Silently fail
        }
    }

    /**
     * Play an audio file in a loop (used for incoming call ringtone).
     * MELODIA SE REDA COMPLET, APOI SE REPETA.
     */
    @ReactMethod
    fun playAudioFileLoop(path: String) {
        stopLoop()
        try {
            val cleanPath = path.removePrefix("file://").removePrefix("file:")
            loopPlayer = MediaPlayer().apply {
                setAudioAttributes(
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_NOTIFICATION_RINGTONE)
                        .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                        .build()
                )
                setDataSource(cleanPath)
                isLooping = true
                prepare()
                start()
            }
        } catch (e: Exception) {
            loopPlayer = null
            // Fallback: default ringtone
            try {
                val uri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE) ?: return
                loopPlayer = MediaPlayer().apply {
                    setAudioAttributes(
                        AudioAttributes.Builder()
                            .setUsage(AudioAttributes.USAGE_NOTIFICATION_RINGTONE)
                            .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                            .build()
                    )
                    setDataSource(reactApplicationContext, uri)
                    isLooping = true
                    prepare()
                    start()
                }
            } catch (e2: Exception) {
                loopPlayer = null
            }
        }
    }

    /**
     * Play an audio file ONCE (no loop) — for message tones and sound preview.
     */
    @ReactMethod
    fun playAudioFile(path: String) {
        try {
            loopPlayer?.stop()
            loopPlayer?.release()
        } catch (_: Exception) {}
        loopPlayer = null
        try { currentRingtone?.stop() } catch (_: Exception) {}
        currentRingtone = null

        try {
            val cleanPath = path.removePrefix("file://").removePrefix("file:")
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
                setOnCompletionListener { mp ->
                    mp.release()
                    if (loopPlayer === mp) loopPlayer = null
                }
            }
        } catch (e: Exception) {
            loopPlayer = null
        }
    }

    /**
     * Play the standard ringback tone for outgoing calls.
     */
    @ReactMethod
    fun startRingback() {
        stopRingback()
        try {
            toneGenerator = ToneGenerator(AudioManager.STREAM_VOICE_CALL, 80)
            ringbackHandler = Handler(Looper.getMainLooper())
            ringbackRunnable = object : Runnable {
                override fun run() {
                    try {
                        toneGenerator?.startTone(ToneGenerator.TONE_SUP_RINGTONE, 1000)
                    } catch (_: Exception) {}
                    ringbackHandler?.postDelayed(this, 4000)
                }
            }
            ringbackRunnable?.run()
        } catch (e: Exception) {
            toneGenerator = null
        }
    }

    /**
     * Stop the ringback tone.
     */
    @ReactMethod
    fun stopRingback() {
        try {
            ringbackRunnable?.let { ringbackHandler?.removeCallbacks(it) }
            toneGenerator?.stopTone()
            toneGenerator?.release()
        } catch (_: Exception) {}
        toneGenerator = null
        ringbackHandler = null
        ringbackRunnable = null
    }

    /**
     * Stop any looping audio playback.
     */
    @ReactMethod
    fun stopLoop() {
        try {
            loopPlayer?.stop()
            loopPlayer?.release()
        } catch (_: Exception) {}
        loopPlayer = null
        try { currentRingtone?.stop() } catch (_: Exception) {}
        currentRingtone = null
    }
}
```

---

## PASUL 4 — Verifica fisierele TypeScript (deja modificate de iOS)

### 4a. soundOptions.ts

**Verifica** ca exista:
- `import RNFS from 'react-native-fs'`
- `CUSTOM_SOUNDS_DIR`
- `CUSTOM_PICK_OPTION`
- `getCustomSoundOption()`
- `copyAudioToAppStorage()`
- `deleteCustomSound()`

Daca NU — aplica modificarile din prompt-ul iOS.

### 4b. SettingsScreen.tsx

**Verifica** ca exista:
- `import DocumentPicker from 'react-native-document-picker'`
- Functia `pickCustomSound()`
- `renderSoundSelector` modificat cu `CUSTOM_PICK_OPTION`

**IMPORTANT Platform.OS check:** In functia `pickCustomSound`, verifica ca picker-ul foloseste tipul corect:

```typescript
const result = await DocumentPicker.pick({
  type: Platform.OS === 'ios'
    ? ['public.audio']    // iOS UTType
    : ['audio/*'],         // Android MIME type
  copyTo: 'documentDirectory',
});
```

### 4c. NotificationService.ts

**Verifica** ca exista:
- `import RNFS from 'react-native-fs'`
- `const CUSTOM_SOUNDS_DIR = ...`
- Suport `file:` in `showMessageNotification()`
- Fix path in `playCallSound()` (cu CUSTOM_SOUNDS_DIR)

---

## PASUL 5 — Permisiuni Runtime (Android 13+)

Pe Android 13+ (API 33), permisiunea `READ_MEDIA_AUDIO` trebuie ceruta la runtime. `react-native-document-picker` gestioneaza partial acest lucru, dar daca picker-ul esueaza pe Android 13+, adauga cerere explicita.

In `pickCustomSound()` din SettingsScreen.tsx, adauga (doar pt Android):

```typescript
import { PermissionsAndroid } from 'react-native';

// La inceputul functiei pickCustomSound, inainte de DocumentPicker.pick:
if (Platform.OS === 'android') {
  const apiLevel = Platform.Version;
  if (typeof apiLevel === 'number' && apiLevel >= 33) {
    const granted = await PermissionsAndroid.request(
      'android.permission.READ_MEDIA_AUDIO' as any,
      {
        title: t('settings.audioPermissionTitle') || 'Audio Access',
        message: t('settings.audioPermissionMessage') || 'QRChat needs access to your audio files to set custom sounds.',
        buttonPositive: t('common.ok') || 'OK',
      }
    );
    if (granted !== PermissionsAndroid.RESULTS.GRANTED) {
      Alert.alert(t('common.error'), t('settings.audioPermissionDenied') || 'Audio permission denied');
      return;
    }
  }
}
```

Adauga traduceri:
```json
"settings.audioPermissionTitle": "Audio Access",
"settings.audioPermissionMessage": "QRChat needs access to your audio files to set custom sounds.",
"settings.audioPermissionDenied": "Permission to access audio files was denied"
```

---

## PASUL 6 — Build si Test

```bash
cd /Users/ruslanconstantinovici/QRChat-Android

# Clean build
cd android && ./gradlew clean && cd ..
npx react-native run-android

# SAU pe telefon fizic:
npx react-native run-android --deviceId=<device-id>
```

### Test Checklist Android

| # | Test | Expected |
|---|------|----------|
| 1 | Settings > Sounds > Call Ringtone > "Choose from Phone" | Se deschide picker Android nativ |
| 2 | Selecteaza un fisier audio (.mp3, .m4a) | Se copiaza in app, se reda preview 5s |
| 3 | Setarea arata "Custom Sound" cu filename | Corect |
| 4 | Butonul "x" sterge sunetul custom, revine la default | Corect |
| 5 | Apel incoming cu sunet custom | Melodia suna COMPLET si se REPETA |
| 6 | Mesaj incoming cu sunet custom | Se reda O DATA |
| 7 | Selecteaza "No Sound" | Niciun sunet la apel/mesaj |
| 8 | Revino la system sound | Functioneaza ca inainte |
| 9 | Android 13+ (Pixel 7/8): permisiune audio | Se cere permisiunea, functioneaza |
| 10 | Android < 13: permisiune storage | Functioneaza fara dialog extra |
| 11 | Fisier > 10MB | Alert "File too large" |
| 12 | Reinstaleaza app — custom sounds persistente? | DA — fisierele sunt in DocumentDir |
| 13 | Per-contact custom tone (ContactProfile) | Functioneaza identic |

---

## Diferente Cheie iOS vs Android

| Aspect | iOS | Android |
|--------|-----|---------|
| Picker type | `['public.audio']` UTType | `['audio/*']` MIME |
| Native play | AVAudioPlayer | MediaPlayer |
| Loop | numberOfLoops = -1 | isLooping = true |
| No loop | numberOfLoops = 0 | isLooping = false |
| Stop | audioPlayer.stop() | loopPlayer.stop() + release() |
| Permission | N/A (sandboxed) | READ_MEDIA_AUDIO (13+) / READ_EXTERNAL_STORAGE (<13) |
| File path | /Documents/custom-sounds/ | /data/data/com.qrchat/files/custom-sounds/ |
| Fallback | System sound ID | Default RingtoneManager |

---

## Rezumat Fisiere Modificate Android

| Fisier | Ce se face |
|--------|-----------|
| `android/app/src/main/java/com/qrchat/SystemSoundModule.kt` | FIX playAudioFileLoop (path real), +playAudioFile (no loop) |
| `android/app/src/main/AndroidManifest.xml` | +READ_MEDIA_AUDIO, +READ_EXTERNAL_STORAGE |
| `src/screens/SettingsScreen.tsx` | +PermissionsAndroid check (daca nu exista) |
| `src/i18n/locales/en.json` | +3 chei permisiuni (daca nu exista) |
| `src/i18n/locales/ro.json` | +3 chei permisiuni |
| `src/i18n/locales/ru.json` | +3 chei permisiuni |

**Nota:** Restul fisierelor TS (soundOptions.ts, NotificationService.ts, ContactProfileScreen.tsx) sunt deja modificate de implementarea iOS si NU trebuie modificate din nou. Codul TS este cross-platform cu Platform.OS checks acolo unde e nevoie.

---

## Buguri Cunoscute de Evitat

1. **MediaPlayer leak:** INTOTDEAUNA apeleaza `release()` dupa `stop()` pe Android. Fara release(), MediaPlayer-ul ramane in memorie.
2. **File URI vs File Path:** Pe Android, DocumentPicker poate returna un URI content:// — de aceea folosim `copyTo: 'documentDirectory'` si `fileCopyUri` care e un path real.
3. **Scoped Storage (Android 11+):** Nu putem accesa direct fisiere din storage-ul extern. Picker-ul gestioneaza asta — fisierul e copiat in sandbox.
4. **AudioFocus:** Cand se reda sunetul de apel, considera setarea `AudioAttributes.USAGE_NOTIFICATION_RINGTONE` care are prioritate mare si poate intrerupe alte playere audio.
