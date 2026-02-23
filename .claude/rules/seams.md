# How to Extend Each Seam

Guidelines for adding to or swapping each change seam without breaking the others.

---

## Seam 1 — Add a new LLM provider (`app/providers/llm.py`)

1. Add an `elif provider == "<name>":` branch in `get_llm()`
2. Import the provider's LangChain class inside the branch (lazy import keeps the default fast)
3. Add the new API key field to `Settings` in `app/config.py`
4. Document it in `.env.example`

Nothing else changes. The agent runner, tools, and observability are unaware of which provider is active.

---

## Seam 2 — Manage prompts (runtime, no code changes needed)

Create a new version:
```
POST /api/prompts
{"key": "agent.system", "content": "...", "purpose": "...", "owner": "..."}
```

Activate it (deactivates all other versions for that key):
```
PUT /api/prompts/agent.system/2/activate
```

The agent picks up the new prompt on the next request — no restart required.

To add a **new prompt key** used by a specific agent task:
1. Seed it via the API or add a new Alembic migration in `alembic/versions/`
2. Call `fetch_active_prompt("your.new.key", db)` in the relevant runner code

---

## Seam 3 — Add a new tool (`app/tools/`)

1. Create `app/tools/my_tool.py` extending `ChangeSeamsTool`
2. Declare a `ToolContract` with `name`, `description`, `args_schema` (JSON Schema), and `required_permissions`
3. Implement `_run(self, ...) -> str` and `_arun(self, ...) -> str`
4. At the bottom of the file: this file auto-registers, but you must add `from app.tools.my_tool import MyTool` + `register(MyTool())` to `app/tools/__init__.py`
5. Add the tool name to `ENABLED_TOOLS` in `.env`

Tools must handle missing API keys gracefully — return an explanatory string, don't raise.

```python
class MyTool(ChangeSeamsTool):
    name: str = "my_tool"
    description: str = "What this tool does."
    args_schema: Type[BaseModel] = MyToolInput
    contract: ToolContract = ToolContract(
        name="my_tool",
        description="...",
        args_schema={"type": "object", "properties": {...}, "required": [...]},
        required_permissions=["external_api"],
    )
    def _run(self, param: str, ...) -> str: ...
    async def _arun(self, param: str, ...) -> str: ...
```

---

## Seam 4 — Add a new config flag (`app/config.py`)

1. Add a field to `Settings` — use `str`, `float`, or `bool`; avoid `list[str]` (use `str` + `@property`)
2. Add it to `.env.example` with a comment explaining valid values
3. Read it anywhere via `from app.config import settings`

---

## Seam 5 — Change observability backend (`app/observability/tracing.py`)

The `setup_tracing()` function is the only place to change. Swap `ConsoleSpanExporter` for any OTEL-compatible exporter:

```python
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint="...")))
```

The `OtelCallbackHandler` continues to emit spans and accumulate response data unchanged.
