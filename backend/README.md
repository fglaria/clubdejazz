# Club de Jazz API

Backend API for Club de Jazz de Concepción member management system.

## Tech Stack

- **Framework:** FastAPI
- **Database:** PostgreSQL (Supabase)
- **ORM:** SQLAlchemy (async)
- **Auth:** JWT tokens
- **Migrations:** Alembic

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Get JWT token |
| GET | `/api/users/me` | Get profile |
| PUT | `/api/users/me` | Update profile |
| GET | `/api/memberships/types` | List membership types |
| POST | `/api/memberships/apply` | Apply for membership |
| GET | `/api/memberships/me` | My memberships |
| GET | `/api/fee-rates/current` | Current fee rates |
| GET | `/api/events` | Public events |
| GET | `/health` | Health check |

## Local Development

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Create .env from template
cp .env.example .env
# Edit .env with your database credentials

# Run migrations
alembic upgrade head

# Seed initial data
python -m app.services.seed

# Start server
uvicorn app.main:app --reload
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `JWT_SECRET_KEY` | Secret for signing JWT tokens |
| `JWT_ALGORITHM` | JWT algorithm (default: HS256) |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry (default: 30) |
| `DEBUG` | Enable debug mode (default: false) |

## Deployment

Deployed on [Render](https://render.com) with auto-deploy on push to main.

- **URL:** https://clubdejazz.onrender.com
- **Docs:** https://clubdejazz.onrender.com/docs
