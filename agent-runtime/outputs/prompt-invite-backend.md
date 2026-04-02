# Prompt: backend-engineer — Invite Link Backend & Supabase (Faza 1)

## Obiectiv

Construieste intreaga infrastructura backend pentru sistemul de invite links:
1. Supabase: tabel, RLS, pg_cron, Realtime, Edge Functions
2. Client: SupabaseService.ts, InviteLinkService.ts
3. Railway: landing page endpoint `/invite/:linkId`

## Context

### Supabase Project
- **Project ID:** `wquzcormtzjeagqktmtc`
- **Region:** eu-central-1
- **URL:** `https://wquzcormtzjeagqktmtc.supabase.co`
- **Status:** ACTIVE_HEALTHY (free tier)

### Codebase QRChat
- **Path:** `/Users/ruslanconstantinovici/QRChat`
- **Stack:** React Native 0.84, TypeScript, Node.js server (Express + WebSocket)
- **Server deploy:** Railway.app (`exciting-success-production-d272.up.railway.app`)
- **Server file:** `server/index.js` (Express + WebSocket `ws`)
- **Package manager:** npm

### MCP Tools disponibile
Ai acces la Supabase MCP tools. Foloseste-le:
- `mcp__claude_ai_Supabase__apply_migration` — pentru SQL migration
- `mcp__claude_ai_Supabase__deploy_edge_function` — pentru Edge Functions
- `mcp__claude_ai_Supabase__execute_sql` — pentru SQL ad-hoc (RLS, pg_cron)
- `mcp__claude_ai_Supabase__list_tables` — verificare
- `mcp__claude_ai_Supabase__get_project` — informatii proiect
- `mcp__claude_ai_Supabase__get_publishable_keys` — anon key

### Modelul de securitate (de la security-engineer)
Serverul este zero-knowledge — stocheaza DOAR date criptate. Nu decripteaza niciodata.
- `link_id`: 16 hex chars, derivat din linkSecret (lookup key unic)
- `ciphertext`: base64 string, nacl.secretbox encrypted payload
- `nonce`: base64 string, 24-byte nonce
- `signature`: base64 string, Ed25519 detached signature
- `creator_display_name`: string plaintext OPTIONAL (pentru UX — Bob vede "Alice wants to connect")

---

## Pas 1: Instaleaza dependente

```bash
cd /Users/ruslanconstantinovici/QRChat
npm install @supabase/supabase-js react-native-url-polyfill
```

`@supabase/supabase-js` — clientul Supabase pentru React Native
`react-native-url-polyfill` — necesar pentru Supabase JS in React Native

---

## Pas 2: SQL Migration — Tabelul `invite_links`

Aplica aceasta migrare folosind MCP tool `mcp__claude_ai_Supabase__apply_migration` pe proiectul `wquzcormtzjeagqktmtc`:

```sql
-- Migration: Create invite_links table for invite link system
-- Security model: zero-knowledge server (encrypted payloads only)

create extension if not exists "pgcrypto";

create table public.invite_links (
  id            uuid primary key default gen_random_uuid(),

  -- Lookup key: HKDF-derived from linkSecret (16 hex chars)
  link_id       text not null unique,

  -- Encrypted creator data (server cannot read these)
  creator_encrypted_payload  text not null,     -- base64 nacl.secretbox ciphertext
  creator_nonce              text not null,     -- base64 24-byte nonce
  creator_signature          text not null,     -- base64 Ed25519 detached signature

  -- Plaintext display name (optional, for UX on accept screen)
  creator_display_name       text,

  -- Status machine: pending → accepted / expired / revoked
  status        text not null default 'pending'
                check (status in ('pending', 'accepted', 'expired', 'revoked')),

  -- TTL option chosen by creator
  ttl_option    text not null default '1h'
                check (ttl_option in ('30m', '1h', '24h')),

  -- Encrypted acceptor data (filled on acceptance)
  acceptor_encrypted_payload  text,
  acceptor_nonce              text,
  acceptor_signature          text,
  acceptor_display_name       text,

  -- Timestamps
  created_at    timestamptz not null default now(),
  expires_at    timestamptz not null,
  accepted_at   timestamptz,

  -- Double handshake: creator must confirm after acceptor accepts
  creator_confirmed   boolean not null default false,
  confirmed_at        timestamptz,

  -- Anti-abuse metadata
  metadata      jsonb default '{}'::jsonb
);

-- Performance indexes
create index idx_invite_links_link_id on public.invite_links (link_id);
create index idx_invite_links_status on public.invite_links (status)
  where status = 'pending';
create index idx_invite_links_expires on public.invite_links (expires_at)
  where status = 'pending';

-- Enable Realtime on this table
alter publication supabase_realtime add table public.invite_links;
```

---

## Pas 3: RLS Policies

Executa folosind `mcp__claude_ai_Supabase__execute_sql`:

```sql
-- Enable RLS
alter table public.invite_links enable row level security;

-- Policy 1: Anyone can SELECT (needed for Realtime + validate)
-- Edge Functions use service_role which bypasses RLS anyway
create policy "Anyone can read invite links"
on public.invite_links
for select
to anon, authenticated
using (true);

-- Policy 2: No direct INSERT (only via Edge Functions)
create policy "No direct insert"
on public.invite_links
for insert
to anon, authenticated
with check (false);

-- Policy 3: No direct UPDATE
create policy "No direct update"
on public.invite_links
for update
to anon, authenticated
using (false);

-- Policy 4: No direct DELETE
create policy "No direct delete"
on public.invite_links
for delete
to anon, authenticated
using (false);
```

---

## Pas 4: pg_cron Cleanup

Executa folosind `mcp__claude_ai_Supabase__execute_sql`:

```sql
-- Cleanup function: mark expired + hard-delete old invites
create or replace function public.cleanup_expired_invites()
returns void
language plpgsql
security definer
as $$
begin
  -- Mark pending invites that have passed their expires_at
  update public.invite_links
  set status = 'expired'
  where status = 'pending'
    and expires_at < now();

  -- Hard-delete all invites older than 48 hours (no longer needed)
  delete from public.invite_links
  where created_at < now() - interval '48 hours';
end;
$$;

-- Schedule: run every 5 minutes
select cron.schedule(
  'cleanup-expired-invites',
  '*/5 * * * *',
  $$select public.cleanup_expired_invites()$$
);
```

---

## Pas 5: Edge Functions (4 functii)

Deploy fiecare folosind `mcp__claude_ai_Supabase__deploy_edge_function` pe proiectul `wquzcormtzjeagqktmtc`.

### 5a. Shared utilities

Fisier: `supabase/functions/_shared/cors.ts`
```typescript
export const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers':
    'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, OPTIONS',
};
```

Fisier: `supabase/functions/_shared/supabase-admin.ts`
```typescript
import { createClient } from 'npm:@supabase/supabase-js@2';

export const supabaseAdmin = createClient(
  Deno.env.get('SUPABASE_URL')!,
  Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
);
```

### 5b. `invite-create` — Creeaza un invite link

```typescript
import { corsHeaders } from '../_shared/cors.ts';
import { supabaseAdmin } from '../_shared/supabase-admin.ts';

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const {
      link_id,
      creator_encrypted_payload,
      creator_nonce,
      creator_signature,
      creator_display_name,
      ttl_option,
    } = await req.json();

    // Validate required fields
    if (!link_id || !creator_encrypted_payload || !creator_nonce || !creator_signature) {
      return new Response(
        JSON.stringify({ error: 'Missing required fields: link_id, creator_encrypted_payload, creator_nonce, creator_signature' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
      );
    }

    // Validate link_id format (16 hex chars)
    if (!/^[a-f0-9]{16}$/i.test(link_id)) {
      return new Response(
        JSON.stringify({ error: 'Invalid link_id format (expected 16 hex chars)' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
      );
    }

    // Validate TTL option
    const validTTL = ['30m', '1h', '24h'];
    const ttl = validTTL.includes(ttl_option) ? ttl_option : '1h';

    // Calculate expires_at based on TTL
    const now = new Date();
    let expiresAt: Date;
    switch (ttl) {
      case '30m':
        expiresAt = new Date(now.getTime() + 30 * 60 * 1000);
        break;
      case '1h':
        expiresAt = new Date(now.getTime() + 60 * 60 * 1000);
        break;
      case '24h':
        expiresAt = new Date(now.getTime() + 24 * 60 * 60 * 1000);
        break;
      default:
        expiresAt = new Date(now.getTime() + 60 * 60 * 1000);
    }

    // Check for duplicate link_id (collision protection)
    const { data: existing } = await supabaseAdmin
      .from('invite_links')
      .select('id')
      .eq('link_id', link_id)
      .single();

    if (existing) {
      return new Response(
        JSON.stringify({ error: 'Duplicate link_id. Regenerate the invite.' }),
        { status: 409, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
      );
    }

    // Rate limit: max 10 active invites per display name (simple anti-spam)
    if (creator_display_name) {
      const { count } = await supabaseAdmin
        .from('invite_links')
        .select('*', { count: 'exact', head: true })
        .eq('creator_display_name', creator_display_name)
        .eq('status', 'pending')
        .gt('expires_at', now.toISOString());

      if (count && count >= 10) {
        return new Response(
          JSON.stringify({ error: 'Too many active invites. Revoke some first.' }),
          { status: 429, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
        );
      }
    }

    // Insert the invite
    const { data, error } = await supabaseAdmin
      .from('invite_links')
      .insert({
        link_id,
        creator_encrypted_payload,
        creator_nonce,
        creator_signature,
        creator_display_name: creator_display_name || null,
        ttl_option: ttl,
        expires_at: expiresAt.toISOString(),
      })
      .select('id, link_id, status, ttl_option, created_at, expires_at')
      .single();

    if (error) throw error;

    return new Response(
      JSON.stringify({ invite: data }),
      { status: 201, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
    );
  } catch (error) {
    console.error('invite-create error:', error);
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
    );
  }
});
```

**Deploy:** `mcp__claude_ai_Supabase__deploy_edge_function` — name: `invite-create`, verify JWT: true

### 5c. `invite-validate` — Valideaza un invite link (no auth)

```typescript
import { corsHeaders } from '../_shared/cors.ts';
import { supabaseAdmin } from '../_shared/supabase-admin.ts';

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const url = new URL(req.url);
    const linkId = url.searchParams.get('link_id');

    if (!linkId) {
      return new Response(
        JSON.stringify({ error: 'link_id query parameter required' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
      );
    }

    const { data, error } = await supabaseAdmin
      .from('invite_links')
      .select('id, link_id, creator_display_name, status, expires_at, created_at')
      .eq('link_id', linkId)
      .single();

    if (error || !data) {
      return new Response(
        JSON.stringify({ valid: false, reason: 'not_found' }),
        { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
      );
    }

    // Check expiry
    const now = new Date();
    const expiresAt = new Date(data.expires_at);
    const isExpired = now > expiresAt;

    if (isExpired && data.status === 'pending') {
      // Mark as expired in DB
      await supabaseAdmin
        .from('invite_links')
        .update({ status: 'expired' })
        .eq('id', data.id);
    }

    if (isExpired || data.status !== 'pending') {
      return new Response(
        JSON.stringify({
          valid: false,
          reason: isExpired ? 'expired' : data.status,
          creator_display_name: data.creator_display_name,
        }),
        { status: 410, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
      );
    }

    // Valid invite
    const remainingMs = expiresAt.getTime() - now.getTime();
    const remainingMinutes = Math.floor(remainingMs / 60000);

    return new Response(
      JSON.stringify({
        valid: true,
        creator_display_name: data.creator_display_name,
        remaining_minutes: remainingMinutes,
        invite_id: data.id,
      }),
      { status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
    );
  } catch (error) {
    console.error('invite-validate error:', error);
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
    );
  }
});
```

**Deploy:** `mcp__claude_ai_Supabase__deploy_edge_function` — name: `invite-validate`, verify JWT: **false** (`--no-verify-jwt`)

### 5d. `invite-accept` — Bob accepta invitatie (no auth)

```typescript
import { corsHeaders } from '../_shared/cors.ts';
import { supabaseAdmin } from '../_shared/supabase-admin.ts';

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const {
      link_id,
      acceptor_encrypted_payload,
      acceptor_nonce,
      acceptor_signature,
      acceptor_display_name,
    } = await req.json();

    // Validate required fields
    if (!link_id || !acceptor_encrypted_payload || !acceptor_nonce || !acceptor_signature) {
      return new Response(
        JSON.stringify({ error: 'Missing required fields: link_id, acceptor_encrypted_payload, acceptor_nonce, acceptor_signature' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
      );
    }

    // Fetch the invite
    const { data: invite, error: fetchError } = await supabaseAdmin
      .from('invite_links')
      .select('*')
      .eq('link_id', link_id)
      .eq('status', 'pending')
      .gt('expires_at', new Date().toISOString())
      .single();

    if (fetchError || !invite) {
      return new Response(
        JSON.stringify({ error: 'Invite not found, expired, or already accepted' }),
        { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
      );
    }

    // Atomically update to 'accepted' (optimistic concurrency via WHERE status='pending')
    const { data: updated, error: updateError } = await supabaseAdmin
      .from('invite_links')
      .update({
        status: 'accepted',
        acceptor_encrypted_payload,
        acceptor_nonce,
        acceptor_signature,
        acceptor_display_name: acceptor_display_name || null,
        accepted_at: new Date().toISOString(),
      })
      .eq('id', invite.id)
      .eq('status', 'pending')
      .select()
      .single();

    if (updateError || !updated) {
      return new Response(
        JSON.stringify({ error: 'Invite was already accepted by someone else' }),
        { status: 409, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
      );
    }

    // Return creator's encrypted data (Bob will decrypt with linkSecret)
    return new Response(
      JSON.stringify({
        success: true,
        creator: {
          encrypted_payload: updated.creator_encrypted_payload,
          nonce: updated.creator_nonce,
          signature: updated.creator_signature,
          display_name: updated.creator_display_name,
        },
      }),
      { status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
    );
  } catch (error) {
    console.error('invite-accept error:', error);
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
    );
  }
});
```

**Deploy:** `mcp__claude_ai_Supabase__deploy_edge_function` — name: `invite-accept`, verify JWT: **false** (`--no-verify-jwt`)

### 5e. `invite-confirm` — Alice confirma (double handshake)

```typescript
import { corsHeaders } from '../_shared/cors.ts';
import { supabaseAdmin } from '../_shared/supabase-admin.ts';

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const { link_id } = await req.json();

    if (!link_id) {
      return new Response(
        JSON.stringify({ error: 'link_id required' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
      );
    }

    // Fetch the invite (must be in 'accepted' state)
    const { data: invite, error: fetchError } = await supabaseAdmin
      .from('invite_links')
      .select('*')
      .eq('link_id', link_id)
      .eq('status', 'accepted')
      .single();

    if (fetchError || !invite) {
      return new Response(
        JSON.stringify({ error: 'Invite not found or not in accepted state' }),
        { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
      );
    }

    // Mark as confirmed
    const { data: updated, error: updateError } = await supabaseAdmin
      .from('invite_links')
      .update({
        creator_confirmed: true,
        confirmed_at: new Date().toISOString(),
      })
      .eq('id', invite.id)
      .select()
      .single();

    if (updateError) throw updateError;

    // Return acceptor's encrypted data (Alice will decrypt with linkSecret)
    return new Response(
      JSON.stringify({
        success: true,
        acceptor: {
          encrypted_payload: updated.acceptor_encrypted_payload,
          nonce: updated.acceptor_nonce,
          signature: updated.acceptor_signature,
          display_name: updated.acceptor_display_name,
        },
      }),
      { status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
    );
  } catch (error) {
    console.error('invite-confirm error:', error);
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
    );
  }
});
```

**Deploy:** `mcp__claude_ai_Supabase__deploy_edge_function` — name: `invite-confirm`, verify JWT: **false** (`--no-verify-jwt`)

### 5f. `invite-revoke` — Revoca un invite link

```typescript
import { corsHeaders } from '../_shared/cors.ts';
import { supabaseAdmin } from '../_shared/supabase-admin.ts';

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const { link_id } = await req.json();

    if (!link_id) {
      return new Response(
        JSON.stringify({ error: 'link_id required' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
      );
    }

    const { data, error } = await supabaseAdmin
      .from('invite_links')
      .update({ status: 'revoked' })
      .eq('link_id', link_id)
      .eq('status', 'pending')
      .select('id, link_id, status')
      .single();

    if (error || !data) {
      return new Response(
        JSON.stringify({ error: 'Invite not found or already used/expired' }),
        { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
      );
    }

    return new Response(
      JSON.stringify({ success: true, invite: data }),
      { status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
    );
  } catch (error) {
    console.error('invite-revoke error:', error);
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
    );
  }
});
```

**Deploy:** `mcp__claude_ai_Supabase__deploy_edge_function` — name: `invite-revoke`, verify JWT: **false**

---

## Pas 6: Client Services

### 6a. SupabaseService.ts

Creeaza fisierul `/Users/ruslanconstantinovici/QRChat/src/services/SupabaseService.ts`:

```typescript
import 'react-native-url-polyfill/auto';
import { createClient, SupabaseClient } from '@supabase/supabase-js';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Publishable keys — safe for client-side use
// IMPORTANT: Get the actual anon key from Supabase dashboard or MCP tool get_publishable_keys
const SUPABASE_URL = 'https://wquzcormtzjeagqktmtc.supabase.co';
const SUPABASE_ANON_KEY = 'REPLACE_WITH_ACTUAL_ANON_KEY'; // ← GET THIS from mcp__claude_ai_Supabase__get_publishable_keys

export const supabase: SupabaseClient = createClient(
  SUPABASE_URL,
  SUPABASE_ANON_KEY,
  {
    auth: {
      storage: AsyncStorage,
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: false, // important for React Native
    },
  },
);

export { SUPABASE_URL, SUPABASE_ANON_KEY };
```

**IMPORTANT:** Foloseste `mcp__claude_ai_Supabase__get_publishable_keys` cu project_id `wquzcormtzjeagqktmtc` pentru a obtine cheia `anon` reala. Inlocuieste `REPLACE_WITH_ACTUAL_ANON_KEY`.

### 6b. InviteLinkService.ts

Creeaza fisierul `/Users/ruslanconstantinovici/QRChat/src/services/InviteLinkService.ts`:

```typescript
/**
 * InviteLinkService — API layer for invite link CRUD operations.
 * Calls Supabase Edge Functions and manages Realtime subscriptions.
 */
import { supabase, SUPABASE_URL, SUPABASE_ANON_KEY } from './SupabaseService';
import { RealtimeChannel } from '@supabase/supabase-js';

// ============================================================
// Types
// ============================================================

export interface CreateInviteParams {
  link_id: string;
  creator_encrypted_payload: string;  // base64
  creator_nonce: string;              // base64
  creator_signature: string;          // base64
  creator_display_name?: string;
  ttl_option: '30m' | '1h' | '24h';
}

export interface CreateInviteResponse {
  invite: {
    id: string;
    link_id: string;
    status: string;
    ttl_option: string;
    created_at: string;
    expires_at: string;
  };
}

export interface ValidateInviteResponse {
  valid: boolean;
  creator_display_name?: string;
  remaining_minutes?: number;
  invite_id?: string;
  reason?: string;
}

export interface AcceptInviteParams {
  link_id: string;
  acceptor_encrypted_payload: string;  // base64
  acceptor_nonce: string;              // base64
  acceptor_signature: string;          // base64
  acceptor_display_name?: string;
}

export interface AcceptInviteResponse {
  success: boolean;
  creator: {
    encrypted_payload: string;
    nonce: string;
    signature: string;
    display_name?: string;
  };
}

export interface ConfirmInviteResponse {
  success: boolean;
  acceptor: {
    encrypted_payload: string;
    nonce: string;
    signature: string;
    display_name?: string;
  };
}

export interface InviteRealtimeUpdate {
  status: string;
  acceptor_display_name?: string;
  acceptor_encrypted_payload?: string;
  acceptor_nonce?: string;
  acceptor_signature?: string;
  creator_confirmed?: boolean;
}

// ============================================================
// API Calls (via Supabase Edge Functions)
// ============================================================

/**
 * Create a new invite link.
 * Requires auth (JWT) — user must be authenticated.
 */
export async function createInvite(
  params: CreateInviteParams,
): Promise<CreateInviteResponse> {
  const { data, error } = await supabase.functions.invoke('invite-create', {
    body: params,
    method: 'POST',
  });

  if (error) {
    const errorBody = error.context ? await error.context.json().catch(() => null) : null;
    throw new Error(errorBody?.error || error.message || 'Failed to create invite');
  }

  return data as CreateInviteResponse;
}

/**
 * Validate an invite link (anonymous — no auth needed).
 * Uses direct fetch since this endpoint has --no-verify-jwt.
 */
export async function validateInvite(
  linkId: string,
): Promise<ValidateInviteResponse> {
  const response = await fetch(
    `${SUPABASE_URL}/functions/v1/invite-validate?link_id=${encodeURIComponent(linkId)}`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'apikey': SUPABASE_ANON_KEY,
      },
    },
  );

  const data = await response.json();

  if (!response.ok && response.status !== 410) {
    throw new Error(data.error || 'Failed to validate invite');
  }

  return data as ValidateInviteResponse;
}

/**
 * Accept an invite link (anonymous — no auth needed).
 * Bob sends his encrypted payload, receives Alice's encrypted payload.
 */
export async function acceptInvite(
  params: AcceptInviteParams,
): Promise<AcceptInviteResponse> {
  const response = await fetch(
    `${SUPABASE_URL}/functions/v1/invite-accept`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'apikey': SUPABASE_ANON_KEY,
      },
      body: JSON.stringify(params),
    },
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || 'Failed to accept invite');
  }

  return data as AcceptInviteResponse;
}

/**
 * Confirm an invite (double handshake — Alice confirms after Bob accepts).
 */
export async function confirmInvite(
  linkId: string,
): Promise<ConfirmInviteResponse> {
  const response = await fetch(
    `${SUPABASE_URL}/functions/v1/invite-confirm`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'apikey': SUPABASE_ANON_KEY,
      },
      body: JSON.stringify({ link_id: linkId }),
    },
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || 'Failed to confirm invite');
  }

  return data as ConfirmInviteResponse;
}

/**
 * Revoke a pending invite link.
 */
export async function revokeInvite(linkId: string): Promise<void> {
  const response = await fetch(
    `${SUPABASE_URL}/functions/v1/invite-revoke`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'apikey': SUPABASE_ANON_KEY,
      },
      body: JSON.stringify({ link_id: linkId }),
    },
  );

  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.error || 'Failed to revoke invite');
  }
}

// ============================================================
// Realtime Subscription
// ============================================================

/**
 * Subscribe to real-time updates for a specific invite.
 * Alice uses this to know when Bob accepts.
 *
 * @param inviteId - The UUID of the invite (from CreateInviteResponse)
 * @param onUpdate - Callback when the invite status changes
 * @returns cleanup function to unsubscribe
 */
export function subscribeToInvite(
  inviteId: string,
  onUpdate: (update: InviteRealtimeUpdate) => void,
): () => void {
  const channel: RealtimeChannel = supabase
    .channel(`invite-${inviteId}`)
    .on(
      'postgres_changes',
      {
        event: 'UPDATE',
        schema: 'public',
        table: 'invite_links',
        filter: `id=eq.${inviteId}`,
      },
      (payload) => {
        const updated = payload.new as Record<string, unknown>;
        onUpdate({
          status: updated.status as string,
          acceptor_display_name: updated.acceptor_display_name as string | undefined,
          acceptor_encrypted_payload: updated.acceptor_encrypted_payload as string | undefined,
          acceptor_nonce: updated.acceptor_nonce as string | undefined,
          acceptor_signature: updated.acceptor_signature as string | undefined,
          creator_confirmed: updated.creator_confirmed as boolean | undefined,
        });
      },
    )
    .subscribe();

  // Return cleanup function
  return () => {
    supabase.removeChannel(channel);
  };
}
```

---

## Pas 7: Railway Landing Page

Adauga un endpoint in `/Users/ruslanconstantinovici/QRChat/server/index.js` care serveste o pagina HTML simpla pentru invite links. Aceasta pagina se afiseaza cand Bob deschide link-ul in browser (app-ul nu e instalat).

Cauta in `server/index.js` sectiunea cu Express routes (dupa `app.use(express.json())` si inainte de WebSocket setup). Adauga:

```javascript
// ============================================================
// Invite Link Landing Page
// ============================================================
app.get('/invite/:linkId', (req, res) => {
  const { linkId } = req.params;

  // Validate linkId format (16 hex chars)
  if (!/^[a-f0-9]{16}$/i.test(linkId)) {
    return res.status(400).send('Invalid invite link');
  }

  // Serve a simple landing page
  // The #fragment is preserved by the browser and used by the app
  res.send(`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>QRChat Invite</title>
  <meta property="og:title" content="QRChat Invite">
  <meta property="og:description" content="You've been invited to chat securely on QRChat">
  <meta property="og:type" content="website">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #0a0a0a;
      color: #ffffff;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .container {
      text-align: center;
      padding: 2rem;
      max-width: 400px;
    }
    .logo {
      width: 80px;
      height: 80px;
      background: linear-gradient(135deg, #FF6B00, #FF8C00);
      border-radius: 20px;
      margin: 0 auto 1.5rem;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 2rem;
    }
    h1 { font-size: 1.5rem; margin-bottom: 0.5rem; }
    .subtitle { color: #888; margin-bottom: 2rem; }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      background: rgba(0, 168, 132, 0.15);
      color: #00A884;
      padding: 0.5rem 1rem;
      border-radius: 20px;
      font-size: 0.9rem;
      margin-bottom: 2rem;
    }
    .btn {
      display: block;
      width: 100%;
      padding: 1rem;
      border-radius: 12px;
      font-size: 1rem;
      font-weight: 600;
      text-decoration: none;
      margin-bottom: 0.75rem;
      cursor: pointer;
      border: none;
    }
    .btn-primary {
      background: linear-gradient(135deg, #FF6B00, #FF8C00);
      color: white;
    }
    .btn-secondary {
      background: #1a1a1a;
      color: #888;
      border: 1px solid #333;
    }
    .note { color: #666; font-size: 0.8rem; margin-top: 1.5rem; }
  </style>
</head>
<body>
  <div class="container">
    <div class="logo">Q</div>
    <h1>QRChat</h1>
    <p class="subtitle">Encrypted Messaging</p>
    <div class="badge">&#128274; End-to-end encrypted</div>
    <p style="margin-bottom: 2rem; color: #ccc;">
      You've been invited to chat securely on QRChat
    </p>
    <a class="btn btn-primary" href="qrchat://invite/${linkId}" id="openApp">
      Open in QRChat
    </a>
    <a class="btn btn-secondary" href="https://apps.apple.com/app/qrchat/id6744400349" target="_blank">
      Download on App Store
    </a>
    <p class="note">
      After installing, tap the invite link again to connect automatically.
    </p>
  </div>
  <script>
    // Try to open the app via custom scheme
    // If it fails (app not installed), the page stays visible
    setTimeout(function() {
      window.location.href = 'qrchat://invite/${linkId}' + window.location.hash;
    }, 100);
  </script>
</body>
</html>`);
});
```

**IMPORTANT:** Pune acest route INAINTE de orice catch-all route sau WebSocket upgrade handler.

---

## Pas 8: Verificare

Dupa implementare, verifica:

1. **Tabelul exista:**
   ```
   mcp__claude_ai_Supabase__list_tables (project_id: wquzcormtzjeagqktmtc)
   ```

2. **Edge Functions deployed:**
   ```
   mcp__claude_ai_Supabase__list_edge_functions (project_id: wquzcormtzjeagqktmtc)
   ```
   Trebuie sa vezi: invite-create, invite-validate, invite-accept, invite-confirm, invite-revoke

3. **RLS active:**
   ```sql
   SELECT tablename, policyname, cmd FROM pg_policies WHERE tablename = 'invite_links';
   ```

4. **pg_cron job:**
   ```sql
   SELECT * FROM cron.job WHERE jobname = 'cleanup-expired-invites';
   ```

5. **Realtime enabled:**
   ```sql
   SELECT * FROM pg_publication_tables WHERE pubname = 'supabase_realtime' AND tablename = 'invite_links';
   ```

6. **Client files exist:**
   - `/Users/ruslanconstantinovici/QRChat/src/services/SupabaseService.ts`
   - `/Users/ruslanconstantinovici/QRChat/src/services/InviteLinkService.ts`

7. **npm install success:**
   - `@supabase/supabase-js` in node_modules
   - `react-native-url-polyfill` in node_modules

8. **Railway landing page:**
   - `curl https://exciting-success-production-d272.up.railway.app/invite/a1b2c3d4e5f6a1b2` → HTML response

---

## Reguli stricte

1. **NU modifica** fisiere crypto (`src/crypto/*`) — asta face security-engineer
2. **NU crea** ecrane sau componente UI — asta face frontend-engineer
3. **NU modifica** WebSocket logic-ul existent in `server/index.js` — adauga DOAR ruta Express noua
4. **Supabase anon key** — e o cheie PUBLICA (publishable), sigura pentru client. Service role key NU se pune niciodata in client code
5. **Deploy pe Railway** se face DOAR prin `deploy.sh` cu auto-verify si rollback (dupa ce adaugi landing page endpoint)
6. **Nu face git push** fara aprobarea lead-ului
7. **Dupa orice modificare de cod:** deploy pe simulator + telefon fizic
8. **Incrementeaza build number** daca modifici cod nativ (package.json)

---

## Fisiere pe care le creezi/modifici

| Fisier | Actiune | Ce faci |
|--------|---------|---------|
| `src/services/SupabaseService.ts` | **CREATE** | Client Supabase init |
| `src/services/InviteLinkService.ts` | **CREATE** | API layer + Realtime |
| `server/index.js` | **MODIFY** | Adauga `/invite/:linkId` route |
| `package.json` | **MODIFY** (npm install) | Adauga dependente |

---

## Output

Dupa ce ai terminat:

1. Actualizeaza `agent-runtime/state/status.md`:
   ```
   | backend-engineer | DONE | Supabase setup + Edge Functions + client services | — |
   ```

2. Scrie in `agent-runtime/messages/backend-to-frontend.md`:
   ```
   # Mesaj de la backend-engineer catre frontend-engineer + network-engineer

   Backend-ul invite links este gata.

   ## Ce exista acum:
   - Supabase table `invite_links` cu RLS + pg_cron + Realtime
   - 5 Edge Functions: invite-create, invite-validate, invite-accept, invite-confirm, invite-revoke
   - SupabaseService.ts — client Supabase init
   - InviteLinkService.ts — toate API-urile + Realtime subscription
   - Railway landing page la /invite/:linkId

   ## Cum folosesti:
   - Import: `import { createInvite, validateInvite, acceptInvite, ... } from '../services/InviteLinkService'`
   - Realtime: `const unsub = subscribeToInvite(inviteId, (update) => { ... })`

   ## URL format:
   https://exciting-success-production-d272.up.railway.app/invite/LINK_ID#base64url(linkSecret)
   - LINK_ID = 16 hex chars (din path)
   - linkSecret = 32 bytes base64url encoded (din fragment, dupa #)
   ```

---

## Dependente

- **Depinzi de**: nimic (poti incepe imediat, in paralel cu security-engineer)
- **Te asteapta**: frontend-engineer (ecrane), network-engineer (deep links), qa-engineer (teste)
- **Nu blochezi** pe security-engineer — lucrati in paralel
- **Coordinare cu security-engineer**: schema tabelului si Edge Functions folosesc aceleasi campuri ca `EncryptedInvite` din `InviteLinkCrypto.ts`. Daca security-engineer schimba structura, adapteaza schema
