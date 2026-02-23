"""
Tests for the agent runner — full flow with a fake LLM (no real API calls).
Verifies: prompt fetch, tool dispatch, span capture, token accumulation, DB write.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.observability.tracing import OtelCallbackHandler, setup_tracing


# ── OtelCallbackHandler unit tests ───────────────────────────────────────

def test_otel_handler_accumulates_token_usage():
    tracer = setup_tracing()
    handler = OtelCallbackHandler(tracer=tracer, trace_id="abc123")

    from langchain_core.outputs import LLMResult, ChatGeneration

    msg = AIMessage(content="hello")
    gen = ChatGeneration(message=msg)
    result = LLMResult(
        generations=[[gen]],
        llm_output={"token_usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}},
    )
    handler.on_llm_end(result, run_id=uuid.uuid4())

    assert handler.token_usage["prompt_tokens"] == 10
    assert handler.token_usage["completion_tokens"] == 5
    assert handler.token_usage["total_tokens"] == 15


def test_otel_handler_accumulates_across_multiple_llm_calls():
    tracer = setup_tracing()
    handler = OtelCallbackHandler(tracer=tracer, trace_id="abc123")

    from langchain_core.outputs import LLMResult, ChatGeneration

    def make_result(p, c, t):
        msg = AIMessage(content="x")
        gen = ChatGeneration(message=msg)
        return LLMResult(
            generations=[[gen]],
            llm_output={"token_usage": {"prompt_tokens": p, "completion_tokens": c, "total_tokens": t}},
        )

    handler.on_llm_end(make_result(10, 5, 15), run_id=uuid.uuid4())
    handler.on_llm_end(make_result(20, 8, 28), run_id=uuid.uuid4())

    assert handler.token_usage["prompt_tokens"] == 30
    assert handler.token_usage["total_tokens"] == 43


def test_otel_handler_records_tool_calls():
    tracer = setup_tracing()
    handler = OtelCallbackHandler(tracer=tracer, trace_id="abc123")

    run_id = uuid.uuid4()
    handler.on_tool_start(
        serialized={"name": "echo"},
        input_str='{"text": "hi"}',
        run_id=run_id,
    )
    handler.on_tool_end(output="Echo: hi", run_id=run_id)

    assert len(handler.tool_calls) == 1
    assert handler.tool_calls[0]["name"] == "echo"
    assert handler.tool_calls[0]["input"] == '{"text": "hi"}'
    assert handler.tool_calls[0]["output"] == "Echo: hi"


def test_otel_handler_adds_span_per_tool_call():
    tracer = setup_tracing()
    handler = OtelCallbackHandler(tracer=tracer, trace_id="abc123")

    run_id = uuid.uuid4()
    handler.on_tool_start(serialized={"name": "echo"}, input_str="x", run_id=run_id)
    handler.on_tool_end(output="y", run_id=run_id)

    tool_spans = [s for s in handler.spans if "tool" in s["name"]]
    assert len(tool_spans) == 1
    assert tool_spans[0]["attributes"]["tool.name"] == "echo"


# ── Agent runner integration test (mocked LLM) ───────────────────────────

async def test_run_agent_with_mocked_llm(db_session):
    """Full run_agent() flow with a fake LLM — verifies DB write and response shape."""
    from app.agent.runner import run_agent
    from app.models.observation import ObservationLog
    from sqlalchemy import select

    tracer = setup_tracing()

    # Mock the LLM to return a fixed answer without hitting OpenAI
    fake_response = {
        "messages": [
            HumanMessage(content="What is 2+2?"),
            AIMessage(content="The answer is 4."),
        ]
    }

    with patch("app.agent.runner.get_llm") as mock_get_llm, \
         patch("app.agent.runner.create_agent") as mock_create_agent:

        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        mock_compiled = MagicMock()
        mock_compiled.ainvoke = AsyncMock(return_value=fake_response)
        mock_create_agent.return_value = mock_compiled

        result = await run_agent(
            message="What is 2+2?",
            session_id="test-session",
            db=db_session,
            tracer=tracer,
        )

    # Response shape
    assert result["answer"] == "The answer is 4."
    assert "trace_id" in result
    assert len(result["trace_id"]) == 32
    assert isinstance(result["spans"], list)
    assert isinstance(result["token_usage"], dict)

    # Observation log written to DB
    res = await db_session.execute(
        select(ObservationLog).where(ObservationLog.trace_id == result["trace_id"])
    )
    log = res.scalar_one_or_none()
    assert log is not None
    assert log.user_message == "What is 2+2?"
    assert log.agent_response == "The answer is 4."
    assert log.session_id == "test-session"


async def test_health_endpoint(client):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


async def test_config_endpoint(client):
    res = await client.get("/api/config")
    assert res.status_code == 200
    data = res.json()
    assert "llm_provider" in data
    assert "enabled_tools" in data
    assert isinstance(data["enabled_tools"], list)
