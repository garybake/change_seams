---
paths:
  - "app/**/*.py"
---

# Backend Conventions

## FastAPI

- Route modules live in `app/api/` (chat) and `app/prompts/router.py` (prompt CRUD)
- Include routers in `app/main.py` via `app.include_router(...)`
- Dependency injection: use `Depends(get_db)` for DB sessions; never instantiate sessions directly in route handlers
- The tracer is stored on `request.app.state.tracer` (set in the `lifespan` function)
- Return Pydantic response models from all endpoints; never return raw dicts from route handlers

## SQLAlchemy (async)

- All DB access is async — use `await db.execute(...)`, `await db.commit()`, `await db.refresh(...)`
- `get_db()` in `app/db.py` yields an `AsyncSession`; import and use `Depends(get_db)` in routes
- ORM models live in `app/models/`; import all models in `app/models/__init__.py` so `Base.metadata` is populated for Alembic autogenerate and `create_all`
- Use `sqlalchemy.JSON` (not `sqlalchemy.dialects.postgresql.JSONB`) in ORM model column definitions — keeps models portable for SQLite tests. Migration files may use `postgresql.JSONB` directly

## LangChain 1.x

- Agent creation: `from langchain.agents import create_agent` — takes `model`, `tools`, `system_prompt`
- Invoke: `await agent.ainvoke({"messages": [HumanMessage(content=...)]}, config=RunnableConfig(callbacks=[...]))`
- Callbacks (observability): pass `OtelCallbackHandler` instance via `RunnableConfig(callbacks=[handler])`
- Token usage: read from `response.llm_output["token_usage"]` in `on_llm_end`, with fallback to `gen.message.usage_metadata`

## Config / Settings

- All runtime config is in `app/config.py` — a single `settings` singleton from `pydantic_settings.BaseSettings`
- **Do not** declare `list[str]` fields directly in `Settings` — pydantic-settings 2.x tries to JSON-parse env values before validators run. For comma-separated list env vars, declare the field as `str` and expose a `@property` that parses it. See `enabled_tools_csv` + `enabled_tools` in `app/config.py`
- Never read `os.environ` directly; always use `settings.<field>`

## Tools

- All tools extend `ChangeSeamsTool(BaseTool)` from `app/tools/base.py`
- Every tool must declare a `ToolContract` with `args_schema` (JSON Schema dict) and `required_permissions`
- Register tools at module bottom: `register(MyTool())` in `app/tools/__init__.py` imports
- `get_enabled_tools(settings.enabled_tools)` returns only the tools named in `ENABLED_TOOLS`
- If a tool's API key is missing, return a user-friendly string rather than raising an exception
