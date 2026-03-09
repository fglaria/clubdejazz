# CLAUDE.md - Club de Jazz Intranet

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

- **Render service**: `clubdejazz` (https://clubdejazz.onrender.com)
- **Repo**: https://github.com/fglaria/clubdejazz
- **Auto-deploy**: On push to main branch

### Render Config

- Backend: `rootDir: backend`, Python runtime
- Frontend: `rootDir: frontend`, Static site

## Key Business Rules

See `docs/plans/2026-01-21-jazz-club-webapp-design.md` for full details.

| Membership | Fee | Voting |
|------------|-----|--------|
| Numerario | 0.10-0.50 UTM | Yes |
| Honorario | Free | Voice only |
| Fundador | 0.10-0.50 UTM | Yes |
| Estudiante | 50% discount | Yes (if 18+) |
