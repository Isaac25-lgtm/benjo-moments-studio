# PostgreSQL Setup and Migrations

Benjo Moments uses PostgreSQL exclusively in local development and on Render.

## Local setup

Create a database:

```powershell
$env:PGPASSWORD = "your-postgres-password"
psql -h localhost -U postgres -d postgres -c "CREATE DATABASE benjo_moments"
```

Set `.env`:

```env
DATABASE_URL=postgresql+psycopg2://postgres:your-password@localhost:5432/benjo_moments
SECRET_KEY=replace-with-a-long-random-value
FLASK_ENV=development
TEST_AUTH_MODE=false
```

Apply migrations and start the application:

```powershell
python -m alembic upgrade head
python app.py
```

## Render and Neon

Set these Render environment variables:

- `DATABASE_URL`: Neon PostgreSQL URL with `sslmode=require`
- `DEFAULT_ADMIN_EMAIL`: initial manager email
- `DEFAULT_ADMIN_PASSWORD`: strong initial password
- `TEST_AUTH_MODE=false`

`render.yaml` runs `python -m alembic upgrade head` before each deployment.
Uploaded files are stored on the attached Render disk, while all structured
application data is stored in PostgreSQL.

## Useful commands

```powershell
python -m alembic current
python -m alembic history
python -m alembic upgrade head
```
