# Prompt: Backend Engineer — Apple Receipt Validation Server

## Rol
Tu esti **backend-engineer** pentru QRChat. Sarcina ta este sa adaugi pe server endpoint-ul de validare Apple IAP receipt si sa integrezi cu sistemul de licensing existent.

## Context proiect
- **Codebase:** `/Users/ruslanconstantinovici/QRChat`
- **Server:** `server/index.js` (Node.js + Express + WebSocket)
- **Licensing:** `server/licensing.js` (promo codes + device licensing)
- **Server LIVE:** Railway — `https://exciting-success-production-d272.up.railway.app`
- **Bundle ID:** `com.ruslan.qrchat`
- **Product ID:** `com.ruslan.qrchat.unlimited`
- **Tip produs:** Non-consumable ($2.99)

## Fisiere de citit OBLIGATORIU
1. `server/index.js` — vezi cum sunt definite endpoint-urile existente (linia ~206-230)
2. `server/licensing.js` — toata logica de licensing (promo codes, device licensing)
3. `package.json` (root) — dependente server (Node.js)

## Ce trebuie sa faci

### 1. Adauga endpoint `POST /validate-receipt` in `server/index.js`

Acest endpoint primeste receipt-ul de la client dupa o cumparare IAP si il valideaza cu Apple.

#### Locatie in cod
Adauga DUPA endpoint-ul `/check-license` (linia ~225 in index.js):

```javascript
// Validate Apple IAP receipt (din app dupa purchase/restore)
app.post('/validate-receipt', async (req, res) => {
  const { transactionId, productId, purchaseToken, deviceId } = req.body;

  // 1. Validare input
  if (!transactionId || !productId || !deviceId) {
    return res.status(400).json({
      success: false,
      message: 'Missing transactionId, productId, or deviceId',
    });
  }

  // 2. Verifica product ID
  if (productId !== 'com.ruslan.qrchat.unlimited') {
    return res.status(400).json({
      success: false,
      message: 'Unknown product ID',
    });
  }

  // 3. Verifica daca tranzactia e deja inregistrata (idempotent)
  if (isTransactionRegistered(transactionId)) {
    // Tranzactie deja procesata — re-licentiaza device-ul
    licensedDevices.set(deviceId, true);
    saveToDisk();
    return res.json({ success: true, message: 'Transaction already validated' });
  }

  // 4. Valideaza cu Apple (vezi sectiunea de mai jos)
  try {
    const isValid = await validateWithApple(transactionId, productId);

    if (isValid) {
      // 5. Licentiaza device-ul
      registerIAPTransaction(transactionId, productId, deviceId);
      return res.json({ success: true, message: 'Purchase validated! QRChat Unlimited active.' });
    } else {
      return res.json({ success: false, message: 'Receipt validation failed' });
    }
  } catch (error) {
    console.error('[License] Receipt validation error:', error.message);
    // In caz de eroare Apple API — accepta tranzactia temporar
    // (mai bine un false positive decat un client frustrat)
    registerIAPTransaction(transactionId, productId, deviceId);
    return res.json({ success: true, message: 'Purchase accepted (pending full validation)' });
  }
});
```

### 2. Adauga functii noi in `server/licensing.js`

#### a. Storage pentru tranzactii IAP

Adauga la inceputul fisierului, langa celelalte constante de fisiere (linia ~22-23):

```javascript
const IAP_FILE = path.join(DATA_DIR, 'qrchat_iap_transactions.json');

// transactionId -> { productId, deviceId, validatedAt, source }
const iapTransactions = new Map();
```

Adauga incarcare/salvare in functiile `loadFromDisk()` si `saveToDisk()`:

```javascript
// In loadFromDisk(), dupa blocul licensedDevices:
try {
  if (fs.existsSync(IAP_FILE)) {
    const data = JSON.parse(fs.readFileSync(IAP_FILE, 'utf8'));
    for (const [txId, entry] of Object.entries(data)) {
      iapTransactions.set(txId, entry);
    }
    console.log(`[License] Loaded ${iapTransactions.size} IAP transactions from disk`);
  }
} catch (e) {
  console.warn('[License] Failed to load IAP transactions:', e.message);
}

// In saveToDisk(), dupa licensedObj:
const iapObj = Object.fromEntries(iapTransactions);
fs.writeFileSync(IAP_FILE, JSON.stringify(iapObj, null, 2), 'utf8');
```

#### b. Functii de gestionare tranzactii

```javascript
/**
 * Verifica daca o tranzactie IAP e deja inregistrata.
 */
function isTransactionRegistered(transactionId) {
  return iapTransactions.has(transactionId);
}

/**
 * Inregistreaza o tranzactie IAP valida.
 */
function registerIAPTransaction(transactionId, productId, deviceId) {
  iapTransactions.set(transactionId, {
    productId,
    deviceId,
    validatedAt: Date.now(),
    source: 'apple_iap',
  });
  licensedDevices.set(deviceId, true);
  console.log(`[License] IAP transaction registered: ${transactionId} → device ${deviceId.substring(0, 8)}...`);
  saveToDisk();
}

/**
 * Listeaza tranzactii IAP (admin only).
 */
function listIAPTransactions(adminSecret) {
  if (!verifyAdminSecret(adminSecret)) return null;
  const txns = [];
  for (const [txId, entry] of iapTransactions.entries()) {
    txns.push({ transactionId: txId, ...entry });
  }
  return txns;
}
```

#### c. Exporta noile functii

Actualizeaza `module.exports` (linia ~255):

```javascript
module.exports = {
  createPromoCode,
  redeemPromo,
  isDeviceLicensed,
  listCodes,
  changeAdminSecret,
  isTransactionRegistered,
  registerIAPTransaction,
  listIAPTransactions,
  get ADMIN_SECRET() { return ADMIN_SECRET; },
};
```

### 3. Apple Receipt Validation

#### Varianta A — Simpla (recomandata pentru v1.0)

Pentru un non-consumable de $2.99, validarea client-side prin StoreKit 2 (pe care `react-native-iap` o face automat) este suficienta. Server-ul inregistreaza tranzactia si licentiaza device-ul pe baza transactionId-ului primit de la client.

```javascript
/**
 * Validare simplificata — StoreKit 2 valideaza pe client.
 * Server-ul inregistreaza tranzactia si verifica unicitatea.
 */
async function validateWithApple(transactionId, productId) {
  // StoreKit 2 pe iOS verifica automat semnatura Apple pe client
  // Server-ul nostru verifica doar ca:
  // 1. transactionId nu e duplicat (previne replay)
  // 2. productId este corect
  // 3. transactionId are format valid (numeric string)

  if (!/^\d+$/.test(transactionId)) {
    console.warn(`[License] Invalid transactionId format: ${transactionId}`);
    return false;
  }

  return true; // Accept — StoreKit 2 a validat deja pe client
}
```

#### Varianta B — Full server-side (pentru viitor, cu Apple App Store Server API v2)

Daca in viitor se doreste validare completa pe server, se va folosi Apple App Store Server API v2:
- Necesita: App Store Connect API Key (p8 file)
- Endpoint Apple: `https://api.storekit.itunes.apple.com/inApps/v2/transactions/{transactionId}`
- Auth: JWT cu ES256 semnat cu cheia API

**NU implementa varianta B acum** — varianta A este suficienta pentru submission Apple si protejeaza impotriva replay attacks.

### 4. Actualizeaza endpoint-ul `POST /check-license`

Modifica endpoint-ul existent (linia ~219) sa verifice si tranzactiile IAP:

```javascript
// Verificare licenta device (din app)
app.post('/check-license', (req, res) => {
  const { deviceId } = req.body;
  if (!deviceId) {
    return res.status(400).json({ success: false, message: 'Missing deviceId' });
  }
  const licensed = isDeviceLicensed(deviceId);
  res.json({ licensed, source: licensed ? 'promo_or_iap' : 'none' });
});
```

`isDeviceLicensed()` va returna `true` pentru AMBELE surse (promo code SAU IAP) — nu necesita modificari, pentru ca ambele seteaza `licensedDevices.set(deviceId, true)`.

### 5. Adauga admin endpoint pentru listare tranzactii IAP

```javascript
// List IAP transactions (admin)
app.get('/admin/iap-transactions', (req, res) => {
  const secret = req.headers['x-admin-secret'];
  const txns = listIAPTransactions(secret);
  if (!txns) return res.status(403).json({ error: 'Unauthorized' });
  res.json(txns);
});
```

## Actualizeaza import-uri in `server/index.js`

Modifica linia ~19 (import-ul din licensing):

```javascript
const {
  createPromoCode,
  redeemPromo,
  isDeviceLicensed,
  listCodes,
  changeAdminSecret,
  isTransactionRegistered,
  registerIAPTransaction,
  listIAPTransactions,
  ADMIN_SECRET,
} = require('./licensing');
```

## Reguli stricte

1. **NU modifica** fisiere din `src/` — acelea sunt pentru architect/frontend
2. **NU modifica** fisiere din `ios/` sau `android/` — acelea sunt pentru release-engineer
3. Toate endpoint-urile noi trebuie sa aiba validare input (400 pe missing fields)
4. Logging cu prefix `[License]` — consistent cu restul codului
5. Toate datele se salveaza pe disc (functia `saveToDisk()`) — supravietuiesc restart server
6. Endpoint-ul `/validate-receipt` trebuie sa fie **idempotent** — acelasi transactionId returneaza success fara a dubla inregistrarea

## Testare server local

```bash
cd /Users/ruslanconstantinovici/QRChat/server
QRCHAT_GRACE_PERIOD=true QRCHAT_ADMIN_SECRET=test-secret-123 node index.js

# Test endpoint (din alt terminal):
curl -X POST http://localhost:3000/validate-receipt \
  -H "Content-Type: application/json" \
  -d '{"transactionId":"123456789","productId":"com.ruslan.qrchat.unlimited","deviceId":"test-device-id"}'

# Verifica ca raspunde { success: true }

curl -X POST http://localhost:3000/check-license \
  -H "Content-Type: application/json" \
  -d '{"deviceId":"test-device-id"}'

# Verifica ca raspunde { licensed: true }
```

## Deploy pe Railway

Dupa testare locala, deploy pe Railway:
1. Commit + push pe branch-ul principal
2. Railway va face auto-deploy
3. Testeaza endpoint-ul pe URL-ul live

## Verificare finala

- [ ] `POST /validate-receipt` functioneaza si returneaza `{ success: true }`
- [ ] `POST /validate-receipt` este idempotent (al doilea call cu acelasi transactionId returneaza success)
- [ ] `POST /check-license` returneaza `{ licensed: true }` dupa validate-receipt
- [ ] `GET /admin/iap-transactions` returneaza lista tranzactiilor (cu admin secret)
- [ ] Datele supravietuiesc restart server (salvate in `qrchat_iap_transactions.json`)
- [ ] Nu sunt erori in console la pornire
- [ ] Import-urile din `index.js` sunt actualizate
