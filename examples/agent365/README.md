# agent365

Demonstrates Agent 365 `AgentUser` support in reactive and proactive modes.

## Reactive Echo

`src/main.py` mimics the echo example. Incoming messages are handled normally, but when the inbound activity recipient has `role="agenticUser"`, `ctx.send()` and `ctx.reply()` send as that concrete `AgentUser` using the inbound activity's service URL.

```bash
export CLIENT_ID=<agent-identity-blueprint-app-id>
export CLIENT_SECRET=<agent-identity-blueprint-secret>
export TENANT_ID=<tenant-id>

uv run --project examples/agent365 python src/main.py
```

## Proactive AgentUser Send

`src/proactive.py` mimics the proactive messaging example, but sends as a specific AgentUser. Supply the concrete agent identity app ID and agent user ID.

```bash
export CLIENT_ID=<agent-identity-blueprint-app-id>
export CLIENT_SECRET=<agent-identity-blueprint-secret>
export TENANT_ID=<tenant-id>

uv run --project examples/agent365 python src/proactive.py \
  <conversation-id> \
  <agent-identity-app-id> \
  <agent-user-id>
```

## Identity Model

- `CLIENT_ID`: blueprint client/app ID.
- `agent_identity_app_id`: concrete agent identity app/client ID.
- `agent_user_id`: user-shaped account/persona object ID for the agent.
