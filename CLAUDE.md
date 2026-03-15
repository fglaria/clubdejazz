# CLAUDE.md - Club de Jazz Intranet

> **Note:** Only the `intranet/` folder is a git repo. Parent `clubdejazz/` is not tracked.

## Overview

Member management webapp for Club de Jazz de Concepción.

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI (Python 3.11+) |
| Frontend | Next.js 14 (React) |
| Database | Supabase PostgreSQL |
| Auth | Custom JWT |
| Deploy | Render |

## Project Structure

```
intranet/
├── backend/          # FastAPI app
│   └── app/
│       ├── api/      # Route handlers
│       ├── models/   # SQLAlchemy models
│       ├── schemas/  # Pydantic schemas
│       ├── core/     # Auth, security
│       └── services/ # Business logic
├── frontend/         # Next.js app
│   └── src/
│       ├── app/      # App Router pages
│       ├── components/
│       └── lib/      # API client, utils
└── docs/             # Design docs (not in git)
```

## Development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Database

Supabase PostgreSQL. Credentials stored in `~/.claude/credentials/supabase-clubdejazz.env`.

Connection test:
```bash
source ~/.claude/credentials/supabase-clubdejazz.env
psql "$DATABASE_URL" -c "SELECT version();"
```

## Deployment

- **Repo**: https://github.com/fglaria/clubdejazz
- **Auto-deploy**: On push to main branch

### Render Services (workspace: ClubDeJazz, ID: tea-d6mp5275r7bs73cj9790)

| Service | ID | URL | rootDir | Runtime |
|---------|-----|-----|---------|---------|
| clubdejazz (backend) | srv-d6mp6qlm5p6s73fvlun0 | https://clubdejazz.onrender.com | `backend` | Python |
| clubdejazz-web (frontend) | srv-d6olck15pdvs73em3psg | https://clubdejazz-web.onrender.com | `frontend` | Node |

**When checking Render:** Always select workspace `ClubDeJazz` (ID: `tea-d6mp5275r7bs73cj9790`) directly — never list workspaces or ask which one.

### Environment Variables

| Service | Key | Value |
|---------|-----|-------|
| Frontend | `NEXT_PUBLIC_API_URL` | `https://clubdejazz.onrender.com` |

## Admin Pages

The frontend includes admin pages at `/admin/*`:

| Route | Description |
|-------|-------------|
| `/admin/members` | List memberships, filter by status, approve/reject pending, create new member (user+membership), assign membership to existing user, reset password |
| `/admin/payments` | List payments, filter by status, confirm/reject pending |
| `/admin/events` | Full CRUD for events, publish/unpublish toggle |

## Development Workflow

New features follow a two-phase approach:

1. **MVP first**: Write fast, functional code to get the feature working. Prioritize correctness and speed of delivery over architecture. Direct DB queries in endpoints, minimal abstraction, inline logic — all acceptable.
2. **Manual review then refactor**: The user reviews the working code and decides when/if to refactor it. Claude should not preemptively refactor MVP code unless asked.

**Existing examples**:
- `payments/`, `events/` — MVP-style (direct logic in endpoints, acceptable for now)
- `admin/`, `memberships/` — already refactored with service layer pattern

When implementing new features, default to MVP style unless the user explicitly asks for the service layer pattern.

## Known Issues

### bcrypt/passlib compatibility
- **Issue**: passlib 1.7.4 is incompatible with bcrypt >= 4.1.0
- **Cause**: bcrypt 4.1 added strict 72-byte password limit; passlib uses >72 byte test strings internally
- **Fix**: Pin `bcrypt>=4.0.0,<4.1.0` in requirements.txt

## Key Business Rules

See `docs/plans/2026-01-21-jazz-club-webapp-design.md` for full details.

| Membership | Fee | Voting |
|------------|-----|--------|
| Numerario | 0.10-0.50 UTM | Yes |
| Honorario | Free | Voice only |
| Fundador | 0.10-0.50 UTM | Yes |
| Estudiante | 50% discount | Yes (if 18+) |
