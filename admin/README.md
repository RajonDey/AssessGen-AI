# AssessGen Admin

Internal Next.js dashboard for generation, review, and content bank browsing.

## Setup

```bash
cp .env.example .env.local
npm install
```

## Dev

Requires the backend API on port 8000 (see repo root `make dev`).

The admin app **proxies** `/api/*` to the backend by default, so you do not need CORS or a
cross-origin `NEXT_PUBLIC_API_URL` in local dev. Leave `NEXT_PUBLIC_API_URL` empty in `.env.local`.

```bash
npm run dev
```

Open [http://localhost:3000/login](http://localhost:3000/login).

Default seeded credentials (after `make seed`):

- Email: `admin@assessgen.local`
- Password: `admin`

## Pages

| Route | Purpose |
|-------|---------|
| `/login` | Email + password → JWT |
| `/generate` | Start reading runs, poll status |
| `/review` | Queue + approve/reject paused runs |
| `/bank` | Browse passages and items |
