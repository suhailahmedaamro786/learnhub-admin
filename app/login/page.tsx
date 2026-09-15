'use client';

import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';
import { LogIn, ShieldCheck } from 'lucide-react';
import { createClient } from '@/lib/supabase/client';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault(); setLoading(true); setError('');
    const supabase = createClient();
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) { setError('Invalid email or password.'); setLoading(false); return; }
    router.replace('/dashboard'); router.refresh();
  }

  return <main className="min-h-screen grid place-items-center px-4">
    <div className="card w-full max-w-md p-8 shadow-2xl shadow-black/20">
      <div className="mb-7 flex items-center gap-3"><div className="rounded-xl bg-indigo-500/15 p-3 text-indigo-300"><ShieldCheck /></div><div><h1 className="text-2xl font-bold">LearnHub Admin</h1><p className="text-sm text-slate-400">Secure administration portal</p></div></div>
      <form onSubmit={submit} className="space-y-4">
        <input className="input" type="email" required placeholder="Admin email" value={email} onChange={e => setEmail(e.target.value)} />
        <input className="input" type="password" required placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} />
        {error && <p className="rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-300">{error}</p>}
        <button disabled={loading} className="flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-500 px-4 py-3 font-semibold hover:bg-indigo-400 disabled:opacity-50"><LogIn size={18}/>{loading ? 'Signing in…' : 'Sign in'}</button>
      </form>
      <p className="mt-5 text-xs text-slate-500">Only users with <b>profiles.role = admin</b> can access the dashboard.</p>
    </div>
  </main>;
}
