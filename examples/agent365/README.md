# agent365

Acquire an Agent 365 agent user token using an agent identity blueprint, an agent identity app ID, and an agent user.

## Run

Set these environment variables or add them to `.env`:

```bash
AGENT365_TENANT_ID=<tenant-id>
AGENT365_BLUEPRINT_CLIENT_ID=<agent-identity-blueprint-app-id>
AGENT365_BLUEPRINT_CLIENT_SECRET=<agent-identity-blueprint-secret>
AGENT365_AGENT_IDENTITY_APP_ID=<agent-identity-app-id>
AGENT365_AGENT_USER_ID=<agent-user-object-id>
```

Then run:

```bash
uv run --project examples/agent365 python src/main.py
```

By default this requests a Teams bot API token for `https://botapi.skype.com/.default`.

To request another resource, set `AGENT365_SCOPE`, for example:

```bash
AGENT365_SCOPE=https://graph.microsoft.com/.default
```

You can use `AGENT365_AGENT_USER_UPN` instead of `AGENT365_AGENT_USER_ID`.
