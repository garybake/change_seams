"""
Seam 5 — Prometheus metrics.

Defines application-level metrics that are scraped by Prometheus via /metrics.
Call record_agent_metrics() once per completed agent run to update all counters
and histograms.

To swap the observability backend, replace or extend record_agent_metrics()
or change the exporter in setup_tracing() in tracing.py — nothing else changes.
"""
from prometheus_client import Counter, Histogram

chat_requests_total = Counter(
    "chat_requests_total",
    "Total number of chat requests completed",
    ["provider", "model"],
)

chat_request_duration_seconds = Histogram(
    "chat_request_duration_seconds",
    "End-to-end agent request duration in seconds",
    ["provider", "model"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

llm_tokens_total = Counter(
    "llm_tokens_total",
    "Total LLM tokens consumed",
    ["token_type", "provider", "model"],  # token_type: prompt | completion
)

tool_calls_total = Counter(
    "tool_calls_total",
    "Total tool invocations",
    ["tool_name"],
)


def record_agent_metrics(
    provider: str,
    model: str,
    latency_seconds: float,
    token_usage: dict,
    tool_calls: list,
) -> None:
    """Record Prometheus metrics for a completed agent run."""
    chat_requests_total.labels(provider=provider, model=model).inc()
    chat_request_duration_seconds.labels(provider=provider, model=model).observe(
        latency_seconds
    )
    llm_tokens_total.labels(token_type="prompt", provider=provider, model=model).inc(
        token_usage.get("prompt_tokens", 0)
    )
    llm_tokens_total.labels(
        token_type="completion", provider=provider, model=model
    ).inc(token_usage.get("completion_tokens", 0))
    for call in tool_calls or []:
        tool_calls_total.labels(tool_name=call.get("name", "unknown")).inc()
