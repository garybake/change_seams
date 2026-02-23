# change_seams

A FastAPI reference app demonstrating five "change seams" — narrow interfaces where the LLM provider, prompt, tools, config, and observability can each be swapped independently without touching the rest of the codebase.

## Quick start

```bash
cp .env.example .env   # fill in OPENAI_API_KEY (and optionally TAVILY_API_KEY, OPENWEATHERMAP_API_KEY)
docker-compose up      # starts Postgres, runs migrations, serves on http://localhost:8000
pytest tests/          # runs all 33 tests (no API keys needed — uses SQLite + mocks)
```

## Rules

Detailed conventions are in `.claude/rules/`:

| File | Covers |
|------|--------|
| `architecture.md` | Stack, directory layout, the five seams, agent request flow |
| `backend.md` | FastAPI, SQLAlchemy async, LangChain 1.x, config/settings, tools |
| `seams.md` | How to add a provider, prompt, tool, config flag, or swap the observability backend |
| `testing.md` | Test setup, fixture rules, mocking LLM calls, what each test file covers |
| `migrations.md` | Alembic setup, adding migrations, ORM model rules |
| `frontend.md` | Vanilla JS conventions, trace panel rendering |
