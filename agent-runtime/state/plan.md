# QRChat Team — Plan: Invite Links System

## Obiectiv
Implementarea sistemului de invite links — partajarea contactelor prin link criptat (WhatsApp/Viber/SMS), cu double handshake, TTL configurabil (30m/1h/24h), tracking status in Supabase.

## Decizii luate
- Domeniu: Railway existent (exciting-success-production-d272.up.railway.app)
- TTL: utilizatorul alege (30m / 1h / 24h)
- Double handshake: DA — ambii trebuie sa accepte
- Supabase project: `wquzcormtzjeagqktmtc` (eu-central-1, free tier)
- Securitate: linkSecret 32 bytes in URL fragment (#), payload criptat pe server, Ed25519 semnatura

## Faza 1 — Backend + Securitate (paralel)

### security-engineer
- Implementeaza InviteLinkCrypto: linkSecret gen, HKDF derivare linkId + encKey
- Encrypt/decrypt payload cu nacl.secretbox
- Ed25519 sign/verify pe payload
- Fisier nou: src/crypto/InviteLinkCrypto.ts

### backend-engineer
- Creeaza tabelul invite_links in Supabase (migration SQL)
- Creeaza 3 Edge Functions: invite-create, invite-validate, invite-accept
- Configureaza RLS policies
- Configureaza pg_cron cleanup (la 5 min)
- Activeaza Realtime pe tabel
- Creeaza src/services/SupabaseService.ts (client init)
- Creeaza src/services/InviteLinkService.ts (API calls)

## Faza 2 — Deep Links + Ecrane (paralel)

### network-engineer
- Deep link handler in App.tsx (Linking API)
- Parsare URL: railway-url/invite/CODE#linkSecret
- Rutare catre InviteAcceptScreen
- Gestionare cold start + warm start

### frontend-engineer
- Ecran nou: CreateInviteScreen (TTL selector, create button)
- Ecran nou: ShareInviteScreen (QR + link + copy + share sheet)
- Ecran nou: InviteAcceptScreen (numele creatorului, Accept/Decline)
- Ecran nou: InviteManagementScreen (lista link-uri + status + countdown)
- Buton "Share Link" pe QRGenerateScreen
- Hook: useInviteRealtime (Supabase Realtime)
- i18n: toate stringurile noi in en/ro/ru/fr
- Navigatie: adauga ecranele noi in React Navigation

## Faza 3 — QA + Integrare

### qa-engineer
- Teste: create invite, validate, accept, expire, revoke
- Teste: double handshake flow complet
- Teste: brute force protection (rate limiting)
- Teste: expired link handling
- Test pe simulator + dispozitiv fizic

### prompt-architect
- Scrie prompt-uri detaliate pentru fiecare agent inainte de fiecare faza

## Dependente

```
prompt-architect ──→ TOTI (scrie prompt-urile intai)
security-engineer ──→ backend-engineer (crypto module necesar pentru Edge Functions)
                  ──→ frontend-engineer (encrypt/decrypt in ecrane)
backend-engineer ──→ frontend-engineer (API-uri necesare pentru ecrane)
                 ──→ network-engineer (URL format pentru deep links)
network-engineer ──→ frontend-engineer (deep link handler necesitar pentru navigatie)
TOTI ────────────→ qa-engineer (teste dupa implementare)
```
