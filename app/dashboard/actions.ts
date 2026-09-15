'use server';

import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';
import { requireAdmin } from '@/lib/supabase/server';

function text(v: FormDataEntryValue | null) { return String(v ?? '').trim(); }

export async function createCourse(formData: FormData) {
  const { supabase } = await requireAdmin(); if (!supabase) redirect('/login');
  const payload = { title: text(formData.get('title')), description: text(formData.get('description')) || null, price: Number(formData.get('price') || 0), duration_weeks: Number(formData.get('duration_weeks') || 0) || null, status: text(formData.get('status')) || 'draft', thumbnail_url: text(formData.get('thumbnail_url')) || null };
  const { error } = await supabase.from('courses').insert(payload);
  if (error) throw new Error(`Course could not be created: ${error.message}`);
  revalidatePath('/dashboard'); revalidatePath('/dashboard/courses');
}

export async function updateAdmissionStatus(formData: FormData) {
  const { supabase } = await requireAdmin(); if (!supabase) redirect('/login');
  const id = text(formData.get('id')); const status = text(formData.get('status'));
  if (!id || !status) return;
  const { error } = await supabase.from('admissions').update({ status }).eq('id', id);
  if (error) throw new Error(`Admission update failed: ${error.message}`);
  revalidatePath('/dashboard'); revalidatePath('/dashboard/admissions');
}

export async function saveBranding(formData: FormData) {
  const { supabase } = await requireAdmin(); if (!supabase) redirect('/login');
  const id = text(formData.get('id')) || '1';
  const payload = { institute_name: text(formData.get('institute_name')), footer_text: text(formData.get('footer_text')), contact_email: text(formData.get('contact_email')) };
  const { error } = await supabase.from('system_settings').update(payload).eq('id', id);
  if (error) throw new Error(`Branding update failed: ${error.message}`);
  revalidatePath('/dashboard/settings'); revalidatePath('/dashboard');
}
