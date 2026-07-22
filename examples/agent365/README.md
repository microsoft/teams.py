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

The Teams SDK emits OpenTelemetry-compatible spans and metrics, but it does not configure exporters, Microsoft OpenTelemetry, or Agent365 scopes for you. Keep those dependencies in your app host.

Install OpenTelemetry/exporter packages in your app or example environment only:

```bash
uv add --project examples/agent365 opentelemetry-sdk opentelemetry-exporter-otlp
```

If your app uses the Microsoft OpenTelemetry distro for Agent365 observability, add it at the app level too:

```bash
uv add --project examples/agent365 microsoft-opentelemetry
```

Only use hosting extras or Microsoft Agents SDK packages when your app already uses that hosting stack. If you want a Teams-only app with no Agents SDK dependency, avoid `microsoft-opentelemetry[hosting]` and provide the Agent365 token resolver yourself.

Configure OpenTelemetry before starting the app. The public telemetry constants expose the canonical source names used by the SDK:

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

### Explicit Agent365 baggage

Agent365 correlation baggage is opt-in. Wrap Agent365 work with `agent365_baggage(...)` when you want Teams activity context to flow into Microsoft OpenTelemetry/Agent365 scopes. The SDK does not add this baggage automatically as part of generic Teams telemetry.

```python
import os

from microsoft_teams.api import MessageActivity
from microsoft_teams.apps import ActivityContext, agent365_baggage


async def handle_message(ctx: ActivityContext[MessageActivity]) -> None:
    with agent365_baggage(
        ctx,
        operation_source=os.getenv("OTEL_SERVICE_NAME", "agent365-example"),
        channel_link=os.getenv("TEAMS_CHANNEL_LINK"),
    ):
        # Put Agent365 scopes here, for example InvokeAgentScope, InferenceScope,
        # or ExecuteToolScope from your app-level Microsoft OTel/Agent Framework integration.
        await ctx.reply("Hello from Agent365 with explicit baggage.")
```

By default, `agent365_baggage(...)` includes stable Agent365 correlation identifiers from the Teams activity, such as tenant, conversation, service URL, channel, agent/app identity, and user ID when present. It does not include message text, attachments, names, or email addresses by default. Add display identity fields one at a time with `include`:

```python
with agent365_baggage(ctx, include=["sender_name", "agent_name"]):
    ...
```

Supported include values are `sender_name`, `agent_name`, `agent_description`, `sender_email`, and `agent_email`.

For work without an inbound Teams context, create the baggage scope manually:

```python
from microsoft_teams.apps import Agent365Baggage

with (
    Agent365Baggage()
    .operation_source("agent365-example")
    .set("gen_ai.conversation.id", conversation_id)
):
    ...
```

### Agent365 token resolver guidance

Microsoft OpenTelemetry owns exporter/auth configuration for Agent365 product visibility. The Teams SDK only provides SDK spans/metrics plus the explicit Agent365 baggage bridge above.

- **Default Python setup:** `a365_token_resolver` can be omitted if `DefaultAzureCredential` or environment-based auth can acquire the Agent365 Observability token.
- **OBO / Agent Framework setup:** use `AgenticTokenCache` in app code. Refresh the cache from the async Teams turn handler, then provide Microsoft OpenTelemetry a synchronous `a365_token_resolver` that returns the cached token.
- **Teams-only app, no Agents SDK dependency:** avoid `microsoft-opentelemetry[hosting]`. Use a manual resolver/cache with MSAL, client credentials, or your app's own OBO exchange.
- **S2S setup:** use a manual resolver backed by client credentials.

Keep content/output logging disabled unless your app intentionally opts in. The example guidance above is for correlation and operation visibility, not transcript or generated-output capture.
