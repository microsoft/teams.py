# Agent365 OpenTelemetry

Demonstrates Agent365 observability for reactive Teams turns and proactive sends.

The Teams SDK owns Teams spans, metrics, token acquisition, and Agent365-compatible baggage. The app host owns the Microsoft OpenTelemetry distro, exporter configuration, and Agent365 operation scopes.

## Configuration

```bash
cd examples/agent365

export CLIENT_ID=<agentic-blueprint-app-id>
export CLIENT_SECRET=<agentic-blueprint-secret>
export TENANT_ID=<tenant-id>
```

`microsoft-opentelemetry` is an example-only dependency. The Teams SDK packages depend only on the standard OpenTelemetry API and do not configure exporters.

`src/observability.py` configures the Agent365 exporter. Python's exporter token resolver is synchronous, so the example refreshes an app-instance token asynchronously through `app.token_provider` before opening an Agent365 scope, then exposes that cached token to the exporter.

Sensitive content recording remains disabled. The examples create `InvokeAgentScope` instances without recording message input or output.

## Reactive flow

```bash
uv run python src/main.py
```

The app configures:

```python
app = App(
    telemetry={
        "agent365": {
            "include": ["senderName", "senderEmail", "agentName", "agentEmail", "agentDescription"],
            "operation_source": "Microsoft.Teams.Apps",
        }
    }
)
```

Inbound Agent365 baggage is established before the SDK's root turn span, so the turn, handler, API, auth, and app-created Agent365 spans share the same identity. Identifier fields are included by default; names and email addresses require explicit `include` entries. Set `"agent365": False` to disable the bridge.

## Proactive flow

```bash
uv run python src/proactive.py \
  <conversation-id> \
  <agentic-app-instance-id> \
  <agentic-user-id>
```

There is no inbound activity for proactive work. `src/proactive.py` therefore creates a reusable `create_agent365_scope(...)` opener and supplies the per-operation `AgenticUser` and conversation ID. Everything inside that baggage scope, including `InvokeAgentScope`, `app.send`, lower-level API calls, and auth spans, carries the same identity.

The proactive process explicitly flushes the tracer provider before exit because the Agent365 exporter batches spans.

## Public integration surfaces

- `app.token_provider.get_app_token(...)`
- `app.token_provider.get_agentic_user_token(...)`
- `app.token_provider.get_agentic_app_instance_token(...)`
- `App(telemetry={"agent365": ...})`
- `agent365_baggage(...)` for low-level/manual scopes
- `create_agent365_scope(...)` for reusable proactive scopes

The canonical Teams telemetry source names remain:

- API/lower layer: `Microsoft.Teams.Api`
- Apps/orchestration layer: `Microsoft.Teams.Apps`
