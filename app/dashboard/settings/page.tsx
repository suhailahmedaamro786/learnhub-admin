import Link from 'next/link';
import { ArrowLeft, Save } from 'lucide-react';
import { requireAdmin } from '@/lib/supabase/server';
import { saveBranding } from '../actions';

export const dynamic = 'force-dynamic';

export default async function SettingsPage() {
  const { supabase, user } = await requireAdmin(); if (!user || !supabase) return null;
  const { data } = await supabase.from('system_settings').select('*').limit(1).maybeSingle();
  return <main className="mx-auto max-w-3xl px-5 py-8"><div className="mb-6 flex items-center gap-3"><Link href="/dashboard" className="rounded-lg border border-slate-800 p-2"><ArrowLeft size={17}/></Link><div><h1 className="text-2xl font-bold">Website settings</h1><p className="text-sm text-slate-500">Control public branding without changing code.</p></div></div>
    <div className="card p-6"><form action={saveBranding} className="space-y-4"><input type="hidden" name="id" value={data?.id || '1'}/><label className="block text-sm text-slate-300">Institute name<input className="input mt-2" name="institute_name" defaultValue={data?.institute_name || 'LearnHub'}/></label><label className="block text-sm text-slate-300">Footer text<input className="input mt-2" name="footer_text" defaultValue={data?.footer_text || '© LearnHub. All rights reserved.'}/></label><label className="block text-sm text-slate-300">Contact email<input className="input mt-2" name="contact_email" type="email" defaultValue={data?.contact_email || ''}/></label><button className="flex items-center gap-2 rounded-xl bg-indigo-500 px-5 py-3 font-semibold hover:bg-indigo-400"><Save size={17}/> Save settings</button></form></div>
  </main>;
}
