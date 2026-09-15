import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { requireAdmin } from '@/lib/supabase/server';
import { updateAdmissionStatus } from '../actions';

export const dynamic = 'force-dynamic';

export default async function AdmissionsPage() {
  const { supabase, user } = await requireAdmin(); if (!user || !supabase) return null;
  const { data: admissions, error } = await supabase.from('admissions').select('*').order('created_at', { ascending: false });
  return <main className="mx-auto max-w-7xl px-5 py-8"><div className="mb-6 flex items-center gap-3"><Link href="/dashboard" className="rounded-lg border border-slate-800 p-2"><ArrowLeft size={17}/></Link><div><h1 className="text-2xl font-bold">Admissions</h1><p className="text-sm text-slate-500">Review applications and update their status.</p></div></div>
    <div className="card overflow-hidden"><div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="bg-slate-900/60 text-xs uppercase text-slate-500"><tr><th className="px-5 py-3">Applicant</th><th className="px-5 py-3">Contact</th><th className="px-5 py-3">Course</th><th className="px-5 py-3">Status</th><th className="px-5 py-3">Action</th></tr></thead><tbody>{(admissions ?? []).map((a: any)=><tr key={a.id} className="border-t border-slate-800"><td className="px-5 py-4 font-medium">{a.name || a.full_name || a.student_name || 'Applicant'}</td><td className="px-5 py-4 text-slate-400">{a.email || a.phone || '—'}</td><td className="px-5 py-4 text-slate-400">{a.course_name || a.course || a.course_id || '—'}</td><td className="px-5 py-4"><span className="rounded-full bg-indigo-500/10 px-2.5 py-1 text-xs text-indigo-300">{a.status || 'pending'}</span></td><td className="px-5 py-4"><form action={updateAdmissionStatus} className="flex gap-2"><input type="hidden" name="id" value={a.id}/><select className="rounded-lg border border-slate-700 bg-slate-900 px-2 py-2 text-xs" name="status" defaultValue={a.status || 'pending'}><option value="pending">Pending</option><option value="approved">Approved</option><option value="rejected">Rejected</option><option value="contacted">Contacted</option></select><button className="rounded-lg bg-indigo-500 px-3 py-2 text-xs font-semibold">Save</button></form></td></tr>)}{!admissions?.length && <tr><td colSpan={5} className="px-5 py-12 text-center text-slate-500">No applications yet.</td></tr>}</tbody></table></div>{error && <p className="p-4 text-sm text-red-300">Could not load admissions: {error.message}</p>}</div></main>;
}
