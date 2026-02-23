---
paths:
  - "tests/**/*.py"
---

# Testing Conventions

## Setup

- Test framework: `pytest` with `pytest-asyncio` (`asyncio_mode = auto` in `pytest.ini`)
- All test DB access uses SQLite via `aiosqlite` — no Postgres needed to run tests
- Shared fixtures are in `tests/conftest.py`

## Key fixture rules

- **Always import `app.models` before calling `Base.metadata.create_all`** — models register themselves with `Base.metadata` only when imported. If you skip this, `create_all` creates zero tables silently.
  ```python
  from app.db import Base
  import app.models  # registers ORM models
  async with engine.begin() as conn:
      await conn.run_sync(Base.metadata.create_all)
  ```
- Use `tmp_path` fixture for per-test SQLite databases (`sqlite+aiosqlite:///{tmp_path}/test.db`). Do not use `sqlite+aiosqlite:///:memory:` — in-memory SQLite with `aiosqlite` has connection isolation issues that cause "no such table" errors.
- The `client` fixture overrides `get_db` via `app.dependency_overrides` so API tests use the test DB, not the real one. Always clear `dependency_overrides` after the test.

## What to test

| File | What it covers |
|------|---------------|
| `test_config.py` | Settings parsing (especially `enabled_tools` comma string), `get_llm()` returns correct class |
| `test_tools.py` | Each tool's `_run()` in isolation; use `respx` to mock HTTP calls for weather/search; verify graceful no-key behaviour |
| `test_prompts.py` | Prompt CRUD endpoints; **must verify the activate-deactivates-others invariant** |
| `test_agent.py` | Full `run_agent()` flow with `patch("app.agent.runner.get_llm")` and `patch("app.agent.runner.create_agent")` to avoid real API calls; verifies DB write and response shape |

## Mocking LLM calls

Never call real OpenAI/Anthropic APIs in tests. Mock at the agent runner level:

```python
from unittest.mock import AsyncMock, MagicMock, patch

with patch("app.agent.runner.get_llm") as mock_get_llm, \
     patch("app.agent.runner.create_agent") as mock_create_agent:
    mock_create_agent.return_value.ainvoke = AsyncMock(return_value={
        "messages": [HumanMessage(content="q"), AIMessage(content="answer")]
    })
    result = await run_agent(...)
```

## Environment for tests

`conftest.py` sets env defaults before any app import:
```python
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///test.db")
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("ENABLED_TOOLS", "echo")
```
These use `setdefault` so a real `.env` file won't override them during test runs.
