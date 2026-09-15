import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { requireAdmin } from '@/lib/supabase/server';

export const dynamic = 'force-dynamic';

export default async function TeachersPage() {
  const { supabase, user } = await requireAdmin(); if (!user || !supabase) return null;
  const { data: teachers, error } = await supabase.from('teachers').select('*').order('name');
  return <main className="mx-auto max-w-7xl px-5 py-8"><div className="mb-6 flex items-center gap-3"><Link href="/dashboard" className="rounded-lg border border-slate-800 p-2"><ArrowLeft size={17}/></Link><div><h1 className="text-2xl font-bold">Teachers & Faculty</h1><p className="text-sm text-slate-500">Manage instructor profiles shown on the public website.</p></div></div>
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">{(teachers ?? []).map((t: any)=><article key={t.id} className="card p-5"><div className="flex items-start gap-4">{(t.avatar_url || t.image_url) ? <img src={t.avatar_url || t.image_url} alt="" className="h-16 w-16 rounded-2xl object-cover"/> : <div className="grid h-16 w-16 place-items-center rounded-2xl bg-indigo-500/10 text-xl text-indigo-300">{String(t.name || '?').slice(0,1)}</div>}<div><h2 className="font-semibold">{t.name || 'Unnamed teacher'}</h2><p className="text-sm text-indigo-300">{t.role || t.designation || 'Faculty'}</p><p className="mt-1 text-xs text-slate-500">{t.subject || 'General'}</p></div></div><p className="mt-4 line-clamp-3 text-sm text-slate-400">{t.bio || 'No bio added yet.'}</p></article>)}{!teachers?.length && <div className="card p-10 text-center text-slate-500 md:col-span-2 lg:col-span-3">No teachers found.</div>}</div>{error && <p className="mt-4 text-sm text-red-300">Could not load teachers: {error.message}</p>}</main>;
}
