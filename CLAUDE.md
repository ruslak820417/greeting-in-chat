# QRChat — Agent Teams

Acest proiect coordoneaza o echipa de 7 agenti specializati care lucreaza impreuna la dezvoltarea, securizarea si publicarea aplicatiei QRChat — un messenger criptat React Native.

## Proiectul tinta

- **Codebase:** `/Users/ruslanconstantinovici/QRChat`
- **Tech stack:** React Native 0.84, TypeScript, Node.js server, TweetNaCl crypto, WebRTC, SQLite
- **Versiune curenta:** 3.0.6

## Reguli de lucru in echipa

### Dependente intre agenti

Agentii sunt interdependenti. Daca un agent nu poate finaliza o sarcina pentru ca depinde de munca altui agent, el trebuie:

1. Sa scrie in `agent-runtime/messages/` un mesaj catre agentul de care depinde
2. Sa actualizeze `agent-runtime/state/status.md` cu statusul "BLOCKED — astept [agent-name]"
3. Sa continue cu alte sarcini independente din lista sa
4. Sa revina la sarcina blocata dupa ce primeste raspuns

### Comunicare

- Toate rezultatele se scriu in fisiere, nu raman in conversatie
- Fiecare agent actualizeaza `agent-runtime/state/status.md` cand incepe/finalizeaza o sarcina
- Handoff-urile intre agenti se fac prin `agent-runtime/messages/`
- Artefactele comune (shared) sunt in `agent-runtime/shared/`
- Rezultatele finale sunt in `agent-runtime/outputs/`

### Reguli stricte

- Toti agentii lucreaza pe acelasi proiect QRChat (`/Users/ruslanconstantinovici/QRChat`)
- Fiecare agent modifica DOAR fisierele din domeniul sau de competenta
- Inainte de a modifica un fisier pe care alt agent l-ar putea modifica simultan, verifica statusul in `agent-runtime/state/status.md`
- Nu face push la git fara aprobarea lead-ului
- Dupa fiecare modificare, deploy pe simulator si telefon fizic (regula obligatorie)
- Testeaza pe dispozitiv real inainte de a marca o sarcina ca finalizata

## Structura runtime

```
agent-runtime/
  messages/      — comunicare inter-agenti (mesaje, cereri, raspunsuri)
  shared/        — artefacte comune (planuri, checklists, dependente)
  state/         — plan.md (plan curent), status.md (status board)
  outputs/       — rezultate finale (rapoarte, audituri, checklists)
```

## Echipa de agenti (7)

| Agent | Domeniu | Fisiere principale |
|-------|---------|-------------------|
| security-engineer | Securitate, criptografie, autentificare | crypto/, server/index.js, storage/Database.ts |
| backend-engineer | Server Node.js, API, persistenta | server/, services/PushTokenService.ts |
| frontend-engineer | Ecrane, componente, UI/UX, accessibility | screens/, components/, utils/ThemeContext.tsx |
| qa-engineer | Teste, calitate, npm audit, verificari | __tests__/, jest.config.js, package.json |
| architect | Refactorizare, tipuri, arhitectura | services/MessagingService.ts, utils/types.ts |
| network-engineer | WebRTC, signaling, P2P, apeluri | network/, services/CallKitService.ts |
| release-engineer | App Store, CI/CD, metadata, deploy | ios/, android/, CHANGELOG.md, package.json |

## Ordinea de lucru recomandata

### Faza 1 — Critice (security-engineer + backend-engineer in paralel)
- Fix autentificare server (GRACE_PERIOD)
- Fix sender spoofing
- Fix admin secret hardcodat
- Limita pending message queue

### Faza 2 — Stabilitate (architect + qa-engineer + network-engineer in paralel)
- Fix teste broken
- Refactorizare MessagingService
- Fix memory leaks networking
- TypeScript cleanup

### Faza 3 — UI/UX (frontend-engineer)
- Accessibility labels
- Fix race conditions
- i18n completare
- Polish design

### Faza 4 — Release (release-engineer, depinde de toate fazele anterioare)
- Privacy Policy
- App Store metadata
- Screenshots
- Submission

## Lansare

```bash
tmux new -s qrchat-team
claude
```

Instructiune: "Lanseaza echipa QRChat cu toti 7 agentii. Sarcina: [descriere]"
