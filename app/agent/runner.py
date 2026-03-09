"""
Agent runner — orchestrates all five seams for a single chat request.

Flow:
  1. fetch_active_prompt()      → Seam 2 (prompt registry)
  2. get_llm()                  → Seam 1 (provider abstraction)
  3. get_enabled_tools()        → Seam 3 (tool contract layer)
  4. settings.policy_mode       → Seam 4 (runtime config)
  5. OtelCallbackHandler        → Seam 5 (observability)
"""
import time
import uuid
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from opentelemetry import trace
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.observation import ObservationLog
from app.observability.tracing import OtelCallbackHandler
from app.prompts.registry import fetch_active_prompt
from app.providers.llm import get_llm
from app.tools import get_enabled_tools

# Default fallback if no active prompt is found in the DB
_FALLBACK_SYSTEM_PROMPT = "You are a helpful AI assistant with access to tools."


async def run_agent(
    message: str,
    session_id: str | None,
    db: AsyncSession,
    tracer: trace.Tracer,
) -> dict[str, Any]:
    """
    Run the agent for a single user message.

    Returns a dict with: answer, trace_id, spans, token_usage, tool_calls.
    """
    trace_id = uuid.uuid4().hex

    # ── Seam 2: Fetch active prompt from registry ──────────────────────────
    prompt_result = await fetch_active_prompt("agent.system", db)
    if prompt_result:
        system_content, prompt_version = prompt_result
        prompt_key = "agent.system"
    else:
        system_content = _FALLBACK_SYSTEM_PROMPT
        prompt_version = 0
        prompt_key = None

    # ── Seam 1: Get LLM from provider factory ─────────────────────────────
    llm = get_llm()

    # ── Seam 3: Get enabled tools, filtered by policy permissions ─────────
    tools = get_enabled_tools(settings.enabled_tools, settings.allowed_permissions)

    # ── Seam 5: Create per-request callback handler ───────────────────────
    otel_handler = OtelCallbackHandler(tracer=tracer, trace_id=trace_id)

    # ── Seam 4: Policy mode from config ───────────────────────────────────
    policy_mode = settings.policy_mode

    # ── Build and invoke the agent ─────────────────────────────────────────
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_content,
    )

    config = RunnableConfig(callbacks=[otel_handler])

    t0 = time.monotonic()
    with tracer.start_as_current_span("agent.run") as root_span:
        root_span.set_attribute("trace_id", trace_id)
        root_span.set_attribute("llm.provider", settings.llm_provider)
        root_span.set_attribute("llm.model", settings.llm_model)
        root_span.set_attribute("prompt.key", prompt_key or "fallback")
        root_span.set_attribute("prompt.version", prompt_version)
        root_span.set_attribute("policy_mode", policy_mode)

        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=message)]},
            config=config,
        )

        latency_ms = (time.monotonic() - t0) * 1000

        # Extract answer from the last message
        messages = result.get("messages", [])
        answer = messages[-1].content if messages else ""

        # Finalize root span with token totals
        root_span.set_attribute("llm.prompt_tokens", otel_handler.token_usage["prompt_tokens"])
        root_span.set_attribute("llm.completion_tokens", otel_handler.token_usage["completion_tokens"])
        root_span.set_attribute("llm.total_tokens", otel_handler.token_usage["total_tokens"])
        root_span.set_attribute("latency_ms", round(latency_ms, 2))

    # Build the root span entry for the response
    root_span_data = {
        "name": "agent.run",
        "trace_id": trace_id,
        "span_id": uuid.uuid4().hex[:16],
        "latency_ms": round(latency_ms, 2),
        "attributes": {
            "llm.provider": settings.llm_provider,
            "llm.model": settings.llm_model,
            "prompt.key": prompt_key or "fallback",
            "prompt.version": prompt_version,
            "policy_mode": policy_mode,
            **{k: v for k, v in otel_handler.token_usage.items()},
        },
    }
    all_spans = [root_span_data] + otel_handler.spans

    # ── Seam 5: Persist observation log ───────────────────────────────────
    log = ObservationLog(
        trace_id=trace_id,
        session_id=session_id,
        user_message=message,
        agent_response=answer,
        prompt_key=prompt_key,
        prompt_version=prompt_version,
        model=settings.llm_model,
        provider=settings.llm_provider,
        prompt_tokens=otel_handler.token_usage["prompt_tokens"],
        completion_tokens=otel_handler.token_usage["completion_tokens"],
        total_tokens=otel_handler.token_usage["total_tokens"],
        latency_ms=round(latency_ms, 2),
        tool_calls=otel_handler.tool_calls or None,
        policy_mode=policy_mode,
    )
    db.add(log)
    await db.commit()

    return {
        "answer": answer,
        "trace_id": trace_id,
        "spans": all_spans,
        "token_usage": otel_handler.token_usage,
        "tool_calls": otel_handler.tool_calls,
    }
