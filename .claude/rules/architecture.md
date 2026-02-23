# Project Architecture

This is a reference app demonstrating five "change seams" — well-defined interfaces where each dimension of an LLM application can be swapped independently without touching the rest of the codebase.

## Stack

- **Backend**: FastAPI + Python, dependencies via `pip` (`requirements.txt`)
- **Database**: PostgreSQL via SQLAlchemy (async), migrations via Alembic
- **LLM**: LangChain 1.x — use `from langchain.agents import create_agent` (the current API)
- **Frontend**: Vanilla JS, single page served as static files by FastAPI
- **Tests**: pytest + pytest-asyncio, SQLite for test DB (no Postgres needed for tests)
- **Container**: Docker — `docker-compose.yml` for local dev only (Postgres + hot-reload backend)

## Directory Layout

```
app/
  config.py          # Seam 4 — Pydantic Settings, reads .env
  db.py              # Async SQLAlchemy engine, session, Base
  models/            # ORM models (PromptTemplate, ObservationLog)
  providers/llm.py   # Seam 1 — get_llm() factory
  tools/             # Seam 3 — tool contracts + registry
  prompts/           # Seam 2 — prompt registry + CRUD router
  observability/     # Seam 5 — OTEL tracing + OtelCallbackHandler
  agent/runner.py    # Orchestrates all 5 seams per request
  api/chat.py        # POST /api/chat, GET /api/config
  main.py            # FastAPI app, lifespan, static mount
frontend/            # index.html, app.js, style.css
alembic/versions/    # 0001_initial.py, 0002_seed_default_prompt.py
tests/               # conftest.py + test_*.py
```

## The Five Seams

Each seam is a narrow interface. Swap the implementation by changing config or adding a single branch — nothing else changes.

| # | Seam | Interface | Swap mechanism |
|---|------|-----------|----------------|
| 1 | Provider | `get_llm()` in `app/providers/llm.py` | `LLM_PROVIDER` env var |
| 2 | Prompt | `fetch_active_prompt(key, db)` in `app/prompts/registry.py` | `PUT /api/prompts/{key}/{version}/activate` |
| 3 | Tools | `get_enabled_tools(names)` in `app/tools/__init__.py` | `ENABLED_TOOLS` env var |
| 4 | Config | `settings` singleton in `app/config.py` | `.env` file |
| 5 | Observability | `OtelCallbackHandler` in `app/observability/tracing.py` | Swap exporter in `setup_tracing()` |

## Agent Flow (per request)

```
POST /api/chat
  → fetch_active_prompt("agent.system", db)     # Seam 2
  → get_llm()                                    # Seam 1
  → get_enabled_tools(settings.enabled_tools)   # Seam 3
  → OtelCallbackHandler(tracer, trace_id)        # Seam 5
  → create_agent(llm, tools, system_prompt=...)
  → agent.ainvoke({"messages": [HumanMessage]}, config=RunnableConfig(callbacks=[...]))
  → write ObservationLog to DB                  # Seam 5
  → return ChatResponse(answer, trace_id, spans, token_usage)
```
