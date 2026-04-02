# PROMPT 3 — MessagingService Refactorizare

**Agent tinta:** architect
**Proiect:** `/Users/ruslanconstantinovici/qrchatAndroid`
**Obiectiv:** Sparge MessagingService.ts (1731 linii, god class) in 5 module focusate + facade

---

## Context

`/Users/ruslanconstantinovici/qrchatAndroid/src/services/MessagingService.ts` este o clasa monolita de 1731 linii care contine TOATA logica de mesagerie: trimitere, receptie, chunk-uri fisiere, reactii, delivery tracking, editare, stergere, grupuri.

**ATENTIE:** Lucreaza pe copia `/Users/ruslanconstantinovici/qrchatAndroid`, NU pe `/Users/ruslanconstantinovici/QRChat`!

### Dependente existente (importuri):
```typescript
import WebRTCManager from '../network/WebRTCManager';
import SignalingClient from '../network/SignalingClient';
import KeyManager from '../crypto/KeyManager';
import Database from '../storage/Database';
import EventBus from '../utils/EventBus';
import NotificationService from './NotificationService';
import { navigate } from './NavigationService';
import { generateId, getRandomAvatarColor } from '../utils/helpers';
import type { Message, Contact, ContactRequest } from '../utils/types';
import { DoubleRatchet, RatchetMessage } from '../crypto/DoubleRatchet';
import RatchetStore from '../crypto/RatchetStore';
import nacl from 'tweetnacl';
import { decodeBase64, encodeBase64, encodeUTF8, decodeUTF8 } from 'tweetnacl-util';
import i18next from '../i18n';
```

### Stare interna partajata:
```typescript
// Callbacks (8 tipuri)
private onNewMessageCallbacks: NewMessageCallback[] = [];
private onTypingCallbacks: TypingCallback[] = [];
private onDeliveryCallbacks: DeliveryCallback[] = [];
private onConnectionCallbacks: ConnectionCallback[] = [];
private onReadCallbacks: ReadCallback[] = [];
private onDeleteMessageCallbacks: DeleteMessageCallback[] = [];
private onEditMessageCallbacks: EditMessageCallback[] = [];
private onReactionCallbacks: ReactionCallback[] = [];

// State
private initialized: boolean = false;
private handlersRegistered: boolean = false;
private processingIds: Set<string> = new Set();

// Chunk buffers
private fileChunkBuffers: Map<string, {...}> = new Map();
private fileChunkTimers: Map<string, ReturnType<typeof setTimeout>> = new Map();
```

### Metode publice (30+) — grupate pe domeniu:

**SEND (6 metode):**
- `sendTextMessage(contactId, text, selfDestructTimer?, replyTo?)` — linia 349
- `sendImageMessage(contactId, imageUri, fileName, selfDestructTimer?)` — linia 813
- `sendFileMessage(contactId, fileUri, fileName, fileSize, selfDestructTimer?)` — linia 880
- `sendAudioMessage(contactId, audioData, selfDestructTimer?, audioDuration?)` — linia 1120
- `forwardMessage(toContactId, originalMessage)` — linia 1237
- `sendGroupMessage(groupId, memberIds, text)` — linia 1272

**RECEIVE (handler intern, registrat in initialize()):**
- `handleIncomingMessage(...)` — implicit in registerHandlers(), ~linia 290
- Procesare file chunks, decryptare, salvare in DB, notificari

**CHUNKS (2 metode + state):**
- `handleFileRequest(contactId, requestData)` — linia 982
- Chunk buffer management (fileChunkBuffers, fileChunkTimers)
- Chunk assembly + timeout cleanup (300s)

**REACTIONS/EDIT/DELETE (3 metode):**
- `sendDeleteMessage(contactId, messageId)` — linia 1185
- `sendReaction(contactId, messageId, emoji, isRemove)` — linia 1207
- `sendEditMessage(contactId, messageId, newContent)` — linia 1320

**DELIVERY TRACKING (2 metode):**
- `sendReadReceipts(contactId)` — linia 462
- `sendTypingIndicator(contactId, isTyping)` — linia 444

**LIFECYCLE (3 metode):**
- `initialize()` — linia 51
- `connectToContact(contactId)` — linia 426
- `destroy()` — linia 2207

**CALLBACK MANAGEMENT (16 metode on/off):**
- `onNewMessage/offNewMessage`, `onTyping/offTyping`, `onDelivery/offDelivery`
- `onConnectionChange/offConnectionChange`, `onRead/offRead`
- `onDeleteMessage/offDeleteMessage`, `onEditMessage/offEditMessage`
- `onReaction/offReaction`

**UTILS (2 metode):**
- `decryptFileFromDisk(filePath)` — linia 785

---

## Sarcini — pas cu pas

### Pas 1 — Citeste MessagingService.ts complet

```
Citeste: /Users/ruslanconstantinovici/qrchatAndroid/src/services/MessagingService.ts
```

Identifica exact unde incepe si se termina fiecare grupa de functionalitate. Noteaza dependentele intre metode (ex: `sendFileMessage` apeleaza `handleFileRequest` intern?).

### Pas 2 — Creaza structura de directoare

```
src/services/messaging/
  MessageSender.ts
  MessageReceiver.ts
  ChunkManager.ts
  ReactionService.ts
  DeliveryTracker.ts
  types.ts          -- tipuri partajate (callback types, etc.)
  index.ts          -- re-export facade
```

### Pas 3 — Extrage tipurile in `types.ts`

Muta toate type-urile din MessagingService.ts intr-un fisier partajat:

```typescript
// src/services/messaging/types.ts
import type { Message, Contact, ContactRequest } from '../../utils/types';

export type NewMessageCallback = (message: Message) => void;
export type TypingCallback = (contactId: string, isTyping: boolean) => void;
export type DeliveryCallback = (messageId: string, deliveredAt?: number) => void;
export type ReadCallback = (messageIds: string[], readAt?: number) => void;
export type ConnectionCallback = (contactId: string, isConnected: boolean) => void;
export type DeleteMessageCallback = (messageId: string) => void;
export type EditMessageCallback = (messageId: string, newContent: string, editedAt?: number) => void;
export type ReactionCallback = (messageId: string, emoji: string, senderId: string, isRemove: boolean) => void;

// Context partajat pe care facade-ul il paseaza sub-serviciilor
export interface MessagingContext {
  getProcessingIds(): Set<string>;
  isInitialized(): boolean;
}
```

### Pas 4 — Extrage `MessageSender`

```typescript
// src/services/messaging/MessageSender.ts
import type { Message } from '../../utils/types';

export class MessageSender {
  // Primeste dependentele prin constructor (DI)
  constructor(
    private webrtc: typeof WebRTCManager,
    private signaling: typeof SignalingClient,
    private keyManager: typeof KeyManager,
    private db: typeof Database,
  ) {}

  async sendTextMessage(contactId: string, text: string, ...): Promise<Message | null> { ... }
  async sendImageMessage(contactId: string, imageUri: string, ...): Promise<Message | null> { ... }
  async sendFileMessage(contactId: string, fileUri: string, ...): Promise<Message | null> { ... }
  async sendAudioMessage(contactId: string, audioData: string, ...): Promise<Message | null> { ... }
  async forwardMessage(toContactId: string, originalMessage: Message): Promise<Message | null> { ... }
  async sendGroupMessage(groupId: string, memberIds: string[], text: string): Promise<Message | null> { ... }
}
```

**Regula:** MessageSender NU emite callback-uri direct — returneaza mesajul creat, iar facade-ul notifica callback-urile.

### Pas 5 — Extrage `MessageReceiver`

```typescript
// src/services/messaging/MessageReceiver.ts
export class MessageReceiver {
  constructor(
    private keyManager: typeof KeyManager,
    private db: typeof Database,
    private chunkManager: ChunkManager,  // dependenta de ChunkManager
    private onMessageReceived: (message: Message) => void,  // callback catre facade
  ) {}

  // registerHandlers() muta logica de inregistrare a handler-elor
  registerHandlers(webrtc: typeof WebRTCManager, signaling: typeof SignalingClient): void { ... }

  // Toata logica de procesare mesaje incoming
  private async processIncomingMessage(data: any, contactId: string): Promise<void> { ... }
  private async processIncomingFile(data: any, contactId: string): Promise<void> { ... }
}
```

### Pas 6 — Extrage `ChunkManager`

```typescript
// src/services/messaging/ChunkManager.ts
export class ChunkManager {
  private fileChunkBuffers: Map<string, { totalChunks: number; chunks: Map<number, string>; meta: any; startedAt: number }> = new Map();
  private fileChunkTimers: Map<string, ReturnType<typeof setTimeout>> = new Map();

  async handleFileRequest(contactId: string, requestData: any): Promise<void> { ... }
  addChunk(transferId: string, chunkIndex: number, data: string, meta: any): { complete: boolean; assembledData?: string } { ... }
  cleanup(): void { /* clear all timers and buffers */ }
}
```

### Pas 7 — Extrage `ReactionService`

```typescript
// src/services/messaging/ReactionService.ts
export class ReactionService {
  constructor(
    private webrtc: typeof WebRTCManager,
    private signaling: typeof SignalingClient,
    private db: typeof Database,
  ) {}

  async sendDeleteMessage(contactId: string, messageId: string): Promise<void> { ... }
  async sendReaction(contactId: string, messageId: string, emoji: string, isRemove?: boolean): Promise<void> { ... }
  async sendEditMessage(contactId: string, messageId: string, newContent: string): Promise<void> { ... }
}
```

### Pas 8 — Extrage `DeliveryTracker`

```typescript
// src/services/messaging/DeliveryTracker.ts
export class DeliveryTracker {
  constructor(
    private webrtc: typeof WebRTCManager,
    private signaling: typeof SignalingClient,
    private db: typeof Database,
  ) {}

  async sendReadReceipts(contactId: string): Promise<void> { ... }
  async sendTypingIndicator(contactId: string, isTyping: boolean): Promise<void> { ... }
}
```

### Pas 9 — Refactorizeaza `MessagingService` ca FACADE

```typescript
// src/services/MessagingService.ts — acum FACADE (< 200 linii)
import { MessageSender } from './messaging/MessageSender';
import { MessageReceiver } from './messaging/MessageReceiver';
import { ChunkManager } from './messaging/ChunkManager';
import { ReactionService } from './messaging/ReactionService';
import { DeliveryTracker } from './messaging/DeliveryTracker';
import type { NewMessageCallback, TypingCallback, ... } from './messaging/types';

class MessagingService {
  private sender!: MessageSender;
  private receiver!: MessageReceiver;
  private chunks!: ChunkManager;
  private reactions!: ReactionService;
  private delivery!: DeliveryTracker;

  // Callback arrays raman AICI (facade manages subscriptions)
  private onNewMessageCallbacks: NewMessageCallback[] = [];
  // ... restul callback-urilor

  async initialize() {
    this.chunks = new ChunkManager();
    this.sender = new MessageSender(WebRTCManager, SignalingClient, KeyManager, Database);
    this.receiver = new MessageReceiver(KeyManager, Database, this.chunks, (msg) => this.notifyNewMessage(msg));
    this.reactions = new ReactionService(WebRTCManager, SignalingClient, Database);
    this.delivery = new DeliveryTracker(WebRTCManager, SignalingClient, Database);
    this.receiver.registerHandlers(WebRTCManager, SignalingClient);
    this.initialized = true;
  }

  // Delegate to sender
  async sendTextMessage(...args) { return this.sender.sendTextMessage(...args); }
  async sendImageMessage(...args) { return this.sender.sendImageMessage(...args); }
  // ... etc

  // Callback management ramane aici
  onNewMessage(cb: NewMessageCallback) { this.onNewMessageCallbacks.push(cb); }
  offNewMessage(cb: NewMessageCallback) { /* ... */ }

  // Notify helpers (apelate de receiver)
  private notifyNewMessage(msg: Message) {
    this.onNewMessageCallbacks.forEach(cb => cb(msg));
  }

  destroy() {
    this.chunks.cleanup();
  }
}

export default new MessagingService();
```

### Pas 10 — Verifica ca totul compileaza

```bash
cd /Users/ruslanconstantinovici/qrchatAndroid
npx tsc --noEmit
```

### Pas 11 — Verifica ca importurile existente NU se strica

Cauta toate fisierele care importa MessagingService:
```bash
grep -r "from.*MessagingService" src/ --include="*.ts" --include="*.tsx"
```

**TOATE trebuie sa functioneze fara modificari** — facade-ul exporta acelasi singleton, aceleasi metode.

---

## Fisiere de creat/modificat

| Fisier | Actiune |
|--------|---------|
| `src/services/messaging/types.ts` | CREAT NOU — tipuri partajate |
| `src/services/messaging/MessageSender.ts` | CREAT NOU — logica de trimitere |
| `src/services/messaging/MessageReceiver.ts` | CREAT NOU — logica de receptie |
| `src/services/messaging/ChunkManager.ts` | CREAT NOU — gestionare chunks fisiere |
| `src/services/messaging/ReactionService.ts` | CREAT NOU — reactii, edit, delete |
| `src/services/messaging/DeliveryTracker.ts` | CREAT NOU — read receipts, typing |
| `src/services/messaging/index.ts` | CREAT NOU — re-export |
| `src/services/MessagingService.ts` | REFACTORIZAT — devine facade <200 linii |

---

## Criterii de succes

1. `MessagingService.ts` are sub 200 de linii (facade)
2. Fiecare modul nou are o singura responsabilitate clara
3. `npx tsc --noEmit` — 0 erori TypeScript
4. `grep -r "from.*MessagingService" src/` — TOATE importurile existente functioneaza fara modificari
5. Testele Jest existente trec (`npx jest`)
6. Aplicatia porneste pe emulator fara crash (testat de qa-engineer)

---

## Capcane de evitat

- **NU modifica API-ul public** — `MessagingService` trebuie sa exporte exact aceleasi metode cu aceleasi semnaturi. Oricine face `import MessagingService from '../services/MessagingService'` trebuie sa functioneze identic
- **NU crea dependente circulare** — MessageReceiver depinde de ChunkManager, dar ChunkManager NU depinde de MessageReceiver. Pastreaza graficul de dependente aciclic
- **NU muta callback-urile in sub-servicii** — callback management (on/off) ramane in facade. Sub-serviciile comunica prin callback-uri simple pasate la constructie, NU prin EventBus (ar complica debugging-ul)
- **NU uita de `processingIds`** — acest Set previne procesarea duplicata a mesajelor. Trebuie partajat intre MessageReceiver si orice alt modul care proceseaza incoming messages. Paseaza-l ca parte din `MessagingContext`
- **NU sterge singleton-ul** — `export default new MessagingService()` trebuie sa ramana la final. Toata aplicatia depinde de acest pattern
- **NU refactoriza si alte fisiere** — scopul e DOAR MessagingService.ts. Nu modifica WebRTCManager, SignalingClient, Database etc.
- **Atentie la `this` binding** — cand pasezi metode ca callback-uri la sub-servicii, asigura-te ca `this` e corect (foloseste arrow functions sau `.bind()`)
- **Testeaza incremental** — dupa fiecare modul extras, ruleaza `npx tsc --noEmit` sa verifici ca nu ai stricat nimic
