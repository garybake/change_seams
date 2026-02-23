"""Chat and config endpoints."""
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.runner import run_agent
from app.config import settings
from app.db import get_db

router = APIRouter(tags=["chat"])


# ── Schemas ────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    trace_id: str
    spans: list[dict[str, Any]]
    token_usage: dict[str, int]
    tool_calls: list[dict[str, Any]]


class ConfigResponse(BaseModel):
    llm_provider: str
    llm_model: str
    llm_temperature: float
    enabled_tools: list[str]
    policy_mode: str


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.post("/api/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    tracer = request.app.state.tracer
    result = await run_agent(
        message=body.message,
        session_id=body.session_id,
        db=db,
        tracer=tracer,
    )
    return ChatResponse(**result)


@router.get("/api/config", response_model=ConfigResponse)
async def get_config() -> ConfigResponse:
    """Return current runtime configuration (no secrets)."""
    return ConfigResponse(
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
        llm_temperature=settings.llm_temperature,
        enabled_tools=settings.enabled_tools,
        policy_mode=settings.policy_mode,
    )
