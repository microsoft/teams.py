# agent365

Demonstrates scoping Teams API clients with `AgenticIdentity`.

`AgenticIdentity` is the SDK operation/request/proactive scope for the program: it has an `agentic_app_blueprint_id`, can include an `agentic_app_id`, and that app can optionally be associated with an `agentic_user_id`. Token helpers and lifecycle handlers stay specific where the service behavior is specific.

## Reactive Echo

`src/main.py` mimics the echo example. Incoming messages are handled normally; the inbound service URL and agentic identity are carried by the context/API layer.

```bash
export CLIENT_ID=<agentic-app-blueprint-id>
export CLIENT_SECRET=<client-secret>
export TENANT_ID=<tenant-id>

uv run --project examples/agent365 python src/main.py
```

## Proactive API Send

`src/proactive.py` shows both `app.send(..., agentic_identity=...)` and a scoped lower-level conversation activity API client. This user-backed sample uses `app.get_agentic_identity(...)` with `agentic_app_id` and `agentic_user_id` because that token flow needs both IDs; the blueprint ID comes from `CLIENT_ID` and the tenant ID comes from `TENANT_ID`.

```bash
export CLIENT_ID=<agentic-app-blueprint-id>
export CLIENT_SECRET=<client-secret>
export TENANT_ID=<tenant-id>

uv run --project examples/agent365 python src/proactive.py \
  <conversation-id> \
  <agentic-app-id> \
  <agentic-user-id>
```
