---
paths:
  - "alembic/**/*.py"
  - "app/models/**/*.py"
---

# Database & Migrations

## Alembic setup

- Async-native: `alembic/env.py` uses `run_async_migrations()` with `async_engine_from_config`
- The DB URL is overridden from `settings.DATABASE_URL` in `env.py` — the `alembic.ini` URL is a placeholder
- `env.py` imports `app.models` so all ORM models are registered on `Base.metadata` before autogenerate runs

## Adding a migration

For schema changes, prefer autogenerate:
```bash
alembic revision --autogenerate -m "description"
```
Review the generated file before running — autogenerate misses some things (e.g. partial indexes, custom types).

For data migrations (seeding), write manually using `op.bulk_insert()`:
```python
def upgrade():
    table = sa.table("prompt_templates", sa.column("key"), ...)
    op.bulk_insert(table, [{"key": "agent.system", ...}])
```

## ORM model rules

- Use `sqlalchemy.JSON` for JSON columns in ORM models (not `postgresql.JSONB`) — `JSONB` breaks SQLite test setup
- Migration files may use `postgresql.JSONB` directly since migrations only run against Postgres
- Always add new models to `app/models/__init__.py` exports so they register with `Base.metadata`

## Running migrations

In Docker (automatic on container start):
```
alembic upgrade head
```

Locally (requires Postgres running):
```bash
DATABASE_URL=postgresql+asyncpg://... alembic upgrade head
```
