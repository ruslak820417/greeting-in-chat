# SQLite Cold Start Research Report — QRChat iOS

**Date:** 2026-03-29
**Problem:** After cold start call works fine. Killing app + second cold start causes contacts to disappear (SQLite returns empty results). Manual restart fixes it.

---

## 1. Root Cause Analysis (QRChat-Specific)

After examining the codebase (`/Users/ruslanconstantinovici/QRChat/src/storage/Database.ts`) and cross-referencing with known SQLite/iOS issues, there are **three compounding problems**:

### Problem A: WAL + `synchronous=NORMAL` = Data Loss on Kill

**File:** `Database.ts`, line 235-236
```typescript
await this.db.execute("PRAGMA journal_mode = WAL;");
await this.db.execute("PRAGMA synchronous = NORMAL;");
```

With WAL mode and `synchronous=NORMAL`, SQLite does NOT fsync the WAL file after each transaction commit. It only syncs during checkpoints. This means:

- Transactions are written to the `-wal` file but NOT flushed to disk
- If iOS kills the process (which happens on cold start VoIP push), the WAL file may contain unflushed data
- On the next open, SQLite reads the WAL file, but if the OS didn't flush it to disk before the kill, those transactions are GONE

**This is the most likely root cause.** The SQLite documentation explicitly states: *"A transaction committed in WAL mode with synchronous=NORMAL might roll back following a power loss or system crash."* An iOS process kill is equivalent to a power loss from SQLite's perspective.

### Problem B: No WAL Checkpoint Before Background/Kill

**Missing from the codebase entirely:**
- No `applicationWillTerminate` handler in `AppDelegate.swift`
- No `applicationDidEnterBackground` handler in `AppDelegate.swift`
- No `AppState` listener in `Database.ts` that checkpoints on background
- No `PRAGMA wal_checkpoint(TRUNCATE)` anywhere in the codebase
- No `db.close()` call on app lifecycle transitions

When iOS kills the app, the WAL file contains uncommitted (unflushed) pages. The next time the app opens, SQLite runs WAL recovery, but if pages weren't synced to disk, they're lost.

### Problem C: SQLCipher + iOS Background = 0xdead10cc Risk

**File:** `Database.ts`, line 204
```typescript
this.db = open({ name: 'qrchat.db', encryptionKey });
```

QRChat uses SQLCipher encryption via op-sqlite. This triggers a critical iOS-specific issue documented by Signal:

- iOS tries to read the SQLite file header to determine if a file lock is a legitimate database lock
- SQLCipher encrypts the header, making it unreadable to iOS
- iOS sees an unrecognized file with a lock and kills the app with exception code `0xdead10cc`
- This means the app gets killed MORE AGGRESSIVELY than apps with unencrypted databases

This issue does NOT reproduce in the simulator -- only on physical devices.

### Problem D: Stale JSI Handle (Already Partially Fixed)

**File:** `Database.ts`, lines 177-198 (`ensureSQLite()`)

The code already has a health check for stale JSI handles (the `SELECT 1` test), which is good. However, when a cold start creates a new JS runtime, the singleton `Database` instance is recreated from scratch (line 1649: `export default new Database()`), so this isn't the primary issue. The real problem is that the DATA isn't there when the new instance opens the database.

---

## 2. Known Issues Found (With Links)

### SQLite Official Forum
- **[WAL data loss when connection not closed properly](https://sqlite.org/forum/info/b080c1d935a7ba82)** — Confirms that data is unavailable to SELECT from new connections if previous connection wasn't closed properly with WAL mode. Solution: checkpoint before closing.
- **[Data loss after iOS device force restarts](https://sqlite.org/forum/info/dbe512e5bc140c6dac2127f7142a62f591903e9ffe227e87a36bab30a2ae0205)** — Confirms data loss occurs when app is terminated by OS kill.
- **[Why WAL file may disappear](https://sqlite.org/forum/info/d73300eb0a6cc15d)** — Explains WAL file cleanup mechanics and order-dependent behavior.
- **[How corruption happens during WAL checkpoint](https://sqlite.org/forum/info/47107ab818977549)** — Explains checkpoint corruption vectors.

### SQLCipher / Signal
- **[SQLCipher Issue #255: iOS apps terminated on background with encrypted DB](https://github.com/sqlcipher/sqlcipher/issues/255)** — The exact `0xdead10cc` issue. iOS kills apps holding file locks on encrypted databases because it can't read the SQLCipher header.
- **[Signal's SQLCipherVsSharedData demo](https://github.com/signalapp/SQLCipherVsSharedData)** — Signal's reproduction and solution for this bug.
- **[GRDB.swift Issue #302: Important fix for SQLCipher](https://github.com/groue/GRDB.swift/issues/302)** — Documents the `cipher_plaintext_header_size` fix.

### op-sqlite
- **[op-sqlite GitHub Issues](https://github.com/OP-Engineering/op-sqlite/issues)** — No specific "data loss after kill" issue filed, but the library explicitly recommends keeping ONE connection open for the entire app session and NOT closing/reopening.

### Apple Developer
- **[QA1809: Default journaling mode for Core Data SQLite](https://developer.apple.com/library/archive/qa/qa1809/_index.html)** — Apple's documentation on WAL mode behavior and checkpointing.
- **[0xdead10cc prevention](https://developer.apple.com/forums/thread/126438)** — Apple's guidance on avoiding the deadlock crash.
- **[Change in iOS 14 Beta 3 to trigger 0xdead10cc](https://developer.apple.com/forums/thread/655225)** — iOS became stricter about file locks during suspension.

---

## 3. Recommended Fixes (Priority Order)

### Fix 1: Change `synchronous` to FULL (CRITICAL — 1 line change)

**File:** `/Users/ruslanconstantinovici/QRChat/src/storage/Database.ts`, line 236

```typescript
// BEFORE (unsafe — data loss on kill):
await this.db.execute("PRAGMA synchronous = NORMAL;");

// AFTER (safe — every commit is durable):
await this.db.execute("PRAGMA synchronous = FULL;");
```

**Impact:** Small performance cost (extra fsync per commit), but guarantees that every committed transaction survives a process kill. This is what Signal uses.

**Why it works:** With `synchronous=FULL` in WAL mode, SQLite fsyncs the WAL file after every transaction commit. Even if iOS kills the process immediately after, the data is on disk.

### Fix 2: Add WAL Checkpoint on App Background (HIGH)

**File:** `/Users/ruslanconstantinovici/QRChat/src/storage/Database.ts`

Add a new method and AppState listener:

```typescript
/**
 * Checkpoint WAL to main DB file. Call on app background/terminate.
 * Ensures all committed transactions are merged into the main .db file.
 */
async checkpoint(): Promise<void> {
  if (!this.db || !this.sqliteReady) return;
  try {
    await this.db.execute('PRAGMA wal_checkpoint(TRUNCATE)');
    console.log('[Database] WAL checkpoint completed');
  } catch (e) {
    console.warn('[Database] WAL checkpoint failed:', e);
  }
}
```

Then in `MessagingService.ts` (where AppState listener already exists), add checkpoint on background:

```typescript
// In the existing AppState listener (around line 541):
this.appStateSubscription = RNAppState.addEventListener('change', (nextState: string) => {
  if (nextState === 'active') {
    SignalingClient.smartReconnect();
  } else if (nextState === 'background' || nextState === 'inactive') {
    // Checkpoint SQLite WAL before iOS can kill us
    Database.checkpoint().catch(e =>
      console.warn('[DB] Background checkpoint error:', e)
    );
  }
});
```

### Fix 3: Add `applicationDidEnterBackground` in AppDelegate (HIGH)

**File:** `/Users/ruslanconstantinovici/QRChat/ios/QRChat/AppDelegate.swift`

```swift
func applicationDidEnterBackground(_ application: UIApplication) {
  // Begin background task to give SQLite time to checkpoint
  var bgTask = UIBackgroundTaskIdentifier.invalid
  bgTask = application.beginBackgroundTask {
    application.endBackgroundTask(bgTask)
  }

  // The JS-side checkpoint (via AppState listener) handles the actual work.
  // This background task ensures iOS gives us time to complete it.

  // End task after 3 seconds (checkpoint should complete in <100ms)
  DispatchQueue.main.asyncAfter(deadline: .now() + 3.0) {
    application.endBackgroundTask(bgTask)
  }
}

func applicationWillTerminate(_ application: UIApplication) {
  LogService.logNative(1, category: "DB", message: "applicationWillTerminate — iOS is killing us")
  // Note: applicationWillTerminate is NOT reliably called on iOS.
  // The background checkpoint in applicationDidEnterBackground is the real safety net.
}
```

### Fix 4: Add `cipher_plaintext_header_size` for SQLCipher (MEDIUM)

This prevents the `0xdead10cc` issue where iOS aggressively kills the app because it can't identify the encrypted file as a valid SQLite database.

```typescript
// In initSQLite(), after opening the database:
if (encryptionKey) {
  // Allow iOS to read the SQLite header (prevents 0xdead10cc kills)
  // Signal uses this exact approach
  await this.db.execute("PRAGMA cipher_plaintext_header_size = 32;");
}
```

**WARNING:** This requires a one-time migration of existing databases. The first 32 bytes of existing encrypted databases need to be converted. This should be done carefully with a migration path.

**Note:** Check if op-sqlite's SQLCipher build supports this pragma. If not, this fix requires a custom SQLCipher build.

### Fix 5: Reduce WAL Auto-Checkpoint Threshold (LOW)

```typescript
// In initSQLite(), after setting journal_mode:
await this.db.execute("PRAGMA wal_autocheckpoint = 100;"); // Default is 1000
```

This makes SQLite checkpoint more frequently (every 100 pages instead of 1000), reducing the window of data that could be lost. With Fix 1 (`synchronous=FULL`) this is less critical but still good practice.

---

## 4. Best Practices for SQLite in VoIP/Cold-Start Apps

### What Signal Does
Signal (the gold standard for encrypted messaging on iOS) uses:
1. **`synchronous = FULL`** — Every commit is durable
2. **`cipher_plaintext_header_size = 32`** — Prevents iOS from killing the app for holding file locks on encrypted databases
3. **Custom SQLCipher build** with Signal's patches for iOS WAL handling
4. **Single persistent connection** — Never close/reopen during app lifecycle
5. **Explicit checkpoint** on app background transition

### General Best Practices

| Practice | QRChat Status | Action Needed |
|----------|--------------|---------------|
| `synchronous = FULL` in WAL mode | **MISSING** (uses NORMAL) | Change to FULL |
| WAL checkpoint on background | **MISSING** | Add AppState listener |
| `applicationDidEnterBackground` handler | **MISSING** | Add to AppDelegate |
| `beginBackgroundTask` for checkpoint | **MISSING** | Add to AppDelegate |
| `cipher_plaintext_header_size` | **MISSING** | Add (with migration) |
| Single DB connection (no close/reopen) | **OK** (singleton pattern) | No change needed |
| JSI handle health check | **OK** (`SELECT 1` in ensureSQLite) | No change needed |
| `busy_timeout` for concurrent access | **MISSING** | Add `PRAGMA busy_timeout = 5000` |

### Why the Bug is Intermittent
The bug only appears on the SECOND cold start because:
1. First cold start: App opens, loads contacts from DB (data is in main .db file from previous proper shutdown)
2. App receives VoIP push, user takes call, app stays alive
3. User kills app (swipe up or iOS terminates it)
4. During step 3, WAL file has uncommitted pages (contacts, messages written during the call)
5. iOS kills process without checkpoint — WAL pages may not be flushed
6. Second cold start: App opens, SQLite reads WAL file, but unflushed pages are lost
7. Contacts that were written/modified during step 2 appear to vanish
8. Manual restart (step 7): By this point the WAL has been properly recovered/checkpointed, so data appears again

The intermittent nature depends on:
- Whether iOS had time to flush filesystem buffers before the kill
- How much time elapsed between the last write and the kill
- Whether the WAL auto-checkpoint happened to run

---

## 5. Implementation Priority

1. **`synchronous = FULL`** — Immediate fix, 1 line change, eliminates the root cause
2. **WAL checkpoint on background** — Add `Database.checkpoint()` method + AppState listener
3. **`applicationDidEnterBackground`** — Add background task in AppDelegate for checkpoint time
4. **`PRAGMA busy_timeout = 5000`** — Prevents `SQLITE_BUSY` errors during concurrent access
5. **`cipher_plaintext_header_size`** — Prevents aggressive iOS kills (requires migration planning)

Fixes 1-3 should be deployed together in the next build. Fix 4 is a quick addition. Fix 5 requires careful migration testing.
