"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.chat import router as chat_router
from app.observability.tracing import setup_tracing
from app.prompts.router import router as prompts_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize OTEL tracing once at startup
    app.state.tracer = setup_tracing()
    yield
    # Cleanup (nothing needed for ConsoleSpanExporter)


app = FastAPI(
    title="Change Seams",
    description="LLM reference app demonstrating swappable provider, prompt, tool, config, and observability seams.",
    version="1.0.0",
    lifespan=lifespan,
)

# API routes
app.include_router(chat_router)
app.include_router(prompts_router)


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}


# Serve frontend as static files (must come last so API routes take priority)
_frontend_dir = Path(__file__).parent.parent / "frontend"
if _frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
