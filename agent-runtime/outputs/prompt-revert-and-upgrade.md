# PROMPT: Revert la Build 101 + Branch de Upgrade Securitate

## CONTEXT

Build-urile 102-103 au introdus regresii (cold start, audio). Revenim la Build 101 (commit `f772264`) care era stabil — mesaje, apeluri warm, status online, totul verificat si functional pe ambele telefoane.

Apoi cream un branch separat pentru upgrade-ul de securitate si privacy, ca sa putem reveni oricand la versiunea stabila.

## PASUL 1 — REVERT LA BUILD 101

**IMPORTANT:** Nu sterge commit-urile 102-103. Creeaza un branch de backup, apoi reseteaza main.

```bash
cd /Users/ruslanconstantinovici/QRChat

# 1. Salveaza starea curenta intr-un branch de backup
git branch backup/build-103-experiments

# 2. Revino la Build 101 pe main
git reset --hard f772264

# 3. Verifica
git log --oneline -3
# Trebuie sa vezi: f772264 Build 101: Full audit fixes — 10 bugs repaired
```

**Verificare obligatorie dupa revert:**
- `npx tsc --noEmit` — zero erori
- Confirma ca `ios/QRChat/AppDelegate.swift` are `let voipRegistry` (variabila locala, fara fix)
- Confirma ca `index.js` NU are answerCall/endCall listeners cu isActive guard
- Confirma ca `server/index.js` trimite VoIP push DOAR pentru offline (nu "always")

**NU face build, NU face deploy, NU modifica nimic dupa revert. Doar confirma ca starea e curata.**

## PASUL 2 — BRANCH SEPARAT PENTRU UPGRADE

```bash
# Creeaza branch-ul de upgrade pornind de la Build 101
git checkout -b feature/security-privacy-upgrade

# Acum toate modificarile se fac pe acest branch
# main ramane curat la Build 101
```

## PASUL 3 — NUMEROTARE BUILD-URI

De acum înainte, build-urile pe branch-ul de upgrade folosesc seria **200**:
- Primul build pe noul branch: **Build 201**
- Următoarele: 202, 203, 204...

Seria 100 (101, 102, 103) = versiunea veche stabilă.
Seria 200 = versiunea nouă cu upgrade securitate/privacy.

La increment build number, setează `CURRENT_PROJECT_VERSION = 201` (nu 104).

## PASUL 4 — CE URMEAZA

Dupa ce branch-ul e creat, voi primi un prompt separat cu lista completa de imbunatatiri de implementat. Toate se fac pe `feature/security-privacy-upgrade`.

Daca ceva nu merge — `git checkout main` si suntem inapoi la Build 101 stabil.

## REGULI STRICTE

1. **Nu sterge** commit-urile 102-103 — sunt in branch-ul `backup/build-103-experiments`
2. **Nu face push** fara aprobarea mea
3. **Nu face build/archive/TestFlight** fara aprobarea mea
4. **Nu modifica main** — toate schimbarile pe `feature/security-privacy-upgrade`
5. **Nu mentioneaza** sursa de inspiratie in comentarii, commit-uri, sau cod — toate feature-urile sunt dezvoltari proprii QRChat
6. **Commit messages** trebuie sa fie descriptive dar generice: "Add message padding for traffic analysis prevention", NU "Implement SimpleX-style padding"
7. **Nu copia cod** din alte proiecte — implementeaza de la zero bazat pe specificatii tehnice (RFC-uri, standarde criptografice, best practices)
8. **Comentariile din cod** refera standarde, nu produse: "RFC 5869 HKDF", "NaCl crypto_box spec", "WebRTC Insertable Streams API"
