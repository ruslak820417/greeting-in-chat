# Prompt: Architect — Media Files Screen (Specificatie Tehnica)

## Rol
Esti **architect** pentru proiectul QRChat. Sarcina ta este sa definesti specificatia tehnica completa pentru noul ecran **MediaFilesScreen** — un ecran care afiseaza toate fisierele media dintr-o conversatie cu un contact.

## Context
- **Proiect:** `/Users/ruslanconstantinovici/QRChat`
- **Tech stack:** React Native 0.84, TypeScript 5.8, SQLite (op-sqlite), React Navigation 6
- **Versiune:** 4.0.0

## Fisiere de citit INAINTE de a incepe

1. `src/utils/types.ts` — tipurile Message, Contact, Conversation
2. `src/storage/Database.ts` — schema tabelei `messages`, metodele existente `getMessages()`, `getMessagesPaginated()`, `getCallMessages()`, `rowToMessage()`
3. `src/navigation/AppNavigator.tsx` — RootStackParamList, Stack.Screen-uri existente
4. `src/screens/ContactProfileScreen.tsx` — ecranul din care se va naviga spre MediaFiles
5. `src/screens/ChatScreen.tsx` — liniile 420-620 (rendering file/video/image/audio) pentru a intelege structura content-ului per tip

## Ce trebuie sa faci

### 1. Defineste tipul `MediaItem` in `src/utils/types.ts`

Adauga la sfarsitul fisierului:

```typescript
export type MediaCategory = 'photos' | 'videos' | 'audio' | 'files';

export interface MediaItem {
  id: string;                    // message.id
  contentType: Message['contentType']; // 'image' | 'video' | 'audio' | 'file'
  timestamp: number;             // message.timestamp
  senderId: string;              // message.senderId
  senderName?: string;           // message.senderName
  // Image
  imageUri?: string;             // din message.content (URI direct) sau message.imageUri
  // Video
  videoUri?: string;             // din message.content (URI direct)
  // Audio
  audioUri?: string;             // message.audioUri
  audioDuration?: number;        // message.audioDuration (secunde)
  // File
  fileUri?: string;              // din JSON.parse(message.content).uri sau message.fileUri
  fileName?: string;             // din JSON.parse(message.content).name sau message.fileName
  fileSize?: number;             // din JSON.parse(message.content).size sau message.fileSize
  mimeType?: string;             // message.mimeType
}
```

### 2. Defineste semnatura query-ului DB in `src/storage/Database.ts`

Adauga metoda `getMediaByContact()` in clasa Database. Specificatia:

```typescript
/**
 * Returneaza toate mesajele media din conversatia cu un contact.
 * @param conversationId - ID-ul contactului (= conversationId in messages table)
 * @param category - optional: filtreaza pe categorie ('photos' | 'videos' | 'audio' | 'files')
 * @returns Array de MediaItem, sortate descrescator dupa timestamp (cele mai noi primele)
 */
async getMediaByContact(
  conversationId: string,
  category?: MediaCategory
): Promise<MediaItem[]>
```

**Logica de filtrare SQL:**
- `photos`: `contentType = 'image'`
- `videos`: `contentType = 'video'`
- `audio`: `contentType = 'audio'`
- `files`: `contentType = 'file'`
- fara categorie: `contentType IN ('image', 'video', 'audio', 'file')` (exclude 'text' si 'call')

**Mapare din row la MediaItem** (in functie de contentType):
- **image**: `imageUri = row.content` (content-ul imaginii E chiar URI-ul). Daca `row.imageUri` exista, foloseste-l preferential.
- **video**: `videoUri = row.content`
- **audio**: `audioUri = row.audioUri`, `audioDuration = row.audioDuration`
- **file**: `fileUri = row.fileUri`, `fileName = row.fileName`, `fileSize = row.fileSize`. Daca `fileUri` e null, incearca `JSON.parse(row.content)` pentru `{name, size, uri}`.

### 3. Adauga ruta in navigatie (`src/navigation/AppNavigator.tsx`)

Adauga in `RootStackParamList`:
```typescript
MediaFiles: { contactId: string };
```

Adauga import si Screen:
```typescript
import MediaFilesScreen from '../screens/MediaFilesScreen';
// ...
<Stack.Screen name="MediaFiles" component={MediaFilesScreen} />
```

Pozitia: dupa `<Stack.Screen name="ContactProfile" .../>` (linia 84).

### 4. Defineste structura ecranului MediaFilesScreen

Ecranul va avea urmatoarea structura:

```
+-----------------------------------------------+
|  <- Back           Media & Files               |
+-----------------------------------------------+
| [Photos] [Videos] [Audio] [Files]   <- tabs    |
+-----------------------------------------------+
|                                                 |
|  Continut tab-ului selectat:                    |
|                                                 |
|  Photos/Videos: Grid 3 coloane (ca galerie)     |
|  Audio: Lista verticala cu player inline        |
|  Files: Lista verticala cu icon + info          |
|                                                 |
|  Empty state daca nu exista media               |
+-----------------------------------------------+
```

**Props:** `route.params.contactId: string`

**State:**
- `activeTab: MediaCategory` (default: 'photos')
- `items: MediaItem[]`
- `loading: boolean`

**Comportament:**
- La mount si la schimbarea tab-ului, apeleaza `Database.getMediaByContact(contactId, activeTab)`
- Photos tab: `FlatList` cu `numColumns={3}`, imagini patrate cu `gap: 2px`
- Videos tab: `FlatList` cu `numColumns={3}`, thumbnail cu icon play overlay
- Audio tab: `FlatList` simpla, fiecare item: icon, durata, data
- Files tab: `FlatList` simpla, fiecare item: icon tip fisier, nume, dimensiune, data

**Interactiuni:**
- Tap pe imagine: deschide Photo Viewer (sau navigheaza la ChatScreen la acel mesaj — mai simplu: deschide imaginea cu `Linking.openURL`)
- Tap pe video: `Linking.openURL(videoUri)`
- Tap pe audio: play inline (folosind `@react-native-community/audio-toolkit` — deja in proiect)
- Tap pe fisier: `Share.share({ url: fileUri })` sau `Linking.openURL(fileUri)`

### 5. Adauga butonul pe ContactProfileScreen

In `src/screens/ContactProfileScreen.tsx`, dupa blocul `infoStrip` (linia ~399) si inainte de sectiunea Notifications (linia ~402), adauga un buton:

```tsx
{/* Media & Files */}
<TouchableOpacity
  style={[styles.settingRow, { backgroundColor: C.surface, borderColor: C.border }]}
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

## Criterii de succes

1. Tipul `MediaItem` exportat din `types.ts`
2. `MediaCategory` exportat din `types.ts`
3. Semnatura `getMediaByContact()` adaugata in `Database.ts` cu implementare completa
4. Ruta `MediaFiles` adaugata in `AppNavigator.tsx` (tip + Screen)
5. Specificatia tehnica scrisa ca document in `agent-runtime/outputs/media-files-spec.md`
6. `npx tsc --noEmit` trece fara erori noi

## Dependente

- **Blocheaza:** backend-engineer (trebuie sa implementeze query-ul DB) si frontend-engineer (trebuie sa construiasca UI-ul)
- **Nu depinde de nimeni** — architect lucreaza primul

## Verificare

```bash
cd /Users/ruslanconstantinovici/QRChat
npx tsc --noEmit 2>&1 | head -20
```

## Referinta design (din mesagerii populare)

### WhatsApp — "Media, Links, and Docs"
- 3 tab-uri: Media | Links | Docs
- Grid 4 coloane pentru media (poze + video amestecate)
- Video-urile au icon play + durata in colt
- Documentele: lista cu icon, nume, data, dimensiune

### Telegram — "Shared Media"
- Tab-uri: Media | Files | Links | Music | Voice
- Grid 3 coloane pentru Media
- Fisierele au icon colorat pe tip (PDF rosu, ZIP maro, etc.)
- Audio/Voice au player inline cu waveform

### Signal — "All Media"
- Grid simplu cu poze si video
- Nu are tabs separate — totul intr-un grid
- Simplu si minimal
