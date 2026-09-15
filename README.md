# LearnHub Admin

Production-ready Next.js admin dashboard for the LearnHub coaching website. It uses Supabase Auth for sign-in and a **server-only Supabase service-role key** for verified admin operations.

## Features

- Secure email/password admin login
- `profiles.role = admin` authorization check
- Dashboard metrics for students, courses, admissions, teachers and support tickets
- Course creation and publishing status
- Faculty overview
- Admissions review/status workflow
- Website branding settings
- Responsive dark admin UI
- Server-side mutations and cache revalidation

## Local setup

```bash
npm install
cp .env.example .env.local
npm run dev
```

Required variables:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY` — **server only; never prefix with `NEXT_PUBLIC_`**

Create an admin user in Supabase Auth, then make sure its matching `profiles` row has `role = 'admin'`.

## Deploy on Vercel

Set the same three environment variables for Production, Preview and Development as needed. Vercel will run `npm run build` automatically.

> The legacy Streamlit files remain in the repository for reference/backup. The deployed web admin is now the Next.js application at `/dashboard`.
