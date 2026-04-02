# Prompt: Custom Sounds — iOS Implementation

## Obiectiv

Implementeaza selectarea de sunete personalizate din telefonul utilizatorului pentru apeluri si mesaje in QRChat iOS. Melodia de apel se reda COMPLET (toata durata), apoi se repeta de la inceput. Nu se taie.

## Proiect: `/Users/ruslanconstantinovici/QRChat`

---

## PASUL 0 — Citeste Aceste Fisiere Inainte de Orice

```
CITESTE OBLIGATORIU:
1. src/screens/SettingsScreen.tsx            — UI settings, renderSoundSelector(), playPreviewTone()
2. src/utils/soundOptions.ts                 — RINGTONE_OPTIONS, MESSAGE_TONE_OPTIONS
3. src/services/NotificationService.ts       — playCallSound(), showMessageNotification()
4. ios/QRChat/SystemSoundModule.swift        — playSystemSound, playAudioFileLoop, stopLoop
5. ios/QRChat/SystemSoundModule.m            — bridge ObjC
6. src/screens/ContactProfileScreen.tsx      — per-contact custom ringtone/message tone
7. src/storage/Database.ts                   — customRingtone, customMessageTone columns
8. src/utils/types.ts                        — Contact type definition
9. src/i18n/locales/en.json                  — English translations
10. src/i18n/locales/ro.json                 — Romanian translations
11. src/i18n/locales/ru.json                 — Russian translations
```

---

## PASUL 1 — Instaleaza Dependinte

```bash
cd /Users/ruslanconstantinovici/QRChat

# Document Picker — pentru selectare fisier audio din telefon
npm install react-native-document-picker

# RNFS — pentru copiere fisier in app storage
# (verifica daca nu e deja instalat: grep "react-native-fs" package.json)
npm install react-native-fs

# Pod install
cd ios && pod install && cd ..
```

**Verifica dupa instalare:**
```bash
grep -E "react-native-document-picker|react-native-fs" package.json
```

---

## PASUL 2 — Modifica SystemSoundModule.swift

**Fisier:** `ios/QRChat/SystemSoundModule.swift`

Adauga metoda `playAudioFile` (reda O SINGURA DATA, fara loop — pentru mesaje si preview):

```swift
// Adauga DUPA metoda playAudioFileLoop, INAINTE de stopLoop

  /// Reda un fisier audio O SINGURA DATA (fara loop) — pentru mesaje si preview
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
        player.numberOfLoops = 0  // O SINGURA DATA — NU loop
        player.play()
        self?.audioPlayer = player
      } catch {
        print("[SystemSoundModule] playAudioFile error: \(error)")
      }
    }
  }
```

---

## PASUL 3 — Modifica SystemSoundModule.m (Bridge)

**Fisier:** `ios/QRChat/SystemSoundModule.m`

Adauga linia noua dupa `RCT_EXTERN_METHOD(playAudioFileLoop:(NSString *)path)`:

```objc
RCT_EXTERN_METHOD(playAudioFile:(NSString *)path)
```

**Fisierul complet dupa modificare:**
```objc
#import <React/RCTBridgeModule.h>

@interface RCT_EXTERN_MODULE(SystemSoundModule, NSObject)
RCT_EXTERN_METHOD(playSystemSound:(double)soundId)
RCT_EXTERN_METHOD(playSystemSoundLoop:(double)soundId)
RCT_EXTERN_METHOD(playAudioFileLoop:(NSString *)path)
RCT_EXTERN_METHOD(playAudioFile:(NSString *)path)
RCT_EXTERN_METHOD(stopLoop)
@end
```

---

## PASUL 4 — Modifica soundOptions.ts

**Fisier:** `src/utils/soundOptions.ts`

Inlocuieste complet cu:

```typescript
import RNFS from 'react-native-fs';

// iOS System Sound IDs — https://iphonedev.wiki/AudioServices
export const RINGTONE_OPTIONS = [
  { id: '1005', name: 'Opening (Default)', soundId: 1005 },
  { id: '1000', name: 'New Mail', soundId: 1000 },
  { id: '1013', name: 'Alarm', soundId: 1013 },
  { id: '1016', name: 'Tweet', soundId: 1016 },
  { id: '1023', name: 'Anticipate', soundId: 1023 },
  { id: '1025', name: 'Bloom', soundId: 1025 },
  { id: '1026', name: 'Calypso', soundId: 1026 },
  { id: '1027', name: 'Choo Choo', soundId: 1027 },
  { id: '1029', name: 'Descent', soundId: 1029 },
  { id: '1030', name: 'Fanfare', soundId: 1030 },
  { id: '1031', name: 'Ladder', soundId: 1031 },
  { id: '1032', name: 'Minuet', soundId: 1032 },
  { id: '1033', name: 'News Flash', soundId: 1033 },
  { id: '1034', name: 'Noir', soundId: 1034 },
  { id: '1035', name: 'Sherwood Forest', soundId: 1035 },
  { id: '1036', name: 'Spell', soundId: 1036 },
  { id: '1038', name: 'Telegraph', soundId: 1038 },
  { id: '1039', name: 'Tiptoes', soundId: 1039 },
  { id: '1040', name: 'Typewriters', soundId: 1040 },
  { id: '1041', name: 'Update', soundId: 1041 },
  { id: '0', nameKey: 'settings.noSound', soundId: 0 },
];

export const MESSAGE_TONE_OPTIONS = [
  { id: '1007', name: 'Received (Default)', soundId: 1007 },
  { id: '1003', name: 'Mail Sent', soundId: 1003 },
  { id: '1004', name: 'Voicemail', soundId: 1004 },
  { id: '1009', name: 'Tock', soundId: 1009 },
  { id: '1014', name: 'Key Press Click', soundId: 1014 },
  { id: '1015', name: 'Lock', soundId: 1015 },
  { id: '1028', name: 'Ding', soundId: 1028 },
  { id: '1103', name: 'Swish', soundId: 1103 },
  { id: '1104', name: 'Swoosh', soundId: 1104 },
  { id: '1110', name: 'Tink', soundId: 1110 },
  { id: '1111', name: 'Boop', soundId: 1111 },
  { id: '1112', name: 'Pong', soundId: 1112 },
  { id: '1113', name: 'Shake', soundId: 1113 },
  { id: '1114', name: 'Jingle', soundId: 1114 },
  { id: '1115', name: 'Sparkle', soundId: 1115 },
  { id: '0', nameKey: 'settings.noSound', soundId: 0 },
];

// --- Custom Sounds Support ---

export const CUSTOM_SOUNDS_DIR = `${RNFS.DocumentDirectoryPath}/custom-sounds`;

export const MAX_SOUND_FILE_SIZE = 10 * 1024 * 1024; // 10MB

export interface SoundOption {
  id: string;
  name?: string;
  nameKey?: string;
  soundId: number;
  isCustomPicker?: boolean;
  isCustomFile?: boolean;
  filePath?: string;
}

// Optiune speciala — ultimul item in lista, deschide picker-ul
export const CUSTOM_PICK_OPTION: SoundOption = {
  id: 'custom_pick',
  nameKey: 'settings.chooseFromPhone',
  soundId: -1,
  isCustomPicker: true,
};

// Genereaza optiune afisabila pentru sunetul custom curent
export function getCustomSoundOption(settingValue: string, type: 'ringtone' | 'message'): SoundOption | null {
  if (!settingValue || !settingValue.startsWith('file:')) return null;
  const filename = settingValue.substring(5);
  // Extrage un display name curat din filename
  const displayName = filename
    .replace(/^custom_(ringtone|message)_\d+/, '')
    .replace(/^\./, '')
    .replace(/\.[^.]+$/, '')
    || 'Custom Sound';
  return {
    id: settingValue,
    name: displayName.length > 0 ? displayName : 'Custom Sound',
    soundId: -2, // marker: fisier custom
    isCustomFile: true,
    filePath: `${CUSTOM_SOUNDS_DIR}/${filename}`,
  };
}

// Helper: copiaza fisierul selectat in app storage
export async function copyAudioToAppStorage(
  sourceUri: string,
  sourceName: string,
  type: 'ringtone' | 'message',
): Promise<string> {
  // Asigura ca directorul exista
  const dirExists = await RNFS.exists(CUSTOM_SOUNDS_DIR);
  if (!dirExists) {
    await RNFS.mkdir(CUSTOM_SOUNDS_DIR);
  }

  // Extrage extensia
  const ext = sourceName.includes('.')
    ? sourceName.substring(sourceName.lastIndexOf('.'))
    : '.m4a';

  // Filename unic
  const filename = `custom_${type}_${Date.now()}${ext}`;
  const destPath = `${CUSTOM_SOUNDS_DIR}/${filename}`;

  // Copiaza
  await RNFS.copyFile(sourceUri, destPath);

  // Verifica
  const exists = await RNFS.exists(destPath);
  if (!exists) throw new Error('File copy verification failed');

  return filename;
}

// Helper: sterge un fisier custom vechi
export async function deleteCustomSound(settingValue: string): Promise<void> {
  if (!settingValue || !settingValue.startsWith('file:')) return;
  const filename = settingValue.substring(5);
  const path = `${CUSTOM_SOUNDS_DIR}/${filename}`;
  try {
    const exists = await RNFS.exists(path);
    if (exists) await RNFS.unlink(path);
  } catch (e) {
    console.warn('[soundOptions] deleteCustomSound error:', e);
  }
}
```

---

## PASUL 5 — Modifica SettingsScreen.tsx

**Fisier:** `src/screens/SettingsScreen.tsx`

### 5a. Adauga importuri noi (la inceputul fisierului)

```typescript
import { Alert, Platform } from 'react-native'; // Alert deja exista, Platform poate lipsi
import DocumentPicker from 'react-native-document-picker';
import RNFS from 'react-native-fs';
import {
  RINGTONE_OPTIONS,
  MESSAGE_TONE_OPTIONS,
  CUSTOM_PICK_OPTION,
  CUSTOM_SOUNDS_DIR,
  MAX_SOUND_FILE_SIZE,
  getCustomSoundOption,
  copyAudioToAppStorage,
  deleteCustomSound,
} from '../utils/soundOptions';
```

**Sterge** importul vechi: `import { RINGTONE_OPTIONS, MESSAGE_TONE_OPTIONS } from '../utils/soundOptions';`

### 5b. Adauga functia de pick audio (in componenta, dupa `playPreviewTone`)

```typescript
const pickCustomSound = async (settingKey: 'callRingtone' | 'messageTone', type: 'ringtone' | 'message') => {
  try {
    const result = await DocumentPicker.pick({
      type: Platform.OS === 'ios'
        ? ['public.audio']
        : ['audio/*'],
      copyTo: 'documentDirectory',
    });

    const file = result[0];
    if (!file) return;

    // Verifica marime
    if (file.size && file.size > MAX_SOUND_FILE_SIZE) {
      Alert.alert(t('common.error'), t('settings.soundTooLarge'));
      return;
    }

    // Copiaza in app storage
    const sourceUri = file.fileCopyUri || file.uri;
    const filename = await copyAudioToAppStorage(sourceUri, file.name || 'audio.m4a', type);

    // Sterge fisierul custom vechi daca exista
    const currentValue = (settings as any)[settingKey];
    await deleteCustomSound(currentValue);

    // Salveaza setarea
    const newValue = `file:${filename}`;
    await updateSetting(settingKey, newValue);

    // Preview — reda 5 secunde
    const fullPath = `${CUSTOM_SOUNDS_DIR}/${filename}`;
    SystemSoundModule?.playAudioFile?.(fullPath);
    setTimeout(() => {
      try { SystemSoundModule?.stopLoop?.(); } catch (e) {}
    }, 5000);

  } catch (err: any) {
    if (DocumentPicker.isCancel(err)) return;
    console.warn('[SettingsScreen] pickCustomSound error:', err);
    Alert.alert(t('common.error'), t('settings.soundCopyError'));
  }
};
```

### 5c. Modifica `playPreviewTone` sa suporte fisiere custom

```typescript
const playPreviewTone = (soundId: number, filePath?: string) => {
  try {
    SystemSoundModule?.stopLoop?.();
    if (filePath) {
      // Fisier custom — reda cu playAudioFile
      SystemSoundModule?.playAudioFile?.(filePath);
      // Stop dupa 5 secunde
      setTimeout(() => {
        try { SystemSoundModule?.stopLoop?.(); } catch (e) {}
      }, 5000);
    } else if (soundId > 0) {
      SystemSoundModule?.playSystemSound(soundId);
    }
  } catch (e) {
    console.warn('playPreviewTone error:', e);
  }
};
```

### 5d. Modifica `renderSoundSelector` — adauga suport custom

Modifica functia `renderSoundSelector` astfel:

```typescript
const renderSoundSelector = (
  label: string,
  desc: string,
  settingKey: 'callRingtone' | 'messageTone',
  options: typeof RINGTONE_OPTIONS,
  expanded: boolean,
  setExpanded: (v: boolean) => void,
) => {
  const currentValue = (settings as any)[settingKey] as string;
  const customOpt = getCustomSoundOption(currentValue, settingKey === 'callRingtone' ? 'ringtone' : 'message');
  const type = settingKey === 'callRingtone' ? 'ringtone' : 'message';

  // Construieste lista completa: custom curent (daca exista) + predefinite + picker
  const allOptions: any[] = [];
  if (customOpt) allOptions.push(customOpt);
  allOptions.push(...options);
  allOptions.push(CUSTOM_PICK_OPTION);

  const currentOption = allOptions.find(o => o.id === currentValue) || allOptions.find(o => o.id === options[0].id) || allOptions[0];

  return (
    <View style={{ marginBottom: 8 }}>
      <TouchableOpacity
        style={[styles.settingRow, { backgroundColor: C.surface, borderColor: C.border }]}
        onPress={() => setExpanded(!expanded)}
        activeOpacity={0.7}
        accessibilityLabel={label}
        accessibilityRole="button"
      >
        <View style={{ flex: 1 }}>
          <Text style={[styles.settingLabel, { color: C.text }]}>{label}</Text>
          <Text style={[styles.settingDesc, { color: C.textSecondary }]}>{desc}</Text>
        </View>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
          <Text style={[styles.timerValue, { color: C.primary }]}>
            {currentOption.nameKey ? t(currentOption.nameKey) : currentOption.name}
          </Text>
          <Text style={{ color: C.textSecondary, fontSize: 12 }}>{expanded ? '\u25B2' : '\u25BC'}</Text>
        </View>
      </TouchableOpacity>
      {expanded && (
        <View style={[styles.soundList, { backgroundColor: C.surface, borderColor: C.border }]}>
          {allOptions.map((opt: any) => {
            const isActive = currentValue === opt.id;

            // Optiunea "Choose from Phone" — deschide picker
            if (opt.isCustomPicker) {
              return (
                <TouchableOpacity
                  key="custom_pick"
                  style={[
                    styles.soundOption,
                    { borderBottomColor: `${C.border}80` },
                  ]}
                  activeOpacity={0.7}
                  onPress={() => pickCustomSound(settingKey, type)}
                  accessibilityLabel={t('settings.chooseFromPhone')}
                  accessibilityRole="button"
                >
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
                    <View style={[styles.radioOuter, { borderColor: C.accent, borderStyle: 'dashed' }]}>
                      <Text style={{ color: C.accent, fontSize: 14, fontWeight: '700' }}>+</Text>
                    </View>
                    <Text style={[styles.soundName, { color: C.accent, fontWeight: '600' }]}>
                      {t('settings.chooseFromPhone')}
                    </Text>
                  </View>
                </TouchableOpacity>
              );
            }

            // Optiune normala (system sound sau custom file)
            return (
              <TouchableOpacity
                key={opt.id}
                style={[
                  styles.soundOption,
                  { borderBottomColor: `${C.border}80` },
                  isActive && { backgroundColor: `${C.accent}1A` },
                ]}
                activeOpacity={0.7}
                onPress={() => {
                  updateSetting(settingKey, opt.id);
                  if (opt.isCustomFile && opt.filePath) {
                    playPreviewTone(-1, opt.filePath);
                  } else {
                    playPreviewTone(opt.soundId);
                  }
                }}
                accessibilityLabel={`Sound: ${opt.nameKey ? t(opt.nameKey) : opt.name}`}
                accessibilityRole="radio"
                accessibilityState={{ selected: isActive }}
              >
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
                  <View style={[
                    styles.radioOuter,
                    { borderColor: isActive ? C.accent : C.textSecondary },
                  ]}>
                    {isActive && <View style={[styles.radioInner, { backgroundColor: C.accent }]} />}
                  </View>
                  <View>
                    <Text style={[styles.soundName, { color: C.text }]}>
                      {opt.nameKey ? t(opt.nameKey) : opt.name}
                    </Text>
                    {opt.isCustomFile && (
                      <Text style={{ color: C.textSecondary, fontSize: 11, marginTop: 2 }}>
                        {t('settings.customSound')}
                      </Text>
                    )}
                  </View>
                </View>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                  {/* Preview button */}
                  {(opt.soundId > 0 || opt.isCustomFile) && (
                    <TouchableOpacity
                      onPress={() => {
                        if (opt.isCustomFile && opt.filePath) {
                          playPreviewTone(-1, opt.filePath);
                        } else {
                          playPreviewTone(opt.soundId);
                        }
                      }}
                      style={[styles.previewBtn, { backgroundColor: `${C.accent}1A`, borderColor: `${C.accent}33` }]}
                      accessibilityLabel="Preview sound"
                      accessibilityRole="button"
                    >
                      <Text style={{ color: C.accent, fontSize: 11, fontWeight: '600' }}>&#9654; Test</Text>
                    </TouchableOpacity>
                  )}
                  {/* Remove custom sound button */}
                  {opt.isCustomFile && isActive && (
                    <TouchableOpacity
                      onPress={async () => {
                        await deleteCustomSound(opt.id);
                        // Revert la default
                        const defaultId = settingKey === 'callRingtone' ? '1005' : '1007';
                        updateSetting(settingKey, defaultId);
                      }}
                      style={{ padding: 4 }}
                      accessibilityLabel="Remove custom sound"
                      accessibilityRole="button"
                    >
                      <Text style={{ color: C.error, fontSize: 18 }}>x</Text>
                    </TouchableOpacity>
                  )}
                </View>
              </TouchableOpacity>
            );
          })}
        </View>
      )}
    </View>
  );
};
```

### 5e. Actualizeaza apelurile renderSoundSelector

**Nu trebuie schimbat** — functia are deja `settingKey` ca string, dar trebuie schimbat tipul parametrului options si settingKey in definitia functiei (vezi 5d mai sus unde am pus `settingKey: 'callRingtone' | 'messageTone'`).

---

## PASUL 6 — Modifica NotificationService.ts

**Fisier:** `src/services/NotificationService.ts`

### 6a. Adauga import RNFS

```typescript
import RNFS from 'react-native-fs';
```

### 6b. Adauga constanta pentru directorul custom sounds

```typescript
const CUSTOM_SOUNDS_DIR = `${RNFS.DocumentDirectoryPath}/custom-sounds`;
```

### 6c. Modifica `showMessageNotification` (linia ~70-78)

Inlocuieste blocul de playback foreground (liniile 74-79) cu:

```typescript
// Prim-plan (active): reda sunetul custom, apoi return
if (AppState.currentState === 'active') {
  if (soundsEnabled) {
    if (soundId.startsWith('file:')) {
      const filename = soundId.substring(5);
      const path = `${CUSTOM_SOUNDS_DIR}/${filename}`;
      const exists = await RNFS.exists(path);
      if (exists) {
        SystemSoundModule?.playAudioFile?.(path);
      } else {
        SystemSoundModule?.playSystemSound(1007); // fallback
      }
    } else {
      const parsedSoundId = parseInt(soundId, 10);
      if (parsedSoundId > 0) {
        SystemSoundModule?.playSystemSound(parsedSoundId);
      }
    }
  }
  return;
}
```

Si blocul background (liniile 90-93) cu acelasi pattern:

```typescript
// Reda sunetul custom prin modulul nativ
if (soundsEnabled) {
  if (soundId.startsWith('file:')) {
    const filename = soundId.substring(5);
    const path = `${CUSTOM_SOUNDS_DIR}/${filename}`;
    const exists = await RNFS.exists(path);
    if (exists) {
      SystemSoundModule?.playAudioFile?.(path);
    } else {
      SystemSoundModule?.playSystemSound(1007); // fallback
    }
  } else {
    const parsedSoundId = parseInt(soundId, 10);
    if (parsedSoundId > 0) {
      SystemSoundModule?.playSystemSound(parsedSoundId);
    }
  }
}
```

### 6d. Verifica `playCallSound` (linia ~124-181)

Logica `file:` exista DEJA (liniile 153-167). Trebuie doar fixat path-ul:

La linia 155, schimba:
```typescript
// INAINTE:
const path = soundId.substring(5);

// DUPA:
const filename = soundId.substring(5);
const path = `${CUSTOM_SOUNDS_DIR}/${filename}`;
```

Si adauga verificare existenta fisier:
```typescript
if (soundId.startsWith('file:')) {
  const filename = soundId.substring(5);
  const path = `${CUSTOM_SOUNDS_DIR}/${filename}`;
  const exists = await RNFS.exists(path);
  if (exists && typeof SystemSoundModule?.playAudioFileLoop === 'function') {
    try {
      SystemSoundModule.playAudioFileLoop(path);
      return; // nativul a pornit loop-ul complet
    } catch (e) {
      console.warn('[NotificationService] playAudioFileLoop error:', e);
    }
  }
  // Fallback la default
  console.warn('[NotificationService] Custom sound file missing or playback failed, falling back');
}
```

---

## PASUL 7 — Modifica ContactProfileScreen.tsx

**Fisier:** `src/screens/ContactProfileScreen.tsx`

Adauga aceleasi modificari ca in SettingsScreen: import DocumentPicker, buton "Choose from Phone" in listele de sunete per-contact, functie pickCustomSound similar. Logica e identica, doar ca salveaza in `contact.customRingtone` / `contact.customMessageTone` prin `saveField()`.

---

## PASUL 8 — Adauga Traduceri

### en.json
```json
"settings.chooseFromPhone": "Choose from Phone",
"settings.customSound": "Custom Sound",
"settings.soundTooLarge": "File too large (max 10MB)",
"settings.soundCopyError": "Failed to save sound file"
```

### ro.json
```json
"settings.chooseFromPhone": "Alege din telefon",
"settings.customSound": "Sunet personalizat",
"settings.soundTooLarge": "Fisier prea mare (max 10MB)",
"settings.soundCopyError": "Nu s-a putut salva fisierul audio"
```

### ru.json
```json
"settings.chooseFromPhone": "Vybirat iz telefona",
"settings.customSound": "Polzovatelskiy zvuk",
"settings.soundTooLarge": "Fayl slishkom bolshoy (maks 10MB)",
"settings.soundCopyError": "Ne udalos sokhranit zvukovoy fayl"
```

---

## PASUL 9 — Build si Test

```bash
cd /Users/ruslanconstantinovici/QRChat

# Clean build
cd ios && pod install && cd ..
npx react-native run-ios --device

# Test checklist:
# 1. Settings > Sounds > Call Ringtone > ultima optiune "Choose from Phone"
# 2. Se deschide picker, selecteaza un fisier audio
# 3. Se reda preview 5 secunde
# 4. Setarea arata "Custom Sound" cu numele fisierului
# 5. Buton "x" pentru a sterge sunetul custom
# 6. Trimite un apel test de pe alt dispozitiv -> melodia suna COMPLET si se repeta
# 7. Trimite un mesaj test -> se reda sunetul custom O DATA
# 8. Selecteaza "No Sound" -> niciun sunet la apel/mesaj
# 9. Revino la system sound -> functioneaza ca inainte
# 10. Testeaza pe simulator SI pe iPhone fizic!
```

---

## Rezumat Fisiere Modificate

| Fisier | Ce se face |
|--------|-----------|
| `ios/QRChat/SystemSoundModule.swift` | +metoda `playAudioFile` (fara loop) |
| `ios/QRChat/SystemSoundModule.m` | +bridge `playAudioFile` |
| `src/utils/soundOptions.ts` | +CUSTOM_PICK_OPTION, helpers copy/delete/display |
| `src/screens/SettingsScreen.tsx` | +DocumentPicker import, pickCustomSound(), modified renderSoundSelector |
| `src/services/NotificationService.ts` | +RNFS import, suport `file:` in mesaje, fix path apeluri |
| `src/screens/ContactProfileScreen.tsx` | +aceleasi modificari ca SettingsScreen (per-contact) |
| `src/i18n/locales/en.json` | +4 chei noi |
| `src/i18n/locales/ro.json` | +4 chei noi |
| `src/i18n/locales/ru.json` | +4 chei noi |
| `package.json` | +react-native-document-picker, +react-native-fs (daca nu exista) |
| `ios/Podfile.lock` | actualizat dupa pod install |
