# Deploying Benjo Moments to Render

Connect the repository as a Render Blueprint. `render.yaml` configures one web
service and one persistent disk. It uses the paid Starter plan because Render
Free web services do not support persistent disks.

## Required Environment Variables

- `DATABASE_URL`: PostgreSQL URL using psycopg2. Keep the database close to the
  Render service and include `sslmode=require` for a public connection.
- `DEFAULT_ADMIN_EMAIL`: initial manager email
- `DEFAULT_ADMIN_PASSWORD`: strong initial manager password

Render generates `SECRET_KEY`. `TEST_AUTH_MODE` must remain `false`.

## Deployment Lifecycle

1. Install dependencies and compile the source as a build-time syntax check.
2. Apply migrations with `python -m alembic upgrade head`.
3. Start one Gunicorn process with four threads.
4. Verify PostgreSQL and upload storage through `/healthz`.

One process and one instance are intentional: the attached disk and in-memory
rate limiter are local to that instance. The SQLAlchemy pool allows five
regular connections and two temporary overflow connections. TCP keepalives,
connection pre-ping, LIFO pooling, and periodic recycling handle stale hosted
PostgreSQL connections.

## Persistent Uploads

Gallery and hero images are stored at:

```text
/opt/render/project/data/uploads
```

The attached Render disk preserves these files between deployments. It also
means deployments briefly stop the service while Render moves the disk to the
new instance. Structured data remains in PostgreSQL.
