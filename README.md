# Change Seams

A FastAPI reference app demonstrating how to build an LLM application where the provider, prompts, tools, config, and observability are each a **change seam** — a narrow interface you can swap without touching anything else.

See blog post [https://garybake.com/seams1.html](https://garybake.com/seams1.html)

```
swap provider  →  change LLM_PROVIDER=anthropic in .env, restart
swap prompt    →  PUT /api/prompts/agent.system/2/activate
disable tools  →  change ENABLED_TOOLS=echo in .env, restart
swap tracer    →  change one line in app/observability/tracing.py
```

The UI is a single-page chat interface with a live trace panel showing spans, tool calls, and token usage for every request.

---

## Prerequisites

- Docker and Docker Compose
- An OpenAI API key (required)
- Optionally: a [Tavily](https://tavily.com) key for web search and an [OpenWeatherMap](https://openweathermap.org/api) key for weather

---

## Setup

**1. Clone and configure**

```bash
git clone <repo>
cd change_seams
cp .env.example .env
```

Edit `.env` and set at minimum:

```dotenv
OPENAI_API_KEY=sk-...
```

Optionally enable more tools:

```dotenv
TAVILY_API_KEY=tvly-...
OPENWEATHERMAP_API_KEY=...
ENABLED_TOOLS=echo,weather,search
```

**2. Start the app**

```bash
docker-compose up
```

This starts Postgres, runs Alembic migrations (including a seed prompt), and serves the app with hot-reload at `http://localhost:8000`.

**3. Open the UI**

Visit `http://localhost:8000`. Try asking:

- *"What is the square root of 144?"* — tests the echo/reasoning path
- *"What's the weather in Dublin?"* — invokes the weather tool
- *"What happened in the news today?"* — invokes web search

The trace panel on the right shows every span: LLM calls, tool invocations, latency, and token counts.

---

## Running tests

No API keys or running Postgres needed — tests use SQLite and mock all LLM calls.

```bash
pip install -r requirements.txt
pytest tests/
```

---

## The five seams

### 1. Provider (`app/providers/llm.py`)

`get_llm()` reads `LLM_PROVIDER`, `LLM_MODEL`, and `LLM_TEMPERATURE` from the environment and returns the appropriate LangChain chat model. Adding a provider is one `elif` branch.

```dotenv
LLM_PROVIDER=openai        # or anthropic
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.7
```

### 2. Prompt registry (`app/prompts/`)

Prompts are stored in Postgres with versioning. The agent fetches the active prompt by key on every request — no restart needed to change behaviour.

```bash
# Create a new version
curl -X POST http://localhost:8000/api/prompts \
  -H 'Content-Type: application/json' \
  -d '{"key":"agent.system","content":"You are a pirate assistant.","owner":"me"}'

# Activate it (response takes effect immediately)
curl -X PUT http://localhost:8000/api/prompts/agent.system/2/activate
```

### 3. Tool contract layer (`app/tools/`)

Each tool declares a `ToolContract`: name, description, JSON Schema args, and required permissions. The `ENABLED_TOOLS` env var gates which tools the agent can call.

```dotenv
ENABLED_TOOLS=echo,weather,search   # remove any to disable it live
```

Tools handle missing API keys gracefully — they return an explanatory message rather than crashing.

### 4. Runtime config (`app/config.py`)

All flags are read from the environment via Pydantic Settings. The `/api/config` endpoint exposes the current values (no secrets).

```bash
curl http://localhost:8000/api/config
```

### 5. Observability (`app/observability/tracing.py`)

Every request creates an OpenTelemetry root span. Child spans are emitted for each LLM call and tool invocation. Spans are exported to stdout (console) and also returned in the API response so the trace panel can render them without a separate backend.

To point at a real collector, swap `ConsoleSpanExporter` for an OTLP exporter in `setup_tracing()`.

---

## API reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/chat` | Run agent; returns answer + trace spans |
| `GET` | `/api/config` | Current runtime config (no secrets) |
| `GET` | `/api/prompts` | List latest version of every prompt |
| `GET` | `/api/prompts/{key}` | All versions for a prompt key |
| `POST` | `/api/prompts` | Create a new prompt version |
| `PUT` | `/api/prompts/{key}/{version}/activate` | Activate a version |
| `DELETE` | `/api/prompts/{id}` | Delete a prompt row |
| `GET` | `/health` | Liveness check |
| `GET` | `/docs` | Swagger UI |

---

## Project structure

```
app/
  config.py              # Seam 4 — Pydantic Settings, reads .env
  db.py                  # Async SQLAlchemy engine + session
  models/                # PromptTemplate, ObservationLog ORM models
  providers/llm.py       # Seam 1 — get_llm() factory
  tools/                 # Seam 3 — echo, weather, search + registry
  prompts/               # Seam 2 — registry service + CRUD router
  observability/         # Seam 5 — OTEL setup + OtelCallbackHandler
  agent/runner.py        # Wires all 5 seams per request
  api/chat.py            # POST /api/chat, GET /api/config
  main.py                # FastAPI app, lifespan, static file mount
frontend/                # index.html, app.js, style.css (vanilla JS)
alembic/versions/        # DB migrations + default prompt seed
tests/                   # 33 tests, zero real API calls
```
