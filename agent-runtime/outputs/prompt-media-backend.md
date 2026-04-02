# Prompt: Backend/Architect — Database Query pentru Media Files

## Rol
Esti **backend-engineer** (sau **architect**) pentru proiectul QRChat. Sarcina ta este sa implementezi query-ul de baza de date care returneaza toate fisierele media dintr-o conversatie cu un contact.

## Context
- **Proiect:** `/Users/ruslanconstantinovici/QRChat`
- **Fisier principal:** `src/storage/Database.ts`
- **DB:** SQLite via `@op-engineering/op-sqlite`, criptat cu SQLCipher
- **Tipuri:** `src/utils/types.ts`

## Fisiere de citit OBLIGATORIU

1. `src/storage/Database.ts` — INTREG fisierul, in special:
   - Schema tabelei `messages` (liniile 149-180): campurile `contentType`, `imageUri`, `fileUri`, `fileName`, `fileSize`, `audioUri`, `audioDuration`, `mimeType`
   - Metoda `rowToMessage()` (liniile 513-558): cum se mapeaza un row SQLite la un obiect Message
   - Metodele `getMessages()` si `getMessagesPaginated()` (liniile 946-964): pattern-ul de query
   - Metoda `getCallMessages()` (liniile 973-979): exemplu de filtrare pe `contentType`
   - Indexul `idx_messages_contentType` (linia 252): exista doar pentru `contentType = 'call'`
2. `src/utils/types.ts` — tipurile `Message`, `MediaItem`, `MediaCategory` (ultimele 2 vor fi adaugate de architect)

## Schema tabelei `messages` (referinta rapida)

```sql
CREATE TABLE messages (
  id TEXT PRIMARY KEY,
  conversationId TEXT NOT NULL,
  senderId TEXT NOT NULL,
  senderName TEXT,
  content TEXT,
  contentType TEXT DEFAULT 'text',  -- 'text' | 'image' | 'video' | 'file' | 'audio' | 'call'
  timestamp INTEGER NOT NULL,
  -- ... alte campuri ...
  audioUri TEXT,
  audioDuration REAL,
  imageUri TEXT,
  fileUri TEXT,
  fileName TEXT,
  fileSize INTEGER,
  mimeType TEXT
);
```

## Structura `content` per contentType

Aceasta este critica — trebuie sa intelegi cum se stocheaza datele in `content`:

| contentType | content field | Campuri DB dedicate |
|-------------|--------------|---------------------|
| `image` | URI direct al imaginii (ex: `file:///...jpg`) | `imageUri` (uneori setat) |
| `video` | URI direct al video-ului (ex: `file:///...mp4`) | — |
| `audio` | Text descriptiv sau gol | `audioUri`, `audioDuration` |
| `file` | JSON: `{"name":"doc.pdf","size":1234,"uri":"file:///..."}` | `fileUri`, `fileName`, `fileSize` |
| `text` | Text simplu | — |
| `call` | JSON cu info apel | — |

## Ce trebuie sa implementezi

### 1. Adauga tipurile in `src/utils/types.ts` (daca nu sunt deja adaugate de architect)

La sfarsitul fisierului, adauga:

```typescript
export type MediaCategory = 'photos' | 'videos' | 'audio' | 'files';

export interface MediaItem {
  id: string;
  contentType: Message['contentType'];
  timestamp: number;
  senderId: string;
  senderName?: string;
  // Image
  imageUri?: string;
  // Video
  videoUri?: string;
  // Audio
  audioUri?: string;
  audioDuration?: number;
  // File
  fileUri?: string;
  fileName?: string;
  fileSize?: number;
  mimeType?: string;
}
```

### 2. Adauga index SQL in `Database.ts`

In metoda `initSQLite()`, dupa indexul `idx_messages_contentType` (linia ~254), adauga:

```typescript
await this.db.execute(`
  CREATE INDEX IF NOT EXISTS idx_messages_media
  ON messages(conversationId, contentType, timestamp)
  WHERE contentType IN ('image', 'video', 'audio', 'file');
`);
```

Acest index partial optimizeaza query-urile media per conversatie.

### 3. Implementeaza `getMediaByContact()` in clasa `Database`

Adauga dupa metoda `getCallMessages()` (dupa linia ~979):

```typescript
/**
 * Returneaza toate fisierele media dintr-o conversatie.
 * Exclude mesajele text si call.
 */
async getMediaByContact(
  conversationId: string,
  category?: MediaCategory
): Promise<MediaItem[]> {
  const db = await this.ensureSQLite();

  let contentTypeFilter: string;
  let params: any[];

  if (category) {
    const typeMap: Record<MediaCategory, string> = {
      photos: 'image',
      videos: 'video',
      audio: 'audio',
      files: 'file',
    };
    contentTypeFilter = 'AND contentType = ?';
    params = [conversationId, typeMap[category]];
  } else {
    contentTypeFilter = "AND contentType IN ('image', 'video', 'audio', 'file')";
    params = [conversationId];
  }

  const result = await db.execute(
    `SELECT * FROM messages
     WHERE conversationId = ? ${contentTypeFilter}
     ORDER BY timestamp DESC`,
    params
  );

  return (result.rows ?? []).map((row: any) => this.rowToMediaItem(row));
}

/**
 * Returneaza numarul total de fisiere media per categorie.
 * Util pentru afisarea badge-urilor pe tab-uri.
 */
async getMediaCountByContact(
  conversationId: string
): Promise<Record<MediaCategory, number>> {
  const db = await this.ensureSQLite();

  const result = await db.execute(
    `SELECT contentType, COUNT(*) as cnt FROM messages
     WHERE conversationId = ?
     AND contentType IN ('image', 'video', 'audio', 'file')
     GROUP BY contentType`,
    [conversationId]
  );

  const counts: Record<MediaCategory, number> = {
    photos: 0,
    videos: 0,
    audio: 0,
    files: 0,
  };

  const reverseMap: Record<string, MediaCategory> = {
    image: 'photos',
    video: 'videos',
    audio: 'audio',
    file: 'files',
  };

  for (const row of (result.rows ?? []) as any[]) {
    const cat = reverseMap[row.contentType];
    if (cat) counts[cat] = row.cnt;
  }

  return counts;
}
```

### 4. Implementeaza metoda privata `rowToMediaItem()`

Adauga ca metoda privata in clasa Database (langa `rowToMessage()`):

```typescript
/**
 * Converteste un row SQLite intr-un MediaItem.
 * Extrage URI-urile din campurile dedicate sau din content JSON.
 */
private rowToMediaItem(row: Record<string, any>): MediaItem {
  const item: MediaItem = {
    id: row.id,
    contentType: row.contentType ?? 'file',
    timestamp: row.timestamp,
    senderId: row.senderId,
  };

  if (row.senderName != null) item.senderName = row.senderName;
  if (row.mimeType != null) item.mimeType = row.mimeType;

  switch (row.contentType) {
    case 'image':
      // Imaginile stocheaza URI-ul direct in content
      item.imageUri = row.imageUri || row.content || undefined;
      break;

    case 'video':
      // Video-urile stocheaza URI-ul direct in content
      item.videoUri = row.content || undefined;
      break;

    case 'audio':
      item.audioUri = row.audioUri || undefined;
      item.audioDuration = row.audioDuration || undefined;
      break;

    case 'file':
      // Fisierele au campuri dedicate SAU JSON in content
      item.fileUri = row.fileUri || undefined;
      item.fileName = row.fileName || undefined;
      item.fileSize = row.fileSize || undefined;

      // Fallback: parseaza content JSON daca campurile dedicate lipsesc
      if (!item.fileUri || !item.fileName) {
        try {
          const parsed = JSON.parse(row.content);
          if (!item.fileUri && parsed.uri) item.fileUri = parsed.uri;
          if (!item.fileName && parsed.name) item.fileName = parsed.name;
          if (!item.fileSize && parsed.size) item.fileSize = parsed.size;
        } catch {
          // content nu e JSON valid — ignora
        }
      }
      break;
  }

  return item;
}
```

## Importuri necesare

In `src/storage/Database.ts`, actualizeaza importul din types.ts:

```typescript
import type { UserProfile, Contact, ContactRequest, Message, Conversation, Group, MediaItem, MediaCategory } from '../utils/types';
```

**ATENTIE:** Verifica ca `MediaItem` si `MediaCategory` sunt exportate din `types.ts` inainte de a importa. Daca architect-ul nu le-a adaugat inca, adauga-le tu (vezi sectiunea 1).

## Criterii de succes

1. Tipurile `MediaItem` si `MediaCategory` exista in `types.ts`
2. Indexul `idx_messages_media` se creeaza la init
3. `getMediaByContact(conversationId, category?)` returneaza corect `MediaItem[]`
4. `getMediaCountByContact(conversationId)` returneaza counts per categorie
5. `rowToMediaItem()` mapeaza corect pentru toate cele 4 tipuri de content
6. `npx tsc --noEmit` fara erori noi
7. Import-urile sunt corecte

## Dependente

- **Depinde de:** architect (tipurile trebuie sa fie definite — dar le poti adauga tu daca architect nu a terminat)
- **Blocheaza:** frontend-engineer (ecranul MediaFiles depinde de acest query)

## Verificare

```bash
cd /Users/ruslanconstantinovici/QRChat

# 1. Verifica TypeScript
npx tsc --noEmit 2>&1 | head -20

# 2. Verifica ca metodele exista
grep -n "getMediaByContact\|getMediaCountByContact\|rowToMediaItem" src/storage/Database.ts

# 3. Verifica ca tipurile exista
grep -n "MediaItem\|MediaCategory" src/utils/types.ts

# 4. Verifica indexul
grep -n "idx_messages_media" src/storage/Database.ts
```

## IMPORTANT: Ce sa NU faci

- NU modifica metode existente (`getMessages`, `rowToMessage`, etc.)
- NU schimba schema tabelei `messages` — doar adauga un index nou
- NU adauga pachete npm noi
- NU atinge fisiere din `src/screens/` — asta e treaba frontend-engineer
