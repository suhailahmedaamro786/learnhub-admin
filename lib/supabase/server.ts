import { createServerClient } from '@supabase/ssr';
import { createClient as createSupabaseClient } from '@supabase/supabase-js';
import { cookies } from 'next/headers';

export function createClient() {
  const cookieStore = cookies();
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) throw new Error('Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY');
  return createServerClient(url, key, {
    cookies: {
      getAll: () => cookieStore.getAll(),
      setAll(values) { try { values.forEach(({ name, value, options }) => cookieStore.set(name, value, options)); } catch {} },
    },
  });
}

/** Server-only client. Never import this from a Client Component. */
export function createAdminClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !serviceKey) throw new Error('Missing server-only SUPABASE_SERVICE_ROLE_KEY');
  return createSupabaseClient(url, serviceKey, { auth: { autoRefreshToken: false, persistSession: false } });
}

export async function requireAdmin() {
  const authClient = createClient();
  const { data: { user } } = await authClient.auth.getUser();
  if (!user) return { supabase: null, user: null, profile: null };

  const admin = createAdminClient();
  const { data: profile } = await admin.from('profiles').select('id, full_name, name, role').eq('id', user.id).maybeSingle();
  const role = String(profile?.role ?? '').toLowerCase();
  if (role !== 'admin') return { supabase: null, user, profile: null };
  return { supabase: admin, user, profile };
}
