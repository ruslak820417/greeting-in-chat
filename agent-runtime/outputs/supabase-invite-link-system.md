# Invite Link System with Supabase -- Technical Research Report

**Date:** 2026-03-24
**Purpose:** Architecture and implementation guide for a time-limited invite link system using Supabase (Edge Functions, RLS, pg_cron, Realtime) integrated with a React Native app.

---

## Table of Contents

1. [Recommended Table Schema](#1-recommended-table-schema)
2. [Edge Function Code (Deno/TypeScript)](#2-edge-functions-denotypeScript)
3. [Row Level Security (RLS) Policies](#3-row-level-security-rls-policies)
4. [pg_cron Cleanup for Expired Links](#4-pg_cron-cleanup-for-expired-links)
5. [React Native Integration](#5-react-native-integration)
6. [Realtime Subscription](#6-realtime-subscription)
7. [Architecture Overview](#7-architecture-overview)

---

## 1. Recommended Table Schema

```sql
-- Enable required extensions
create extension if not exists "pgcrypto";   -- for gen_random_uuid()
create extension if not exists "pg_cron";     -- for scheduled cleanup

create table public.invite_links (
  id            uuid primary key default gen_random_uuid(),

  -- The short code in the URL: qrchat.app/invite/A1B2C3
  code          text not null unique default encode(gen_random_bytes(6), 'hex'),

  -- Who created this invite
  creator_id    text not null,            -- QRChat user ID (not Supabase auth)
  creator_name  text,                     -- Display name for the invite screen

  -- Creator's public key so Bob can establish E2E crypto
  creator_public_key text not null,

  -- Status tracking
  status        text not null default 'pending'
                check (status in ('pending', 'accepted', 'expired', 'revoked')),

  -- Who accepted (filled on acceptance)
  acceptor_id         text,
  acceptor_name       text,
  acceptor_public_key text,

  -- TTL: 60-minute expiry
  created_at    timestamptz not null default now(),
  expires_at    timestamptz not null default (now() + interval '60 minutes'),
  accepted_at   timestamptz,

  -- Optional metadata
  metadata      jsonb default '{}'::jsonb
);

-- Performance indexes
create index idx_invite_links_code on public.invite_links (code);
create index idx_invite_links_creator on public.invite_links (creator_id);
create index idx_invite_links_status on public.invite_links (status);
create index idx_invite_links_expires on public.invite_links (expires_at)
  where status = 'pending';  -- partial index, only scan pending rows

-- Enable Realtime on this table (for live status updates)
alter publication supabase_realtime add table public.invite_links;
```

### Schema Design Decisions

| Column | Rationale |
|--------|-----------|
| `code` | 12-char hex (6 random bytes). Short enough for URLs, 281 trillion combinations. |
| `creator_public_key` | QRChat is E2E encrypted -- the invite must carry the public key so the acceptor can derive a shared secret without a separate key exchange round-trip. |
| `expires_at` | Computed default at INSERT time. Application and cron both check this. |
| `status` | State machine: `pending` -> `accepted` / `expired` / `revoked`. Check constraint enforces valid values. |
| Partial index on `expires_at` | Only indexes `pending` rows, keeping the index small and cleanup queries fast. |

---

## 2. Edge Functions (Deno/TypeScript)

Three Edge Functions handle the invite lifecycle: **create**, **validate**, and **accept**.

### 2a. Shared Utilities

File: `supabase/functions/_shared/supabase-admin.ts`

```typescript
import { createClient } from 'npm:@supabase/supabase-js@2'

// Admin client -- bypasses RLS, used for server-side operations
export const supabaseAdmin = createClient(
  Deno.env.get('SUPABASE_URL')!,
  Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
)
```

File: `supabase/functions/_shared/cors.ts`

```typescript
// For @supabase/supabase-js >= v2.95.0 you can import directly:
// import { corsHeaders } from 'jsr:@supabase/supabase-js@2/cors'

export const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers':
    'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, OPTIONS',
}
```

### 2b. Create Invite Link

File: `supabase/functions/invite-create/index.ts`

```typescript
import { corsHeaders } from '../_shared/cors.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'

Deno.serve(async (req: Request) => {
  // CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const { creator_id, creator_name, creator_public_key } = await req.json()

    // Validate required fields
    if (!creator_id || !creator_public_key) {
      return new Response(
        JSON.stringify({ error: 'creator_id and creator_public_key required' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Optional: limit active invites per user (prevent spam)
    const { count } = await supabaseAdmin
      .from('invite_links')
      .select('*', { count: 'exact', head: true })
      .eq('creator_id', creator_id)
      .eq('status', 'pending')
      .gt('expires_at', new Date().toISOString())

    if (count && count >= 5) {
      return new Response(
        JSON.stringify({ error: 'Maximum 5 active invites. Revoke one first.' }),
        { status: 429, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Insert the invite
    const { data, error } = await supabaseAdmin
      .from('invite_links')
      .insert({
        creator_id,
        creator_name,
        creator_public_key,
      })
      .select()
      .single()

    if (error) throw error

    // Build the shareable link
    const inviteUrl = `https://qrchat.app/invite/${data.code}`

    return new Response(
      JSON.stringify({
        invite: data,
        url: inviteUrl,
        expires_in_minutes: 60,
      }),
      { status: 201, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  } catch (error) {
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})
```

### 2c. Validate Invite Link (anonymous access -- no auth required)

File: `supabase/functions/invite-validate/index.ts`

```typescript
import { corsHeaders } from '../_shared/cors.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const url = new URL(req.url)
    const code = url.searchParams.get('code')

    if (!code) {
      return new Response(
        JSON.stringify({ error: 'code parameter required' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const { data, error } = await supabaseAdmin
      .from('invite_links')
      .select('id, code, creator_name, status, expires_at')
      .eq('code', code)
      .single()

    if (error || !data) {
      return new Response(
        JSON.stringify({ valid: false, error: 'Invite not found' }),
        { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Check expiry
    const now = new Date()
    const expiresAt = new Date(data.expires_at)
    const isExpired = now > expiresAt

    if (isExpired || data.status !== 'pending') {
      // Mark as expired in DB if not already
      if (data.status === 'pending' && isExpired) {
        await supabaseAdmin
          .from('invite_links')
          .update({ status: 'expired' })
          .eq('id', data.id)
      }

      return new Response(
        JSON.stringify({
          valid: false,
          reason: isExpired ? 'expired' : data.status,
          creator_name: data.creator_name,
        }),
        { status: 410, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Valid invite
    const remainingMs = expiresAt.getTime() - now.getTime()
    const remainingMinutes = Math.floor(remainingMs / 60000)

    return new Response(
      JSON.stringify({
        valid: true,
        creator_name: data.creator_name,
        remaining_minutes: remainingMinutes,
      }),
      { status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  } catch (error) {
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})
```

**Deploy with `--no-verify-jwt`** since this endpoint must be accessible without authentication:

```bash
supabase functions deploy invite-validate --no-verify-jwt
```

### 2d. Accept Invite Link

File: `supabase/functions/invite-accept/index.ts`

```typescript
import { corsHeaders } from '../_shared/cors.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const { code, acceptor_id, acceptor_name, acceptor_public_key } =
      await req.json()

    if (!code || !acceptor_id || !acceptor_public_key) {
      return new Response(
        JSON.stringify({ error: 'code, acceptor_id, acceptor_public_key required' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Fetch the invite
    const { data: invite, error: fetchError } = await supabaseAdmin
      .from('invite_links')
      .select('*')
      .eq('code', code)
      .eq('status', 'pending')
      .gt('expires_at', new Date().toISOString())
      .single()

    if (fetchError || !invite) {
      return new Response(
        JSON.stringify({ error: 'Invite not found, expired, or already used' }),
        { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Prevent self-acceptance
    if (invite.creator_id === acceptor_id) {
      return new Response(
        JSON.stringify({ error: 'Cannot accept your own invite' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Atomically update the invite to 'accepted'
    const { data: updated, error: updateError } = await supabaseAdmin
      .from('invite_links')
      .update({
        status: 'accepted',
        acceptor_id,
        acceptor_name,
        acceptor_public_key,
        accepted_at: new Date().toISOString(),
      })
      .eq('id', invite.id)
      .eq('status', 'pending')  // Optimistic concurrency: only if still pending
      .select()
      .single()

    if (updateError || !updated) {
      return new Response(
        JSON.stringify({ error: 'Invite was already accepted by someone else' }),
        { status: 409, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Return both parties' public keys so they can derive shared secret
    return new Response(
      JSON.stringify({
        success: true,
        pairing: {
          creator_id: updated.creator_id,
          creator_name: updated.creator_name,
          creator_public_key: updated.creator_public_key,
          acceptor_id: updated.acceptor_id,
          acceptor_name: updated.acceptor_name,
          acceptor_public_key: updated.acceptor_public_key,
        },
      }),
      { status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  } catch (error) {
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})
```

### Deployment Commands

```bash
# Deploy all three functions
supabase functions deploy invite-create
supabase functions deploy invite-validate --no-verify-jwt
supabase functions deploy invite-accept --no-verify-jwt

# Set secrets (if not already set by Supabase automatically)
supabase secrets set SUPABASE_URL=https://xxx.supabase.co
supabase secrets set SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

Note: `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are automatically available as environment variables in deployed Edge Functions. You only need to set custom secrets manually.

---

## 3. Row Level Security (RLS) Policies

Since the Edge Functions use the `service_role` key (which bypasses RLS), the RLS policies below protect against direct client-side access via the Supabase JS client. This is defense-in-depth.

```sql
-- Enable RLS
alter table public.invite_links enable row level security;

-- ============================================================
-- POLICY 1: Anyone can validate a link (anonymous SELECT)
-- Only exposes safe fields (no public keys, no IDs)
-- ============================================================
create policy "Anyone can validate invite links"
on public.invite_links
for select
to anon, authenticated
using (true);

-- NOTE: Even though SELECT is open, the Edge Function controls
-- which columns are returned. The RLS here is a safety net.
-- For tighter control, use a database view instead:

create view public.invite_links_public as
select
  code,
  creator_name,
  status,
  expires_at,
  created_at
from public.invite_links;

-- Then apply RLS on the view or restrict the base table:
-- (Alternative tighter policy -- only see your own invites)
-- create policy "Users see own invites"
-- on public.invite_links for select
-- to authenticated
-- using (creator_id = current_setting('request.jwt.claims')::json->>'sub');

-- ============================================================
-- POLICY 2: Only authenticated users can create invites
-- (Not strictly needed since Edge Functions use service_role,
--  but protects against direct client INSERT attempts)
-- ============================================================
create policy "Authenticated users can create invites"
on public.invite_links
for insert
to authenticated
with check (true);

-- ============================================================
-- POLICY 3: Nobody can UPDATE/DELETE via direct client access
-- All mutations go through Edge Functions with service_role
-- ============================================================
create policy "No direct updates"
on public.invite_links
for update
to anon, authenticated
using (false);

create policy "No direct deletes"
on public.invite_links
for delete
to anon, authenticated
using (false);
```

### RLS Strategy Rationale

| Approach | Pros | Cons |
|----------|------|------|
| Edge Functions + service_role (chosen) | Full control over validation logic, rate limiting, business rules | Must secure Edge Functions properly |
| Direct client + RLS only | Simpler architecture | Complex validation logic in SQL policies, harder to rate-limit |

The recommended approach: **all mutations go through Edge Functions** using `service_role` (bypasses RLS). RLS is a safety net preventing direct client-side abuse. The `anon` SELECT policy exists only so the Realtime subscription can work for unauthenticated users opening an invite link.

---

## 4. pg_cron Cleanup for Expired Links

### Enable the Extension

```sql
-- Enable pg_cron (done via Supabase Dashboard > Database > Extensions)
create extension if not exists pg_cron;

-- Grant usage to postgres role
grant usage on schema cron to postgres;
```

### Cleanup Function

```sql
create or replace function public.cleanup_expired_invites()
returns void
language plpgsql
security definer
as $$
declare
  rows_expired integer;
  rows_deleted integer;
begin
  -- Step 1: Mark pending invites that have expired
  update public.invite_links
  set status = 'expired'
  where status = 'pending'
    and expires_at < now();

  get diagnostics rows_expired = row_count;

  -- Step 2: Hard-delete invites older than 24 hours
  -- (keeps the table small; accepted invites are no longer needed
  --  after both parties have exchanged keys)
  delete from public.invite_links
  where expires_at < now() - interval '24 hours';

  get diagnostics rows_deleted = row_count;

  raise notice 'Invite cleanup: % expired, % deleted', rows_expired, rows_deleted;
end;
$$;
```

### Schedule the Cron Job

```sql
-- Run every 5 minutes -- aggressive cleanup for 60-min TTL links
select cron.schedule(
  'cleanup-expired-invites',    -- job name
  '*/5 * * * *',                -- every 5 minutes
  $$select public.cleanup_expired_invites()$$
);

-- Verify the job was created
select * from cron.job where jobname = 'cleanup-expired-invites';
```

### Monitor Job History

```sql
-- Check recent runs
select *
from cron.job_run_details
where jobid = (
  select jobid from cron.job
  where jobname = 'cleanup-expired-invites'
)
order by start_time desc
limit 10;
```

### Manage the Job

```sql
-- Pause/remove the job
select cron.unschedule('cleanup-expired-invites');

-- Clean up old job run history (optional, runs weekly)
select cron.schedule(
  'cleanup-cron-history',
  '0 3 * * 0',    -- Sunday at 3 AM
  $$delete from cron.job_run_details
    where end_time < now() - interval '7 days'$$
);
```

### TTL Strategy Comparison

| Approach | How it Works | Best For |
|----------|-------------|----------|
| **pg_cron (recommended)** | Scheduled DELETE/UPDATE every N minutes | Predictable load, simple, works in Supabase |
| Application-level check | `WHERE expires_at > now()` in every query | Immediate expiry enforcement at read time |
| Database trigger on INSERT | Delete old rows whenever a new row is inserted | Tables with frequent inserts |
| pg_ttl_index extension | Background worker with per-table TTL config | Not available on Supabase managed |

**Recommended combination:** Use pg_cron for bulk cleanup + application-level `WHERE expires_at > now()` checks in Edge Functions for real-time accuracy. This way, even if cron hasn't run yet, expired links are rejected immediately.

---

## 5. React Native Integration

### Installation

```bash
# For Expo-based React Native (QRChat uses RN 0.84)
npx expo install @supabase/supabase-js react-native-url-polyfill expo-sqlite

# Or for bare React Native
npm install @supabase/supabase-js react-native-url-polyfill
```

### Initialize the Supabase Client

File: `src/services/SupabaseService.ts`

```typescript
import 'react-native-url-polyfill/auto'
import { createClient, SupabaseClient } from '@supabase/supabase-js'
import AsyncStorage from '@react-native-async-storage/async-storage'

const SUPABASE_URL = 'https://YOUR_PROJECT_ID.supabase.co'
const SUPABASE_ANON_KEY = 'eyJ...'  // publishable anon key, safe for client

export const supabase: SupabaseClient = createClient(
  SUPABASE_URL,
  SUPABASE_ANON_KEY,
  {
    auth: {
      storage: AsyncStorage,
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: false,  // important for React Native
    },
  }
)
```

### Call Edge Functions from React Native

File: `src/services/InviteLinkService.ts`

```typescript
import { supabase } from './SupabaseService'

// For error handling
import {
  FunctionsHttpError,
  FunctionsRelayError,
  FunctionsFetchError,
} from '@supabase/supabase-js'

interface InviteCreateParams {
  creator_id: string
  creator_name: string
  creator_public_key: string
}

interface InviteCreateResponse {
  invite: {
    id: string
    code: string
    status: string
    expires_at: string
  }
  url: string
  expires_in_minutes: number
}

// --------------------------------------------------
// CREATE an invite link
// --------------------------------------------------
export async function createInviteLink(
  params: InviteCreateParams
): Promise<InviteCreateResponse> {
  const { data, error } = await supabase.functions.invoke('invite-create', {
    body: params,
    method: 'POST',
  })

  if (error) {
    if (error instanceof FunctionsHttpError) {
      const errorBody = await error.context.json()
      throw new Error(errorBody.error || 'Failed to create invite')
    }
    throw error
  }

  return data as InviteCreateResponse
}

// --------------------------------------------------
// VALIDATE an invite link (no auth needed)
// --------------------------------------------------
export async function validateInviteLink(
  code: string
): Promise<{ valid: boolean; creator_name?: string; remaining_minutes?: number; reason?: string }> {
  // Use fetch directly since this endpoint has --no-verify-jwt
  const response = await fetch(
    `https://YOUR_PROJECT_ID.supabase.co/functions/v1/invite-validate?code=${code}`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        // Include anon key for Supabase routing (not for auth)
        'apikey': 'YOUR_SUPABASE_ANON_KEY',
      },
    }
  )

  const data = await response.json()
  return data
}

// --------------------------------------------------
// ACCEPT an invite link
// --------------------------------------------------
export async function acceptInviteLink(params: {
  code: string
  acceptor_id: string
  acceptor_name: string
  acceptor_public_key: string
}): Promise<{
  success: boolean
  pairing: {
    creator_id: string
    creator_name: string
    creator_public_key: string
    acceptor_id: string
    acceptor_name: string
    acceptor_public_key: string
  }
}> {
  // Use fetch directly since this endpoint has --no-verify-jwt
  const response = await fetch(
    `https://YOUR_PROJECT_ID.supabase.co/functions/v1/invite-accept`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'apikey': 'YOUR_SUPABASE_ANON_KEY',
      },
      body: JSON.stringify(params),
    }
  )

  if (!response.ok) {
    const errorData = await response.json()
    throw new Error(errorData.error || 'Failed to accept invite')
  }

  return await response.json()
}
```

### Deep Link Handling

To handle `qrchat.app/invite/A1B2C3` URLs opening the app:

```typescript
import { Linking } from 'react-native'

// Register the URL scheme in app.json / Info.plist
// URL pattern: qrchat://invite/CODE or https://qrchat.app/invite/CODE

function useInviteDeepLink() {
  useEffect(() => {
    // Handle app opened from a link
    const handleUrl = ({ url }: { url: string }) => {
      const match = url.match(/invite\/([A-Fa-f0-9]+)/)
      if (match) {
        const code = match[1]
        navigateToInviteScreen(code)
      }
    }

    // Check if app was opened with a link
    Linking.getInitialURL().then((url) => {
      if (url) handleUrl({ url })
    })

    // Listen for new links while app is open
    const subscription = Linking.addEventListener('url', handleUrl)
    return () => subscription.remove()
  }, [])
}
```

---

## 6. Realtime Subscription

Alice creates an invite and wants to see **in real-time** when Bob accepts it.

### Enable Realtime on the Table

```sql
-- Already done in the schema above, but for reference:
alter publication supabase_realtime add table public.invite_links;
```

Also enable Realtime in the Supabase Dashboard: **Database > Replication > Enable** for the `invite_links` table, selecting UPDATE events at minimum.

### React Native Realtime Hook

File: `src/hooks/useInviteRealtime.ts`

```typescript
import { useEffect, useState, useRef } from 'react'
import { supabase } from '../services/SupabaseService'
import { RealtimeChannel } from '@supabase/supabase-js'

interface InviteRealtimeState {
  status: 'pending' | 'accepted' | 'expired' | 'revoked'
  acceptor_name?: string
  acceptor_public_key?: string
}

export function useInviteRealtime(inviteId: string) {
  const [state, setState] = useState<InviteRealtimeState>({
    status: 'pending',
  })
  const channelRef = useRef<RealtimeChannel | null>(null)

  useEffect(() => {
    if (!inviteId) return

    // Subscribe to changes on this specific invite row
    const channel = supabase
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
          const updated = payload.new as any
          console.log('Invite updated:', updated.status)

          setState({
            status: updated.status,
            acceptor_name: updated.acceptor_name,
            acceptor_public_key: updated.acceptor_public_key,
          })
        }
      )
      .subscribe((status) => {
        console.log('Realtime subscription status:', status)
      })

    channelRef.current = channel

    // Cleanup on unmount
    return () => {
      if (channelRef.current) {
        supabase.removeChannel(channelRef.current)
      }
    }
  }, [inviteId])

  return state
}
```

### Usage in a Screen Component

```tsx
import React from 'react'
import { View, Text, ActivityIndicator } from 'react-native'
import { useInviteRealtime } from '../hooks/useInviteRealtime'

function WaitingForAcceptScreen({ inviteId, inviteUrl }: Props) {
  const { status, acceptor_name, acceptor_public_key } =
    useInviteRealtime(inviteId)

  if (status === 'accepted') {
    // Bob accepted -- initiate key exchange and navigate to chat
    return (
      <View>
        <Text>{acceptor_name} accepted your invite!</Text>
        <Text>Establishing encrypted connection...</Text>
      </View>
    )
  }

  if (status === 'expired') {
    return (
      <View>
        <Text>This invite has expired.</Text>
        <Button title="Create New Invite" onPress={createNewInvite} />
      </View>
    )
  }

  // Still pending
  return (
    <View>
      <Text>Share this link with your contact:</Text>
      <Text selectable>{inviteUrl}</Text>
      <ActivityIndicator />
      <Text>Waiting for someone to accept...</Text>
      <CountdownTimer expiresAt={expiresAt} />
    </View>
  )
}
```

### Realtime Security Note

For Realtime `postgres_changes` to work, the subscribing client must have SELECT permission via RLS. The `anon` SELECT policy defined in Section 3 ensures this works even for unauthenticated clients. If you restrict the SELECT policy, only the invite creator will receive Realtime updates (which may actually be the desired behavior).

---

## 7. Architecture Overview

### Full Flow

```
Alice (creator)                    Supabase                         Bob (acceptor)
     |                                |                                  |
     |-- POST /invite-create -------->|                                  |
     |<-- { code, url, expires } -----|                                  |
     |                                |                                  |
     |-- subscribe(invite-{id}) ----->|                                  |
     |   [Realtime channel open]      |                                  |
     |                                |                                  |
     |-- Share URL via SMS/QR --------|--------------------------------->|
     |                                |                                  |
     |                                |<-- GET /invite-validate?code ----|
     |                                |--- { valid, creator_name } ----->|
     |                                |                                  |
     |                                |<-- POST /invite-accept ----------|
     |                                |--- { pairing: keys } ----------->|
     |                                |                                  |
     |<-- Realtime: status=accepted --|                                  |
     |    + acceptor_public_key       |                                  |
     |                                |                                  |
     [Both derive shared secret from exchanged public keys via TweetNaCl]
     |                                |                                  |
     [--- E2E encrypted P2P chat via WebRTC signaling ---]
```

### Security Considerations

1. **Rate limiting**: The `invite-create` function limits each user to 5 active invites. Consider adding IP-based rate limiting via Supabase's built-in rate limiter or a Deno middleware.

2. **Code entropy**: 6 random bytes = 12 hex chars = 2^48 possibilities (~281 trillion). Brute-forcing at 1000 req/sec would take ~8,900 years. For extra safety, add rate limiting on `invite-validate`.

3. **No auth on validate/accept**: These endpoints use `--no-verify-jwt` intentionally. Bob does not need a Supabase account to accept an invite. The security comes from:
   - The code's randomness (unguessable)
   - The 60-minute TTL (short window)
   - Single-use (status changes to `accepted` atomically)

4. **Optimistic concurrency**: The accept function uses `WHERE status = 'pending'` in the UPDATE to prevent race conditions where two people try to accept the same invite simultaneously.

5. **Public key transport**: The invite carries `creator_public_key`, and acceptance returns `acceptor_public_key`. This replaces the QR code scanning step in QRChat's current flow, enabling remote contact addition.

6. **Service role key safety**: The `SUPABASE_SERVICE_ROLE_KEY` is only used server-side in Edge Functions. It is never exposed to the client. The React Native app only has the `anon` key.

### Cost Estimate (Supabase Free Tier)

| Resource | Free Tier Limit | Invite System Usage |
|----------|----------------|-------------------|
| Database | 500 MB | Negligible (rows are TTL-deleted) |
| Edge Function invocations | 500K/month | ~3 calls per invite flow |
| Realtime connections | 200 concurrent | 1 per active "waiting" screen |
| pg_cron jobs | No explicit limit | 1 job, runs every 5 min |

The invite link system fits comfortably within Supabase's free tier for a small-to-medium user base.

---

## Sources

- [Supabase Edge Functions Documentation](https://supabase.com/docs/guides/functions)
- [Edge Functions Quickstart](https://supabase.com/docs/guides/functions/quickstart)
- [Edge Functions CORS Guide](https://supabase.com/docs/guides/functions/cors)
- [Edge Functions HTTP Methods / Routing](https://supabase.com/docs/guides/functions/http-methods)
- [Securing Edge Functions](https://supabase.com/docs/guides/functions/auth)
- [Edge Functions Environment Variables](https://supabase.com/docs/guides/functions/secrets)
- [Official Edge Function Example: select-from-table-with-auth-rls](https://github.com/supabase/supabase/blob/master/examples/edge-functions/supabase/functions/select-from-table-with-auth-rls/index.ts)
- [Row Level Security Guide](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [Supabase RLS Complete Guide 2026](https://vibeappscanner.com/supabase-row-level-security)
- [Anonymous Sign-Ins](https://supabase.com/docs/guides/auth/auth-anonymous)
- [pg_cron Extension](https://supabase.com/docs/guides/database/extensions/pg_cron)
- [Supabase Cron Quickstart](https://supabase.com/docs/guides/cron/quickstart)
- [Supabase Cron Documentation](https://supabase.com/docs/guides/cron)
- [Postgres as a Cron Server (blog)](https://supabase.com/blog/postgres-as-a-cron-server)
- [Subscribing to Database Changes (Realtime)](https://supabase.com/docs/guides/realtime/subscribing-to-database-changes)
- [Supabase JS: Subscribe to Channel](https://supabase.com/docs/reference/javascript/subscribe)
- [Supabase JS: functions.invoke()](https://supabase.com/docs/reference/javascript/functions-invoke)
- [Use Supabase with Expo React Native](https://supabase.com/docs/guides/getting-started/quickstarts/expo-react-native)
- [Expo: Using Supabase](https://docs.expo.dev/guides/using-supabase/)
- [Edge Functions with React Native Boilerplate](https://docs.launchtoday.dev/react-native-cli/supabase/edge-functions)
- [Working with Supabase Edge Functions (Basejump blog)](https://usebasejump.com/blog/working-with-supabase-edge-functions)
- [TTL in PostgreSQL (Medium)](https://medium.com/@tihomir.manushev/implementing-redis-like-ttl-in-postgresql-6d7dedd51bef)
- [Automatically Expire Rows in Postgres](https://schinckel.net/2021/09/09/automatically-expire-rows-in-postgres/)
- [Time-based Retention Strategies in Postgres](https://blog.sequinstream.com/time-based-retention-strategies-in-postgres/)
- [pg_ttl_index Extension](https://pgxn.org/dist/pg_ttl_index/)
- [Supabase Invite Link Guide (Restack)](https://www.restack.io/docs/supabase-knowledge-supabase-invite-link-guide)
