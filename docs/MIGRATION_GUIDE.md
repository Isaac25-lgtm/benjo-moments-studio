# Migration Guide — Benjo Moments Photography System

This guide covers setting up Postgres locally, running Alembic migrations,
migrating existing SQLite data, and deploying to Render with Neon.

---

## 1. Environment Variables

Copy `.env.example` to `.env` and fill in:

```env
# SQLite fallback (local dev, no Postgres needed)
USE_SQLITE_FALLBACK=true

# OR: Replace with your local Postgres URL
DATABASE_URL=postgresql+psycopg2://benjo:benjo@localhost:5432/benjo_moments

# OR: Neon (production)
DATABASE_URL=postgresql+psycopg2://neondb_owner:<password>@<host>.neon.tech/neondb?sslmode=require

SECRET_KEY=your-long-random-secret-key
FLASK_ENV=development
TEST_AUTH_MODE=true
```

---

## 2. Run Postgres Locally (Docker)

```bash
docker run -d \
  --name benjo-postgres \
  -e POSTGRES_DB=benjo_moments \
  -e POSTGRES_USER=benjo \
  -e POSTGRES_PASSWORD=benjo \
  -p 5432:5432 \
  postgres:16-alpine
```

---

## 3. Run Alembic Migrations

> Migrations run **automatically** at app startup via `app.py → run_migrations()`.
> You can also run them manually:

```bash
# Apply all migrations
python -m alembic upgrade head

# Check current revision
python -m alembic current

# Stamp an existing DB without running migrations (e.g. for an existing SQLite DB)
python -m alembic stamp head
```

---

## 4. Migrate SQLite Data to Postgres

Only needed once when switching from existing SQLite data to Postgres:

```bash
# 1. Set DATABASE_URL to point to target Postgres (edit .env)
# 2. Ensure alembic upgrade head has already been run on Postgres
# 3. Run the migration script

python scripts/migrate_sqlite_to_postgres.py
```

The script is **idempotent** for users and website_settings (skips if already exists).
For tables like income/expenses/gallery, run it once on a clean Postgres database.

---

## 5. Deploy to Render with Neon

### Step 1: Create Neon database
1. Go to [neon.tech](https://neon.tech) → create a new project
2. Copy the **psycopg2 connection string**: `postgresql+psycopg2://user:pass@host/db?sslmode=require`

### Step 2: Add environment variables in Render dashboard
- `DATABASE_URL` → your Neon connection string
- `SECRET_KEY` → generate with:  `python -c "import secrets; print(secrets.token_urlsafe(48))"`
- `TEST_AUTH_MODE` → `false` (production)
- `DEFAULT_ADMIN_EMAIL` → your admin email
- `DEFAULT_ADMIN_PASSWORD` → set a strong password (only used once on first boot)

### Step 3: Deploy
Push to GitHub. Render will auto-deploy because `autoDeploy: true` is set in `render.yaml`.

Alembic migrations run **at startup** — no separate deploy step needed.

---

## 6. Feature Flags Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `TEST_AUTH_MODE` | `true` | Any email/password logs in. Set `false` for production |
| `USE_SQLITE_FALLBACK` | `true` | Use SQLite when `DATABASE_URL` not set (non-production only) |
| `DATABASE_URL` | (auto SQLite) | Full database connection string |
| `SECRET_KEY` | (random ephemeral) | **Must** be set permanently in production |
| `UPLOAD_FOLDER` | `static/uploads` | Where images are stored (use Render disk path in prod) |
