'use client';
import { LogOut } from 'lucide-react';
import { createClient } from '@/lib/supabase/client';
import { useRouter } from 'next/navigation';

export default function SignOutButton() {
  const router = useRouter();
  async function signOut() { await createClient().auth.signOut(); router.replace('/login'); router.refresh(); }
  return <button onClick={signOut} className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-400 hover:bg-white/5 hover:text-white"><LogOut size={16}/> Logout</button>;
}
