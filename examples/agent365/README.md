# agent365

Demonstrates passing `AgenticIdentity` directly to Teams API surfaces.

## Proactive API Send

`src/main.py` sends through the normal API client, but supplies `agentic_identity` to the activity create operation. The API layer uses the agentic token provider to put the right Agent ID token in the request header.

```bash
export CLIENT_ID=<agent-identity-blueprint-app-id>
export CLIENT_SECRET=<agent-identity-blueprint-secret>
export TENANT_ID=<tenant-id>

uv run --project examples/agent365 python src/main.py \
  <conversation-id> \
  <agentic-app-id> \
  <agentic-user-id>
```
