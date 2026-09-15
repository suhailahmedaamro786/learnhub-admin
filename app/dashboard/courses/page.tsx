import Link from 'next/link';
import { ArrowLeft, Plus } from 'lucide-react';
import { requireAdmin } from '@/lib/supabase/server';
import { createCourse } from '../actions';

export const dynamic = 'force-dynamic';

export default async function CoursesPage() {
  const { supabase, user } = await requireAdmin(); if (!user || !supabase) return null;
  const { data: courses, error } = await supabase.from('courses').select('*').order('created_at', { ascending: false });
  const { data: teachers } = await supabase.from('teachers').select('id,name').order('name');

  return <main className="mx-auto max-w-7xl px-5 py-8"><div className="mb-6 flex items-center gap-3"><Link href="/dashboard" className="rounded-lg border border-slate-800 p-2"><ArrowLeft size={17}/></Link><div><h1 className="text-2xl font-bold">Courses</h1><p className="text-sm text-slate-500">Create and manage your public course catalog.</p></div></div>
    <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
      <div className="card overflow-hidden"><div className="border-b border-slate-800 p-5 font-semibold">Course catalog ({courses?.length ?? 0})</div><div className="divide-y divide-slate-800">{(courses ?? []).map((c: any)=><div key={c.id} className="flex items-center justify-between gap-4 p-5"><div><div className="font-medium">{c.title || 'Untitled'}</div><div className="mt-1 text-xs text-slate-500">{c.duration_weeks ? `${c.duration_weeks} weeks · ` : ''}PKR {Number(c.price || 0).toLocaleString()}</div></div><span className={`rounded-full px-2.5 py-1 text-xs ${c.status === 'published' || c.status === 'active' ? 'bg-emerald-500/10 text-emerald-300' : 'bg-amber-500/10 text-amber-300'}`}>{c.status || 'draft'}</span></div>)}{!courses?.length && <div className="p-10 text-center text-slate-500">No courses found.</div>}</div>{error && <p className="p-4 text-sm text-red-300">Could not load courses: {error.message}</p>}</div>
      <div className="card p-5"><div className="mb-4 flex items-center gap-2 font-semibold"><Plus size={18}/> Add course</div><form action={createCourse} className="space-y-3"><input className="input" name="title" required placeholder="Course title"/><textarea className="input min-h-24" name="description" placeholder="Description"/><input className="input" name="price" type="number" min="0" placeholder="Price (PKR)"/><input className="input" name="duration_weeks" type="number" min="1" placeholder="Duration in weeks"/><select className="input" name="status" defaultValue="draft"><option value="draft">Draft</option><option value="published">Published</option><option value="active">Active</option></select><input className="input" name="thumbnail_url" placeholder="Thumbnail URL (optional)"/><button className="w-full rounded-xl bg-indigo-500 px-4 py-3 font-semibold hover:bg-indigo-400">Create course</button></form><p className="mt-3 text-xs text-slate-500">Teacher assignment and image uploads can be added once your final course schema is confirmed.</p></div>
    </div></main>;
}
