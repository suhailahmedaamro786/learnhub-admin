import Link from 'next/link';
import { redirect } from 'next/navigation';
import { BookOpen, GraduationCap, Users, ClipboardList, Settings, MessageSquare, ArrowUpRight } from 'lucide-react';
import { requireAdmin } from '@/lib/supabase/server';
import SignOutButton from './SignOutButton';

export const dynamic = 'force-dynamic';

async function count(supabase: any, table: string, filter?: (q: any) => any) {
  try {
    let q = supabase.from(table).select('*', { count: 'exact', head: true });
    if (filter) q = filter(q);
    const r = await q; return r.count ?? 0;
  } catch { return 0; }
}

export default async function Dashboard() {
  const { supabase, user, profile } = await requireAdmin();
  if (!user) redirect('/login');
  if (!profile) redirect('/login');

  const [students, courses, admissions, teachers, tickets] = await Promise.all([
    count(supabase, 'profiles', q => q.eq('role', 'student')),
    count(supabase, 'courses'),
    count(supabase, 'admissions'),
    count(supabase, 'teachers'),
    count(supabase, 'support_tickets', q => q.in('status', ['open', 'in_progress'])),
  ]);

  const { data: recentAdmissions } = await supabase.from('admissions').select('*').order('created_at', { ascending: false }).limit(8);

  const cards = [
    ['Students', students, Users], ['Courses', courses, BookOpen], ['Admissions', admissions, ClipboardList], ['Teachers', teachers, GraduationCap], ['Open Tickets', tickets, MessageSquare],
  ] as const;

  return <main className="min-h-screen">
    <header className="sticky top-0 z-20 border-b border-slate-800/80 bg-[#070b14]/90 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4">
        <div><div className="font-bold">LearnHub <span className="text-indigo-400">Admin</span></div><div className="text-xs text-slate-500">{profile.full_name || profile.name || user.email}</div></div>
        <SignOutButton />
      </div>
    </header>
    <div className="mx-auto max-w-7xl px-5 py-8">
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4"><div><p className="text-sm text-indigo-300">Control center</p><h1 className="mt-1 text-3xl font-bold">Dashboard</h1><p className="mt-2 text-slate-400">Manage your coaching website, students and admissions from one place.</p></div><Link href="/dashboard/settings" className="flex items-center gap-2 rounded-xl border border-slate-700 px-4 py-2 text-sm hover:bg-white/5"><Settings size={16}/> Settings</Link></div>
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {cards.map(([label, value, Icon]) => <div key={label} className="card p-5"><div className="mb-4 flex items-center justify-between"><span className="text-sm text-slate-400">{label}</span><Icon size={19} className="text-indigo-300"/></div><div className="text-3xl font-bold">{value}</div></div>)}
      </section>
      <section className="mt-8 grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="card overflow-hidden"><div className="flex items-center justify-between border-b border-slate-800 p-5"><div><h2 className="font-semibold">Recent admissions</h2><p className="text-xs text-slate-500">Latest applications received</p></div><Link href="/dashboard/admissions" className="text-sm text-indigo-300">View all <ArrowUpRight className="inline" size={14}/></Link></div>
          <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="text-xs uppercase text-slate-500"><tr><th className="px-5 py-3">Applicant</th><th className="px-5 py-3">Course</th><th className="px-5 py-3">Status</th><th className="px-5 py-3">Date</th></tr></thead><tbody>{(recentAdmissions ?? []).map((a: any) => <tr key={a.id} className="border-t border-slate-800/70"><td className="px-5 py-3 font-medium">{a.name || a.full_name || a.student_name || 'Applicant'}</td><td className="px-5 py-3 text-slate-400">{a.course_name || a.course || a.course_id || '—'}</td><td className="px-5 py-3"><span className="rounded-full bg-indigo-500/10 px-2.5 py-1 text-xs text-indigo-300">{a.status || 'pending'}</span></td><td className="px-5 py-3 text-slate-500">{a.created_at ? new Date(a.created_at).toLocaleDateString() : '—'}</td></tr>)}{!recentAdmissions?.length && <tr><td colSpan={4} className="px-5 py-10 text-center text-slate-500">No admissions yet.</td></tr>}</tbody></table></div>
        </div>
        <div className="card p-5"><h2 className="font-semibold">Quick actions</h2><div className="mt-4 grid gap-2">{[['Courses','/dashboard/courses',BookOpen],['Teachers','/dashboard/teachers',GraduationCap],['Admissions','/dashboard/admissions',ClipboardList],['Branding','/dashboard/settings',Settings]].map(([label,href,Icon]: any)=><Link key={label} href={href} className="flex items-center justify-between rounded-xl border border-slate-800 p-3 text-sm hover:border-indigo-500/40 hover:bg-white/[.03]"><span className="flex items-center gap-3"><Icon size={17} className="text-indigo-300"/>{label}</span><ArrowUpRight size={15}/></Link>)}</div></div>
      </section>
    </div>
  </main>;
}
