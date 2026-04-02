# Security Fixes — Faza 1

Data: 2026-03-21
Agent: security-engineer

## Fix-uri aplicate

### 1. GRACE_PERIOD env var rename
- **Fisier:** `server/index.js` linia 138
- **Ce s-a schimbat:** Env var redenumita din `GRACE_PERIOD` in `QRCHAT_GRACE_PERIOD` pentru consistenta cu naming convention-ul proiectului
- **Stare anterioara:** Deja defaulta la `false` (safe), doar env var-ul avea nume generic
- **Impact:** Railway env vars trebuie actualizate daca era setata `GRACE_PERIOD`

### 2. Sender spoofing — DEJA FIXAT
- **Fisier:** `server/index.js`
- **Verificare:** Toate cele 12 puncte de relay folosesc `from: userId` (server-set). Nu exista `message.from || userId` patterns
- **Concluzie:** Fix-ul a fost aplicat intr-o sesiune anterioara

### 3. Admin secret hardcodat — DEJA FIXAT
- **Fisier:** `server/licensing.js`
- **Verificare:** Nu exista fallback '551106'. `ADMIN_SECRET` vine din env var `QRCHAT_ADMIN_SECRET` sau din fisier persistent (cand se schimba via admin API)
- **Concluzie:** Fix-ul a fost aplicat intr-o sesiune anterioara

### 4. AsyncStorage fallback pentru chei private — DEJA FIXAT
- **Fisier:** `src/storage/Database.ts` liniile 754-773
- **Verificare:** `saveKeys()` arunca eroare cand Keychain nu e disponibil, in loc sa faca fallback la AsyncStorage
- **Concluzie:** Fix-ul a fost aplicat intr-o sesiune anterioara

## Rezumat

- 1 fix aplicat in aceasta sesiune (env var rename)
- 3 fix-uri verificate ca deja aplicate
- **Toate sarcinile critice Faza 1 (securitate) sunt COMPLETE**

## Actiuni necesare de la alte echipe

- **backend-engineer:** Deploy server pe Railway cu noua env var `QRCHAT_GRACE_PERIOD` (daca era setata `GRACE_PERIOD`, trebuie redenumita)
