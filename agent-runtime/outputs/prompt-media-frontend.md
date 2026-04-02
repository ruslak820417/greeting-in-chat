# Prompt: Frontend Engineer — MediaFilesScreen UI Implementation

## Rol
Esti **frontend-engineer** pentru proiectul QRChat. Sarcina ta este sa implementezi ecranul **MediaFilesScreen** — un ecran care afiseaza toate fisierele media dintr-o conversatie cu un contact, organizate pe categorii (Photos, Videos, Audio, Files).

## Context
- **Proiect:** `/Users/ruslanconstantinovici/QRChat`
- **Tech stack:** React Native 0.84, TypeScript 5.8, Ionicons, react-i18next, react-native-safe-area-context
- **Design:** 2 teme (Light orange + Dark teal WhatsApp-style), 4 limbi (en/ro/ru/fr)
- **Referinta design:** Telegram "Shared Media" — grid 3 coloane pentru poze/video, lista pentru audio/fisiere, tab-uri sus

## Fisiere de citit OBLIGATORIU

1. `src/utils/types.ts` — tipurile `MediaItem`, `MediaCategory` (adaugate de architect/backend)
2. `src/storage/Database.ts` — metodele `getMediaByContact()` si `getMediaCountByContact()` (implementate de backend)
3. `src/screens/ContactProfileScreen.tsx` — ecranul din care se navigheaza (trebuie adaugat buton)
4. `src/navigation/AppNavigator.tsx` — trebuie adaugata ruta `MediaFiles`
5. `src/utils/ThemeContext.tsx` — hook `useTheme()`, culorile temei (primary, accent, surface, background, text, border, etc.)
6. `src/screens/ChatScreen.tsx` — liniile 420-620 (rendering file/video/image) ca referinta de stil
7. `src/i18n/locales/en.json` — structura cheilor i18n existente
8. `src/screens/SettingsScreen.tsx` sau `src/screens/ProfileScreen.tsx` — ca referinta pentru pattern-ul de ecran cu header si ScrollView

## Dependente

- **Depinde de:** architect (ruta + tipuri) si backend (query DB)
- **Daca backend nu e gata:** poti crea ecranul cu date mock hardcodate si inlocui cu query-ul real dupa

## Ce trebuie sa implementezi

### 1. Creeaza fisierul `src/screens/MediaFilesScreen.tsx`

```typescript
// Structura de baza:
import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, FlatList,
  Image, StatusBar, ActivityIndicator, Dimensions, Share, Linking,
} from 'react-native';
import { useTranslation } from 'react-i18next';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Ionicons from 'react-native-vector-icons/Ionicons';
import Database from '../storage/Database';
import { useTheme } from '../utils/ThemeContext';
import type { MediaItem, MediaCategory } from '../utils/types';
```

### 2. Header (identic ca in ContactProfileScreen)

```tsx
<View style={[styles.header, { backgroundColor: C.headerBg, borderBottomColor: C.border, paddingTop: insets.top + 16 }]}>
  <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backButton}
    accessibilityLabel={t('common.back')} accessibilityRole="button">
    <Text style={[styles.backText, { color: C.accent }]}>{`\u2190 ${t('common.back')}`}</Text>
  </TouchableOpacity>
  <Text style={[styles.headerTitle, { color: C.text }]}>{t('mediaFiles.title')}</Text>
  <View style={{ width: 80 }} />
</View>
```

### 3. Tab Bar — 4 tab-uri

Design: pastile orizontale, tab-ul activ are fundal `C.accent` cu text alb, restul au fundal transparent cu text `C.textSecondary`.

```tsx
const TABS: { key: MediaCategory; icon: string; labelKey: string }[] = [
  { key: 'photos', icon: 'images-outline', labelKey: 'mediaFiles.photos' },
  { key: 'videos', icon: 'videocam-outline', labelKey: 'mediaFiles.videos' },
  { key: 'audio',  icon: 'musical-notes-outline', labelKey: 'mediaFiles.audio' },
  { key: 'files',  icon: 'document-outline', labelKey: 'mediaFiles.files' },
];
```

Render tab bar:
```tsx
<View style={[styles.tabBar, { backgroundColor: C.surface, borderBottomColor: C.border }]}>
  {TABS.map(tab => {
    const isActive = activeTab === tab.key;
    const count = counts[tab.key];
    return (
      <TouchableOpacity
        key={tab.key}
        style={[styles.tab, isActive && { backgroundColor: C.accent }]}
        onPress={() => setActiveTab(tab.key)}
        activeOpacity={0.7}
        accessibilityLabel={t(tab.labelKey)}
        accessibilityRole="tab"
        accessibilityState={{ selected: isActive }}
      >
        <Ionicons name={tab.icon} size={16} color={isActive ? '#fff' : C.textSecondary} />
        <Text style={[styles.tabText, { color: isActive ? '#fff' : C.textSecondary }]}>
          {t(tab.labelKey)}{count > 0 ? ` (${count})` : ''}
        </Text>
      </TouchableOpacity>
    );
  })}
</View>
```

Stiluri tab bar:
```typescript
tabBar: {
  flexDirection: 'row',
  paddingHorizontal: 12,
  paddingVertical: 8,
  gap: 6,
  borderBottomWidth: 1,
},
tab: {
  flex: 1,
  flexDirection: 'row',
  alignItems: 'center',
  justifyContent: 'center',
  paddingVertical: 8,
  paddingHorizontal: 6,
  borderRadius: 20,
  gap: 4,
},
tabText: {
  fontSize: 11,
  fontWeight: '600',
},
```

### 4. Grid View (Photos & Videos tabs)

Foloseste `FlatList` cu `numColumns={3}`:

```tsx
const SCREEN_WIDTH = Dimensions.get('window').width;
const GRID_GAP = 2;
const NUM_COLUMNS = 3;
const ITEM_SIZE = (SCREEN_WIDTH - GRID_GAP * (NUM_COLUMNS - 1)) / NUM_COLUMNS;

const renderGridItem = ({ item }: { item: MediaItem }) => (
  <TouchableOpacity
    style={[styles.gridItem, { width: ITEM_SIZE, height: ITEM_SIZE }]}
    onPress={() => handleMediaPress(item)}
    activeOpacity={0.8}
    accessibilityLabel={
      item.contentType === 'image'
        ? t('mediaFiles.photoItem')
        : t('mediaFiles.videoItem')
    }
    accessibilityRole="image"
  >
    {item.contentType === 'image' && item.imageUri ? (
      <Image source={{ uri: item.imageUri }} style={styles.gridImage} resizeMode="cover" />
    ) : item.contentType === 'video' && item.videoUri ? (
      <View style={[styles.gridImage, { backgroundColor: C.surfaceLight, justifyContent: 'center', alignItems: 'center' }]}>
        <Ionicons name="play-circle" size={36} color="rgba(255,255,255,0.9)" />
        <Text style={styles.videoOverlayText}>{t('mediaFiles.video')}</Text>
      </View>
    ) : null}
    {/* Data in coltul din dreapta-jos */}
    <View style={styles.gridDateBadge}>
      <Text style={styles.gridDateText}>{formatDate(item.timestamp)}</Text>
    </View>
  </TouchableOpacity>
);
```

Stiluri grid:
```typescript
gridItem: {
  position: 'relative',
  marginRight: GRID_GAP,
  marginBottom: GRID_GAP,
},
gridImage: {
  width: '100%',
  height: '100%',
},
gridDateBadge: {
  position: 'absolute',
  bottom: 4,
  right: 4,
  backgroundColor: 'rgba(0,0,0,0.5)',
  borderRadius: 4,
  paddingHorizontal: 4,
  paddingVertical: 1,
},
gridDateText: {
  color: '#fff',
  fontSize: 9,
  fontWeight: '500',
},
videoOverlayText: {
  color: 'rgba(255,255,255,0.8)',
  fontSize: 10,
  fontWeight: '600',
  marginTop: 4,
},
```

### 5. List View (Audio tab)

```tsx
const renderAudioItem = ({ item }: { item: MediaItem }) => {
  const durationStr = item.audioDuration
    ? `${Math.floor(item.audioDuration / 60)}:${String(Math.floor(item.audioDuration % 60)).padStart(2, '0')}`
    : '--:--';

  return (
    <TouchableOpacity
      style={[styles.listItem, { backgroundColor: C.surface, borderColor: C.border }]}
      onPress={() => handleMediaPress(item)}
      activeOpacity={0.7}
      accessibilityLabel={`${t('mediaFiles.voiceMessage')} ${durationStr}`}
      accessibilityRole="button"
    >
      <View style={[styles.listIcon, { backgroundColor: `${C.accent}1A` }]}>
        <Ionicons name="mic-outline" size={22} color={C.accent} />
      </View>
      <View style={{ flex: 1, marginLeft: 12 }}>
        <Text style={[styles.listTitle, { color: C.text }]}>{t('mediaFiles.voiceMessage')}</Text>
        <Text style={[styles.listSubtitle, { color: C.textMuted }]}>
          {durationStr} \u00B7 {formatDate(item.timestamp)}
        </Text>
      </View>
      <Ionicons name="play-outline" size={20} color={C.accent} />
    </TouchableOpacity>
  );
};
```

### 6. List View (Files tab)

```tsx
const renderFileItem = ({ item }: { item: MediaItem }) => {
  const ext = (item.fileName || '').split('.').pop()?.toLowerCase() || '';
  const { icon, color, label } = getFileTypeInfo(ext);
  const sizeStr = formatFileSize(item.fileSize || 0);

  return (
    <TouchableOpacity
      style={[styles.listItem, { backgroundColor: C.surface, borderColor: C.border }]}
      onPress={() => handleMediaPress(item)}
      activeOpacity={0.7}
      accessibilityLabel={`${item.fileName || t('chat.file')} ${sizeStr}`}
      accessibilityRole="button"
    >
      <View style={[styles.listIcon, { backgroundColor: `${color}20` }]}>
        <Ionicons name={icon} size={22} color={color} />
        <Text style={{ fontSize: 8, color, fontWeight: '700', marginTop: 1 }}>{label}</Text>
      </View>
      <View style={{ flex: 1, marginLeft: 12 }}>
        <Text style={[styles.listTitle, { color: C.text }]} numberOfLines={1}>
          {item.fileName || t('chat.file')}
        </Text>
        <Text style={[styles.listSubtitle, { color: C.textMuted }]}>
          {sizeStr} \u00B7 {formatDate(item.timestamp)}
        </Text>
      </View>
      <Ionicons name="share-outline" size={18} color={C.textMuted} />
    </TouchableOpacity>
  );
};
```

**Functia helper `getFileTypeInfo()`** — identica cu logica din ChatScreen.tsx (liniile 431-443):

```typescript
const getFileTypeInfo = (ext: string): { icon: string; color: string; label: string } => {
  if (['pdf'].includes(ext)) return { icon: 'document-text-outline', color: '#E53935', label: 'PDF' };
  if (['doc', 'docx'].includes(ext)) return { icon: 'document-text-outline', color: '#1976D2', label: 'Word' };
  if (['xls', 'xlsx'].includes(ext)) return { icon: 'grid-outline', color: '#2E7D32', label: 'Excel' };
  if (['ppt', 'pptx'].includes(ext)) return { icon: 'easel-outline', color: '#E65100', label: 'PPT' };
  if (['mp3', 'wav', 'aac', 'ogg', 'm4a', 'flac'].includes(ext)) return { icon: 'musical-notes-outline', color: '#8E24AA', label: 'Audio' };
  if (['mp4', 'mov', 'avi', 'mkv', 'webm'].includes(ext)) return { icon: 'videocam-outline', color: '#00897B', label: 'Video' };
  if (['zip', 'rar', '7z', 'tar', 'gz'].includes(ext)) return { icon: 'archive-outline', color: '#6D4C41', label: 'ZIP' };
  if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp'].includes(ext)) return { icon: 'image-outline', color: '#FB8C00', label: 'Image' };
  if (['txt', 'csv', 'json', 'xml', 'html', 'css', 'js'].includes(ext)) return { icon: 'code-outline', color: '#546E7A', label: 'Text' };
  return { icon: 'document-outline', color: '#78909C', label: 'File' };
};
```

### 7. Helper functions

```typescript
const formatDate = (timestamp: number): string => {
  const d = new Date(timestamp);
  const now = new Date();
  if (d.toDateString() === now.toDateString()) {
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  if (d.toDateString() === yesterday.toDateString()) {
    return t('callLog.yesterday');
  }
  return d.toLocaleDateString([], { day: 'numeric', month: 'short' });
};

const formatFileSize = (bytes: number): string => {
  if (bytes > 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  if (bytes > 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${bytes} B`;
};
```

### 8. Empty State

Cand nu exista media pentru tab-ul selectat:

```tsx
const renderEmptyState = () => (
  <View style={styles.emptyState}>
    <Ionicons
      name={
        activeTab === 'photos' ? 'images-outline'
        : activeTab === 'videos' ? 'videocam-outline'
        : activeTab === 'audio' ? 'mic-outline'
        : 'document-outline'
      }
      size={48}
      color={C.textMuted}
    />
    <Text style={[styles.emptyText, { color: C.textMuted }]}>
      {t('mediaFiles.noMedia')}
    </Text>
  </View>
);
```

### 9. Media Press Handlers

```typescript
const handleMediaPress = async (item: MediaItem) => {
  switch (item.contentType) {
    case 'image':
      if (item.imageUri) {
        // Deschide imaginea — simplu, folosind Linking
        try {
          await Linking.openURL(item.imageUri.startsWith('file://') ? item.imageUri : `file://${item.imageUri}`);
        } catch {
          // Fallback: Share sheet
          try { await Share.share({ url: item.imageUri }); } catch {}
        }
      }
      break;
    case 'video':
      if (item.videoUri) {
        try { await Linking.openURL(item.videoUri); } catch {}
      }
      break;
    case 'audio':
      if (item.audioUri) {
        try { await Linking.openURL(item.audioUri.startsWith('file://') ? item.audioUri : `file://${item.audioUri}`); } catch {}
      }
      break;
    case 'file':
      if (item.fileUri) {
        try {
          await Share.share({ url: item.fileUri.startsWith('file://') ? item.fileUri : `file://${item.fileUri}`, title: item.fileName });
        } catch {}
      }
      break;
  }
};
```

### 10. State & Effects

```typescript
const [activeTab, setActiveTab] = useState<MediaCategory>('photos');
const [items, setItems] = useState<MediaItem[]>([]);
const [counts, setCounts] = useState<Record<MediaCategory, number>>({ photos: 0, videos: 0, audio: 0, files: 0 });
const [loading, setLoading] = useState(true);

useEffect(() => {
  // Load counts o singura data
  Database.getMediaCountByContact(contactId).then(setCounts).catch(console.warn);
}, [contactId]);

useEffect(() => {
  setLoading(true);
  Database.getMediaByContact(contactId, activeTab)
    .then(setItems)
    .catch(console.warn)
    .finally(() => setLoading(false));
}, [contactId, activeTab]);
```

### 11. Render principal

```tsx
return (
  <View style={[styles.container, { backgroundColor: C.background }]}>
    <StatusBar barStyle={C.statusBarStyle} />
    {/* Header */}
    {/* Tab Bar */}
    {loading ? (
      <ActivityIndicator size="large" color={C.accent} style={{ marginTop: 40 }} />
    ) : items.length === 0 ? (
      renderEmptyState()
    ) : (activeTab === 'photos' || activeTab === 'videos') ? (
      <FlatList
        data={items}
        renderItem={renderGridItem}
        keyExtractor={item => item.id}
        numColumns={NUM_COLUMNS}
        contentContainerStyle={{ paddingTop: GRID_GAP }}
      />
    ) : (
      <FlatList
        data={items}
        renderItem={activeTab === 'audio' ? renderAudioItem : renderFileItem}
        keyExtractor={item => item.id}
        contentContainerStyle={{ padding: 12, gap: 8 }}
      />
    )}
  </View>
);
```

### 12. Stiluri lista

```typescript
listItem: {
  flexDirection: 'row',
  alignItems: 'center',
  padding: 12,
  borderRadius: 12,
  borderWidth: 1,
},
listIcon: {
  width: 44,
  height: 44,
  borderRadius: 10,
  alignItems: 'center',
  justifyContent: 'center',
},
listTitle: {
  fontSize: 14,
  fontWeight: '600',
},
listSubtitle: {
  fontSize: 11,
  marginTop: 2,
},
emptyState: {
  flex: 1,
  alignItems: 'center',
  justifyContent: 'center',
  gap: 12,
},
emptyText: {
  fontSize: 14,
},
```

---

## Modificari in fisiere existente

### A. `src/screens/ContactProfileScreen.tsx` — Adauga butonul "Media & Files"

Dupa blocul `<View style={[styles.infoStrip, ...]}> ... </View>` (dupa linia ~399), adauga:

```tsx
{/* Media & Files Button */}
<TouchableOpacity
  style={[styles.settingRow, { backgroundColor: C.surface, borderColor: C.border, marginBottom: 8 }]}
  onPress={() => navigation.navigate('MediaFiles', { contactId })}
  activeOpacity={0.7}
  accessibilityLabel={t('contactProfile.mediaFiles')}
  accessibilityRole="button"
>
  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10, flex: 1 }}>
    <Ionicons name="images-outline" size={20} color={C.accent} />
    <View>
      <Text style={[styles.settingLabel, { color: C.text }]}>{t('contactProfile.mediaFiles')}</Text>
      <Text style={[styles.settingDesc, { color: C.textSecondary }]}>{t('contactProfile.mediaFilesDesc')}</Text>
    </View>
  </View>
  <Ionicons name="chevron-forward" size={18} color={C.textMuted} />
</TouchableOpacity>
```

### B. `src/navigation/AppNavigator.tsx` — Adauga ruta

1. Adauga import:
```typescript
import MediaFilesScreen from '../screens/MediaFilesScreen';
```

2. Adauga in `RootStackParamList`:
```typescript
MediaFiles: { contactId: string };
```

3. Adauga Screen (dupa ContactProfile, linia 84):
```tsx
<Stack.Screen name="MediaFiles" component={MediaFilesScreen} />
```

### C. Chei i18n noi — 4 limbi

#### `src/i18n/locales/en.json` — adauga sectiunea `mediaFiles`:

```json
"mediaFiles": {
  "title": "Media & Files",
  "photos": "Photos",
  "videos": "Videos",
  "audio": "Audio",
  "files": "Files",
  "noMedia": "No media yet",
  "voiceMessage": "Voice message",
  "photoItem": "Photo",
  "videoItem": "Video",
  "video": "Video"
}
```

Si in sectiunea `contactProfile` existenta, adauga:
```json
"mediaFiles": "Media & Files",
"mediaFilesDesc": "Photos, videos, audio, and documents"
```

#### `src/i18n/locales/ro.json`:

```json
"mediaFiles": {
  "title": "Media si fisiere",
  "photos": "Poze",
  "videos": "Video",
  "audio": "Audio",
  "files": "Fisiere",
  "noMedia": "Nicio media inca",
  "voiceMessage": "Mesaj vocal",
  "photoItem": "Poza",
  "videoItem": "Video",
  "video": "Video"
}
```

Si in `contactProfile`:
```json
"mediaFiles": "Media si fisiere",
"mediaFilesDesc": "Poze, video, audio si documente"
```

#### `src/i18n/locales/ru.json`:

```json
"mediaFiles": {
  "title": "Медиа и файлы",
  "photos": "Фото",
  "videos": "Видео",
  "audio": "Аудио",
  "files": "Файлы",
  "noMedia": "Пока нет медиа",
  "voiceMessage": "Голосовое сообщение",
  "photoItem": "Фото",
  "videoItem": "Видео",
  "video": "Видео"
}
```

Si in `contactProfile`:
```json
"mediaFiles": "Медиа и файлы",
"mediaFilesDesc": "Фото, видео, аудио и документы"
```

#### `src/i18n/locales/fr.json`:

```json
"mediaFiles": {
  "title": "Medias et fichiers",
  "photos": "Photos",
  "videos": "Videos",
  "audio": "Audio",
  "files": "Fichiers",
  "noMedia": "Aucun media",
  "voiceMessage": "Message vocal",
  "photoItem": "Photo",
  "videoItem": "Video",
  "video": "Video"
}
```

Si in `contactProfile`:
```json
"mediaFiles": "Medias et fichiers",
"mediaFilesDesc": "Photos, videos, audio et documents"
```

---

## Criterii de succes

1. `MediaFilesScreen.tsx` creat si functional
2. 4 tab-uri functionale: Photos, Videos, Audio, Files
3. Grid 3 coloane pentru Photos si Videos
4. Lista cu icon + info pentru Audio si Files
5. Empty state cand nu exista media
6. Buton pe ContactProfileScreen care deschide MediaFilesScreen
7. Ruta adaugata in AppNavigator.tsx
8. Chei i18n adaugate in toate 4 limbile
9. Accessibility labels pe toate elementele interactive
10. Tema Light + Dark functionala
11. `npx tsc --noEmit` fara erori

## Verificare

```bash
cd /Users/ruslanconstantinovici/QRChat

# 1. TypeScript check
npx tsc --noEmit 2>&1 | head -20

# 2. Verifica fisierul nou
ls -la src/screens/MediaFilesScreen.tsx

# 3. Verifica navigatia
grep "MediaFiles" src/navigation/AppNavigator.tsx

# 4. Verifica i18n
grep "mediaFiles" src/i18n/locales/en.json src/i18n/locales/ru.json src/i18n/locales/ro.json src/i18n/locales/fr.json

# 5. Verifica butonul pe ContactProfile
grep "MediaFiles\|mediaFiles" src/screens/ContactProfileScreen.tsx

# 6. Deploy pe simulator
npx react-native run-ios --simulator="iPhone 16e"
```

## IMPORTANT: Ce sa NU faci

- NU modifica ChatScreen.tsx
- NU adauga pachete npm noi (foloseste doar ce exista deja)
- NU schimba stilul temelor existente
- NU modifica Database.ts (asta e treaba backend-engineer)
- NU sterge cod existent din ContactProfileScreen — doar adauga butonul
- NU adauga funcționalitate in plus (nu e nevoie de search, sort, multi-select, etc.)
