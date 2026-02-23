"""
Seam 5 — Observability Hooks.

Sets up OpenTelemetry tracing to stdout (ConsoleSpanExporter).
OtelCallbackHandler captures per-request spans, token usage, and tool calls
and returns them in the API response so the frontend trace panel can render them.
"""
import time
import uuid
from typing import Any, Optional, Union
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor


def setup_tracing() -> trace.Tracer:
    """Initialize OTEL with ConsoleSpanExporter. Called once at app startup."""
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    return trace.get_tracer("change_seams.agent")


class OtelCallbackHandler(BaseCallbackHandler):
    """
    LangChain callback handler that:
    1. Emits OTEL child spans to stdout for each LLM call and tool invocation.
    2. Accumulates span data, token counts, and tool call logs for the API response.
    """

    def __init__(self, tracer: trace.Tracer, trace_id: str) -> None:
        super().__init__()
        self.tracer = tracer
        self.trace_id = trace_id
        self.spans: list[dict[str, Any]] = []
        self.token_usage: dict[str, int] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
        self.tool_calls: list[dict[str, Any]] = []
        # Temporary storage keyed by run_id (str) for matching start → end
        self._tool_starts: dict[str, dict[str, Any]] = {}
        self._llm_start_times: dict[str, float] = {}
        self._tool_start_times: dict[str, float] = {}

    # ── LLM callbacks ──────────────────────────────────────────────────────

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        self._llm_start_times[str(run_id)] = time.monotonic()

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        start = self._llm_start_times.pop(str(run_id), time.monotonic())
        latency_ms = (time.monotonic() - start) * 1000

        # Accumulate token usage (OpenAI returns this in llm_output)
        usage = (response.llm_output or {}).get("token_usage", {})
        # Also try usage_metadata on the first generation (newer langchain-openai)
        if not usage and response.generations:
            for gen_list in response.generations:
                for gen in gen_list:
                    if hasattr(gen, "message") and hasattr(gen.message, "usage_metadata"):
                        meta = gen.message.usage_metadata or {}
                        usage = {
                            "prompt_tokens": meta.get("input_tokens", 0),
                            "completion_tokens": meta.get("output_tokens", 0),
                            "total_tokens": meta.get("total_tokens", 0),
                        }
                        break

        self.token_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
        self.token_usage["completion_tokens"] += usage.get("completion_tokens", 0)
        self.token_usage["total_tokens"] += usage.get("total_tokens", 0)

        span_data = {
            "name": "llm.call",
            "trace_id": self.trace_id,
            "span_id": uuid.uuid4().hex[:16],
            "latency_ms": round(latency_ms, 2),
            "attributes": {
                "llm.prompt_tokens": usage.get("prompt_tokens", 0),
                "llm.completion_tokens": usage.get("completion_tokens", 0),
                "llm.total_tokens": usage.get("total_tokens", 0),
            },
        }
        self.spans.append(span_data)

        # Emit OTEL child span
        with self.tracer.start_as_current_span("llm.call") as span:
            span.set_attribute("llm.prompt_tokens", usage.get("prompt_tokens", 0))
            span.set_attribute("llm.completion_tokens", usage.get("completion_tokens", 0))
            span.set_attribute("llm.total_tokens", usage.get("total_tokens", 0))
            span.set_attribute("latency_ms", round(latency_ms, 2))

    # ── Tool callbacks ──────────────────────────────────────────────────────

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        tool_name = serialized.get("name", "unknown")
        self._tool_starts[str(run_id)] = {"name": tool_name, "input": input_str}
        self._tool_start_times[str(run_id)] = time.monotonic()

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        start_info = self._tool_starts.pop(str(run_id), {})
        start_time = self._tool_start_times.pop(str(run_id), time.monotonic())
        latency_ms = (time.monotonic() - start_time) * 1000
        tool_name = start_info.get("name", "unknown")
        tool_input = start_info.get("input", "")

        call_record = {
            "name": tool_name,
            "input": tool_input,
            "output": str(output),
            "latency_ms": round(latency_ms, 2),
        }
        self.tool_calls.append(call_record)

        span_data = {
            "name": f"tool.{tool_name}",
            "trace_id": self.trace_id,
            "span_id": uuid.uuid4().hex[:16],
            "latency_ms": round(latency_ms, 2),
            "attributes": {
                "tool.name": tool_name,
                "tool.input": tool_input,
                "tool.output": str(output)[:500],  # truncate long outputs in spans
            },
        }
        self.spans.append(span_data)

        # Emit OTEL child span
        with self.tracer.start_as_current_span(f"tool.{tool_name}") as span:
            span.set_attribute("tool.name", tool_name)
            span.set_attribute("tool.input", tool_input)
            span.set_attribute("tool.output", str(output)[:500])
            span.set_attribute("latency_ms", round(latency_ms, 2))

    def on_tool_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        start_info = self._tool_starts.pop(str(run_id), {})
        self._tool_start_times.pop(str(run_id), None)
        tool_name = start_info.get("name", "unknown")

        span_data = {
            "name": f"tool.{tool_name}",
            "trace_id": self.trace_id,
            "span_id": uuid.uuid4().hex[:16],
            "latency_ms": 0,
            "attributes": {
                "tool.name": tool_name,
                "tool.error": str(error),
            },
        }
        self.spans.append(span_data)
