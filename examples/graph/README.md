# Teams Graph Integration Demo

This demo application showcases how to use Microsoft Graph APIs within a Teams bot, including both delegated (user) and app-only access patterns.

## Features

- **User Authentication**: Teams OAuth integration with automatic token management
- **Profile Information**: Retrieve and display user profile data via delegated access
- **Email Access**: List recent emails with Mail.Read scope
- **App-Level Graph Access**: Query organization data using app-only permissions (no user sign-in needed) via `app.get_app_graph()` or `ctx.app_graph`

## Commands

- `signin` - Authenticate with Microsoft Graph
- `profile` - Display user profile information (requires User.Read)
- `emails` - Show recent emails (requires Mail.Read permission)
- `app-users` - List organization users via `app.get_app_graph()` (app-only, no sign-in needed)
- `app-users ctx` - List organization users via `ctx.app_graph` (app-only, no sign-in needed)
- `signout` - Sign out of Microsoft Graph
- `help` - Show available commands and implementation details

## Setup

1. Configure OAuth connection in Azure Bot registration
2. Set connection name to "graph" (or update `CONNECTION_NAME` env var)
3. Configure appropriate Microsoft Graph permissions:
   - `User.Read` (for profile access)
   - `Mail.Read` (for email access)
   - `User.Read.All` application permission (for app-users commands)
4. Create a `.env` file in `examples/graph/src/` with required environment variables (copy from `sample.env`):
   ```
   CLIENT_ID=<your-azure-bot-app-id>
   CLIENT_SECRET=<your-azure-bot-app-secret>
   TENANT_ID=<your-tenant-id>
   CONNECTION_NAME=graph
   # PORT=3978  # Optional: specify custom port (defaults to 3978)
   ```

## Configuring a Regional Bot
NOTE: This example uses West Europe, but follow the equivalent for other locations.

1. In `azurebot.bicep`, replace all `global` occurrences to `westeurope`
2. In `manifest.json`, in `validDomains`, `*.botframework.com` should be replaced by `europe.token.botframework.com`
3. In `aad.manifest.json`, replace `https://token.botframework.com/.auth/web/redirect` with `https://europe.token.botframework.com/.auth/web/redirect`
4. In `main.py`, update `AppOptions` to include `api_client_settings`

```python
app = App(
    default_connection_name='graph',
    api_client_settings=ApiClientSettings(
        oauth_url="https://europe.token.botframework.com"
    )
)
```

## Running

From the `examples/graph/` directory (so `.env` is discovered automatically):

```bash
cd examples/graph
uv run src/main.py
```

## Example Usage

```python
from microsoft_teams.graph import get_graph_client

# Delegated access — create Graph client using the user's token
graph = get_graph_client(ctx.user_token)
me = await graph.me.get()
messages = await graph.me.messages.get()

# App-only access — no user sign-in needed
graph = app.get_app_graph()
users = await graph.users.get()

# Or via context
users = await ctx.app_graph.users.get()
```
