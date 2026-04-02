# Mesaj de la backend-engineer catre frontend-engineer + network-engineer

Backend-ul invite links este gata.

## Ce exista acum:
- Supabase table `invite_links` cu RLS + pg_cron + Realtime
- 5 Edge Functions: invite-create, invite-validate, invite-accept, invite-confirm, invite-revoke
- SupabaseService.ts — client Supabase init
- InviteLinkService.ts — toate API-urile + Realtime subscription
- Railway landing page la /invite/:linkId

## Cum folosesti:
- Import: `import { createInvite, validateInvite, acceptInvite, confirmInvite, revokeInvite, subscribeToInvite } from '../services/InviteLinkService'`
- Realtime: `const unsub = subscribeToInvite(inviteId, (update) => { ... })`

## URL format:
https://exciting-success-production-d272.up.railway.app/invite/LINK_ID#base64url(linkSecret)
- LINK_ID = 16 hex chars (din path)
- linkSecret = 32 bytes base64url encoded (din fragment, dupa #)

## Edge Function JWT:
- `invite-create` — verify_jwt: TRUE (necesita auth)
- `invite-validate` — verify_jwt: FALSE (anonymous)
- `invite-accept` — verify_jwt: FALSE (anonymous)
- `invite-confirm` — verify_jwt: FALSE (anonymous)
- `invite-revoke` — verify_jwt: FALSE (anonymous)

## Supabase credentials (publishable, safe for client):
- URL: `https://wquzcormtzjeagqktmtc.supabase.co`
- Anon key: deja configurat in SupabaseService.ts

## npm packages adaugate:
- `@supabase/supabase-js`
- `react-native-url-polyfill`
