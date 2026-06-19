# Benjo Moments Studio - Agent Context

## Project Purpose

Benjo Moments Studio is a small photography business application with two
surfaces:

- A public portfolio site with home, gallery, services, about, pricing, and
  contact pages.
- A protected manager portal for customers, invoices, income, expenses,
  assets, gallery content, hero images, pricing, website settings, reports,
  and contact messages.

The intended deployment is a single Render web-service instance backed by
PostgreSQL and a persistent upload disk.

## Stack

- Python 3.12
- Flask 3
- SQLAlchemy 2
- PostgreSQL 16+
- Alembic migrations
- Jinja templates and repository-owned CSS/JavaScript
- Pillow for image validation
- Flask-Limiter for rate limiting
- Gunicorn on Render

PostgreSQL is mandatory. Do not introduce a SQLite fallback unless the user
explicitly changes that product decision.

## Architecture

- `app.py`: application factory, startup seeding, CSRF middleware, security
  headers, error handlers, `/healthz`, `/__version`, and blueprint setup.
- `config.py`: environment parsing and production safety checks.
- `auth.py`: login/logout and session-version validation.
- `public.py`: public pages, contact submission, and uploaded-media routes.
- `admin.py`: manager routes, request parsing, validation, and flash messages.
- `models.py`: SQLAlchemy models and database constraints.
- `database_sa.py`: persistence and business operations.
- `database.py`: compatibility facade that re-exports `database_sa.py`; new
  business logic belongs in `database_sa.py`.
- `db.py`: SQLAlchemy engine and session setup.
- `extensions.py`: shared Flask-Limiter instance and storage selection.
- `uploads.py`: image validation and randomized file storage.
- `templates/`: `public`, `admin`, and `auth` Jinja templates.
- `migrations/`: Alembic history; schema changes require a migration.
- `docs/SMOKE_TESTS.md`: current manual regression checklist.
- `render.yaml`, `Procfile`, `wsgi.py`: production deployment entry points.

## Important Domain Rules

### Invoice Settlement

`database_sa.mark_invoice_paid()` is a critical transaction. It locks the
invoice and customer rows, rejects duplicate settlement and overpayment,
marks the invoice paid, updates the customer balance, creates a linked income
record, and writes an audit event.

Preserve these properties when changing invoices:

- Settlement must remain atomic.
- One invoice must not produce duplicate income.
- `Income.source_invoice_id` identifies generated income.
- Deleting or reversing a paid invoice must keep the customer balance and
  generated income consistent.

### Deletion Behavior

Financial and customer records generally use soft deletion. Some content and
operational records are hard-deleted, and gallery/hero deletion also removes
the stored file. Check the existing function before changing deletion
semantics; do not assume every `delete_*` function behaves alike.

### Authentication

Production supports multiple equal-power administrators in one PostgreSQL
database. `DEFAULT_ADMIN_EMAIL` and `DEFAULT_ADMIN_PASSWORD` bootstrap the
first account; additional active accounts are retained. Password changes
invalidate that user's old sessions via the per-user auth version.

`TEST_AUTH_MODE` is development-only and is rejected in production. Do not
weaken this guard. Never expose values from `.env` in logs, tests, docs, or
responses.

### CSRF

`app.py` checks CSRF globally for POST, PUT, PATCH, and DELETE requests.
Templates use a mixture of explicit hidden fields and automatic injection:

- `templates/admin/base.html` injects a token into admin POST forms that do
  not already contain one.
- `templates/public/base.html` does the same for public POST forms.
- `templates/auth/login.html` includes its token explicitly.

When adding a modifying form, prefer an explicit hidden `csrf_token` field
for clarity and preserve the base-template fallback. API-style requests must
send the configured CSRF header.

### Uploads

Gallery and hero uploads accept validated JPEG, PNG, and WebP images. Keep the
size, pixel-count, Pillow verification, decompression-bomb protection, and
UUID filename controls intact. Never trust the client filename as a storage
path. Upload storage is local to the one Render instance.

## Local Workflow

Required environment values are documented in `.env.example`. The local
database is normally named `benjo_moments`.

```powershell
python -m pip install -r requirements.txt
python -m alembic upgrade head
python app.py
```

Useful URLs:

- Public site: `http://127.0.0.1:5000`
- Manager login: `http://127.0.0.1:5000/login`
- Manager portal: `http://127.0.0.1:5000/admin/`
- Health check: `http://127.0.0.1:5000/healthz`

## Verification

Run `python -m unittest -v tests.test_smoke` and use the scenarios in
`docs/SMOKE_TESTS.md` after behavior changes. At minimum, changes near auth,
CSRF, invoices, uploads, or deletion should verify both the successful path
and the important rejection/rollback path.

Before finishing a code change:

1. Inspect `git diff` and preserve unrelated user changes.
2. Apply any new Alembic migration to a PostgreSQL database.
3. Run the relevant smoke-test section.
4. Confirm `/healthz` still reports database and upload storage health.

## Engineering Guidance

- Follow existing Flask blueprint and database-service boundaries.
- Keep route handlers focused on HTTP parsing and user feedback; put reusable
  persistence and transaction logic in `database_sa.py`.
- Use `Decimal` for new monetary calculations and preserve database `Numeric`
  constraints. Avoid introducing new float-based accounting logic.
- Use SQLAlchemy expressions and transactions instead of raw SQL unless a
  migration or PostgreSQL-specific feature clearly requires it.
- Add database constraints for important invariants, not only form checks.
- Use POST for mutations and keep manager routes protected.
- Keep uploads compatible with the persistent-disk path configured by Render.
- Do not increase Gunicorn workers or Render instances without first moving
  uploads to shared object storage and rate limits to shared Redis storage.
- Treat audit logging as part of business mutations, especially finance,
  customers, invoices, settings, and content management.

## Current Limitations

- Administrator accounts currently have equal permissions; granular roles are
  not implemented.
- Local upload disk and in-memory rate-limit fallback constrain horizontal
  scaling.
- `admin.py` and `database_sa.py` are large; split them only when a requested
  change benefits from a clear domain boundary, not as unrelated cleanup.
- Accounting supports simple invoice settlement, not partial payments,
  refunds, allocations, or a full ledger.

## Product Tone

Public-facing work should feel polished, visual, and photography-led. Manager
screens should remain practical, compact, and easy to scan. Preserve existing
content and branding unless the user asks for a redesign or copy change.
