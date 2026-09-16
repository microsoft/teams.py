# M365 Extensions Sample

This sample embeds the teams.py `App` inside a Microsoft Agents SDK `AgentApplication` using
the `microsoft-teams-m365extensions` bridge. Teams turns that match a teams.py route are handled
by teams.py; everything else — non-Teams channels, and Teams turns with no matching route — falls
through to the `AgentApplication`.

## How It Works

`use_teams_sdk` extracts `client_id`/`tenant_id` from the connection manager, wires teams.py's
outbound token callback to it, constructs the `microsoft_teams.apps.App`, and installs
`TeamsMiddleware` on the Agents SDK adapter — returning the configured `App` ready for handler
registration.

For every Teams turn the middleware checks whether `TEAMS_APP` has a matching route; if so it
processes the activity with teams.py and propagates the returned `InvokeResponse` back through the
Agents SDK pipeline. If no teams.py route matches, the turn falls through to `AGENT_SDK_APP`.

## Commands

Teams SDK routes (`TEAMS_APP`, Teams channel only):

- `help` — Adaptive Card listing every command
- `react` — bot adds then removes an emoji reaction
- `quote` — bot replies with a quoted reply
- `targeted` — ephemeral message visible only to the sender
- `task` — task module fetch/submit flow

Agents SDK routes (`AGENT_SDK_APP`, fallthrough + non-Teams channels):

- `channel` — report the channel this turn arrived on and how it was routed
- `agents sdk react` — reach teams.py's API client from an Agents SDK handler
- `agents sdk proactive` — trigger a proactive send from an Agents SDK handler
- `whoami` / `mail` — Microsoft Graph via two separate OAuth connections (see below)
- `signout` — sign out of both Graph handlers
- anything else — echoed by the Agents SDK

## Setup

This sample uses the official [Teams CLI](https://microsoft.github.io/teams-sdk/cli/)
(`@microsoft/teams.cli`) to register the bot. Install it (requires Node.js 20+) and sign in to
Microsoft 365:

```bash
npm install -g @microsoft/teams.cli
teams login
```

Expose this sample's local `/api/messages` endpoint with a dev tunnel, then create the bot. The
`whoami`/`mail` sign-in and the [Web Chat harness](./tools/webchat) both need an Azure Bot resource,
so create the bot with `--azure`:

```bash
teams app create \
  --name "m365extensions" \
  --azure --resource-group <rg> --create-resource-group \
  --endpoint "https://<your-tunnel>/api/messages"
```

`teams app create` registers the AAD app, generates a client secret, builds and imports the
manifest, and prints your credentials:

```
CLIENT_ID=<client-id>
CLIENT_SECRET=<client-secret>
TENANT_ID=<tenant-id>
```

Copy `sample.env` to `.env` and paste those three values into the `CONNECTIONS__…` fields. The
Agents SDK's `MsalConnectionManager` reads this nested configuration schema, not the flat
`CLIENT_ID` names the CLI prints — so map them across rather than pointing `teams app create --env`
at `.env`:

```bash
cp sample.env .env
# CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID=<CLIENT_ID>
# CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET=<CLIENT_SECRET>
# CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID=<TENANT_ID>
```

## Running

Install dependencies from the repo root, then run the sample from its own directory so `.env` is
discovered automatically:

```bash
uv sync --all-packages
cd examples/m365extensions
uv run src/main.py
```

Install the bot in Teams and send `help` — replies are prefixed `[Teams SDK]` (teams.py route) or
`[Agent SDK]` (fallthrough to `AgentApplication`).

## Multi Authentication (two Graph connections)

`whoami` and `mail` both call Microsoft Graph, but through separate OAuth connections on the same
AAD app, so each keeps its own token cache — signing in for `whoami` does not satisfy `mail`.

| Command | Handler | ABS connection | Scopes |
| --- | --- | --- | --- |
| `whoami` | `graphuser` | `graphuser` | `User.Read` |
| `mail` | `graphmail` | `graphmail` | `User.Read Mail.Read` |

Create the two OAuth connections (`graphuser`, `graphmail`) on the Azure Bot registration — via the
Azure Portal or `az bot authsetting create`, since the Teams CLI doesn't manage OAuth connections —
then uncomment their handler entries in `.env` (see the commented block in `sample.env`). Handlers
are configured from `.env`, not in code. Auth
lives on the Agents SDK side because the intercept runs inside `AgentApplication.on_turn`, which
the middleware only calls when no teams.py route matches — a teams.py route would run
unauthenticated rather than fail. The sample also passes a `should_bypass_teams` predicate so
`signin/*` invokes always stay with the Agents SDK.

## Multichannel

`TeamsMiddleware` routes to teams.py only for Teams activities; every other channel passes straight
through to the Agents SDK. Teams alone can't show that half of the contract, so the sample runs on
three channels:

| | Teams | Web Chat / Direct Line | Email |
| --- | --- | --- | --- |
| `channel` | fell through | passed through | passed through |
| `help` | Adaptive Card (teams.py) | plain text (Agents SDK) | plain text (Agents SDK) |
| `quote`, `task`, `react`, `targeted` | handled by teams.py | no route → echoed | no route → echoed |
| `whoami`, `mail` | OAuth card | OAuth card | declined (cards are inert on email) |

### Web Chat / Direct Line

This example ships a small Direct Line harness in [`tools/webchat`](./tools/webchat) — a browser UI
plus a scriptable CLI — for exercising the non-Teams path:

```bash
python tools/webchat/serve.py                  # browser UI at http://localhost:3000
python tools/webchat/dl_test.py help channel   # scripted, prints card contents too
```

### Email

Enable the Email channel on the bot registration. Two things differ: `activity.text` is the message
body only (the subject arrives in `channelData.Subject`), and the body carries a signature/quoted
thread — which is why `_command()` anchors matches to the first line. Sign-in is declined on email
because Azure Bot Service flattens OAuth cards into a static, unclickable image.
