# agent365

Demonstrates scoping Teams API clients with `AgenticUser`.

## Reactive Echo

`src/main.py` mimics the echo example. Incoming messages are handled normally; the inbound service URL and agentic user are carried by the context/API layer.

```bash
export CLIENT_ID=<agentic-blueprint-app-id>
export CLIENT_SECRET=<agentic-blueprint-secret>
export TENANT_ID=<tenant-id>

uv run --project examples/agent365 python src/main.py
```

## Proactive API Send

`src/proactive.py` shows both `app.send(..., agentic_user=...)` and a scoped lower-level conversation activity API client. In both cases the API layer asks the auth provider for the right Agent ID token and uses it in the request header.

```bash
export CLIENT_ID=<agentic-blueprint-app-id>
export CLIENT_SECRET=<agentic-blueprint-secret>
export TENANT_ID=<tenant-id>

uv run --project examples/agent365 python src/proactive.py \
  <conversation-id> \
  <agentic-app-instance-id> \
  <agentic-user-id>
```
