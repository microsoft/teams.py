# agent365

Demonstrates passing `AgenticIdentity` directly to Teams API surfaces.

## Proactive API Send

`src/main.py` shows both `app.send(..., agentic_identity=...)` and the lower-level conversation activity API. In both cases the API layer asks the auth provider for the right Agent ID token and uses it in the request header.

```bash
export CLIENT_ID=<agent-identity-blueprint-app-id>
export CLIENT_SECRET=<agent-identity-blueprint-secret>
export TENANT_ID=<tenant-id>

uv run --project examples/agent365 python src/main.py \
  <conversation-id> \
  <agentic-app-id> \
  <agentic-user-id>
```
