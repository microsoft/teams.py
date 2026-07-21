# agent365

Demonstrates scoping Teams API clients with `AgenticIdentity`.

## Reactive Echo

`src/main.py` mimics the echo example. Incoming messages are handled normally; the inbound service URL and agentic identity are carried by the context/API layer.

```bash
export CLIENT_ID=<agent-identity-blueprint-app-id>
export CLIENT_SECRET=<agent-identity-blueprint-secret>
export TENANT_ID=<tenant-id>

uv run --project examples/agent365 python src/main.py
```

## Proactive API Send

`src/proactive.py` shows both `app.send(..., agentic_identity=...)` and a scoped lower-level conversation activity API client. In both cases the API layer asks the auth provider for the right Agent ID token and uses it in the request header.

```bash
export CLIENT_ID=<agent-identity-blueprint-app-id>
export CLIENT_SECRET=<agent-identity-blueprint-secret>
export TENANT_ID=<tenant-id>

uv run --project examples/agent365 python src/proactive.py \
  <conversation-id> \
  <agentic-app-id> \
  <agentic-user-id>
```

## Observability

The Teams SDK emits OpenTelemetry-compatible spans and metrics, but it does not configure exporters or the OpenTelemetry SDK for you. Configure tracing, metrics, resources, and exporters in your application host.

Install exporter packages in your app or example environment only:

```bash
uv add --project examples/agent365 opentelemetry-sdk opentelemetry-exporter-otlp
```

Then configure OpenTelemetry before starting the app. The public telemetry constants expose the canonical source names used by the SDK:

- API/lower layer tracer and meter: `Microsoft.Teams.Api`
- Apps/orchestration tracer and meter: `Microsoft.Teams.Apps`

```python
import os

from microsoft_teams.api import TEAMS_API_METER_NAME, TEAMS_API_TRACER_NAME
from microsoft_teams.apps import (
    TEAMS_BOT_APPLICATION_METER_NAME,
    TEAMS_BOT_APPLICATION_TRACER_NAME,
)
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def configure_observability() -> None:
    resource = Resource.create(
        {
            "service.name": os.getenv("OTEL_SERVICE_NAME", "agent365-example"),
        }
    )

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(tracer_provider)

    metric_reader = PeriodicExportingMetricReader(OTLPMetricExporter())
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[metric_reader]))

    # Register the canonical SDK source names with the configured providers.
    for tracer_name in (TEAMS_API_TRACER_NAME, TEAMS_BOT_APPLICATION_TRACER_NAME):
        trace.get_tracer(tracer_name)
    for meter_name in (TEAMS_API_METER_NAME, TEAMS_BOT_APPLICATION_METER_NAME):
        metrics.get_meter(meter_name)
```

Set exporter configuration through OpenTelemetry environment variables, for example:

```bash
export OTEL_SERVICE_NAME=agent365-example
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```
