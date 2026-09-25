# Telemetry Setup — Reference

Detailed code for configuring OpenTelemetry, structlog, and contextual tracing
for Google Cloud (Cloud Trace + Cloud Logging).

---

## OpenTelemetry + structlog Configuration

```python
# src/core/telemetry.py
from __future__ import annotations

import structlog
from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_telemetry(service_name: str) -> None:
    """Initialise OpenTelemetry tracing and structlog.

    Call once during ``lifespan`` startup.
    """
    # ── OpenTelemetry ───────────────────────────────────────────
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(CloudTraceSpanExporter())
    )
    trace.set_tracer_provider(provider)

    # Auto-instrument FastAPI and outbound httpx calls
    FastAPIInstrumentor.instrument()
    HTTPXClientInstrumentor.instrument()

    # ── structlog ───────────────────────────────────────────────
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _add_otel_context,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(0),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _add_otel_context(
    _logger: object,
    _method_name: str,
    event_dict: dict[str, object],
) -> dict[str, object]:
    """Inject the current OTel trace & span IDs into every log entry."""
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx and ctx.trace_id:
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")
    return event_dict
```

---

## Binding `job_id` per Request

Use `structlog.contextvars` to bind the `job_id` so every log line inside that
execution automatically carries it.

```python
# Inside a webhook handler or middleware
import structlog

structlog.contextvars.clear_contextvars()
structlog.contextvars.bind_contextvars(job_id=payload.job_id)

logger = structlog.get_logger()
logger.info("agent_execution_started", agent=payload.agent_name)
# Output: {"event": "agent_execution_started", "agent": "summarizer",
#          "job_id": "abc-123", "trace_id": "00f3...", ...}
```

---

## Why NOT `import logging`

- The standard library `logging` module emits unstructured text by default.
- Adding JSON formatting and OTel context requires complex handler stacking.
- `structlog` processors compose cleanly and produce machine-parseable JSON
  natively, which maps directly to Cloud Logging structured payloads.
- **Rule:** If you see `import logging` anywhere in the project, replace it
  with `import structlog`.

---

## Cloud Logging Integration

When running on Cloud Run, logs written to `stdout` in JSON format are
automatically ingested by Cloud Logging. The `trace_id` field enables linking
logs to Cloud Trace spans in the GCP console — no additional agents or
sidecars are needed.

Required JSON fields for automatic linking:

| Field                                    | Source                              |
| :--------------------------------------- | :---------------------------------- |
| `logging.googleapis.com/trace`           | `projects/{project}/traces/{trace_id}` |
| `logging.googleapis.com/spanId`          | OTel span ID                       |
| `logging.googleapis.com/trace_sampled`   | Sampling decision                   |

You can add these via a custom structlog processor if you want automatic
correlation in the GCP Trace UI:

```python
def _add_gcp_trace_fields(
    _logger: object,
    _method_name: str,
    event_dict: dict[str, object],
) -> dict[str, object]:
    """Add GCP-specific trace fields for Cloud Logging correlation."""
    trace_id = event_dict.get("trace_id")
    if trace_id:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
        event_dict["logging.googleapis.com/trace"] = (
            f"projects/{project_id}/traces/{trace_id}"
        )
    span_id = event_dict.get("span_id")
    if span_id:
        event_dict["logging.googleapis.com/spanId"] = span_id
    return event_dict
```
