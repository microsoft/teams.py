# Teams Graph Integration Demo

This demo application showcases how to use Microsoft Graph APIs within a Teams bot built with the
Teams AI SDK for Python using the new direct token approach.

## Features

- User authentication via Teams OAuth
- Direct token retrieval from Teams API
- Profile information retrieval with Microsoft Graph
- Email listing with Mail.Read scope
- Proper error handling and user feedback
- Interactive command interface
- Consolidated authentication helper function

## Commands

- `signin` - Authenticate with Microsoft Graph
- `profile` - Display user profile information
- `emails` - Show recent emails (requires Mail.Read permission)
- `signout` - Sign out of Microsoft Graph
- `help` - Show available commands

## Setup

1. Configure OAuth connection in Azure Bot registration
2. Set connection name to "graph" (or update `default_connection_name` in app options)
3. Configure appropriate Microsoft Graph permissions:
   - `User.Read` (for profile access)
   - `Mail.Read` (for email access)
4. Create a `.env` file with required environment variables:
   ```
   CONNECTION_NAME=graph
   # PORT=3979  # Optional: specify custom port (defaults to 3979)
   ```

## Running

From the demo directory:

```bash
python main.py
```

Or from the repository root:

```bash
python packages/graph/tests/demo/main.py
```

## Architecture

The demo uses the `microsoft.teams.graph` package which provides:

- **`get_graph_client()`** - Main factory function accepting the flexible Token pattern
- **`DirectTokenCredential`** - Azure TokenCredential implementation for string tokens
- **Token Pattern Approach** - Uses Teams SDK Token pattern for flexible token handling

### Key Implementation Details

```python
# Get token directly from Teams API
token_params = GetUserTokenParams(
    channel_id=ctx.activity.channel_id,
    user_id=ctx.activity.from_.id,
    connection_name=ctx.connection_name,
)
token_response = await ctx.api.users.token.get(token_params)

# Create Graph client with direct token
graph = await get_graph_client(token_response.token, connection_name=ctx.connection_name)

# Make Graph API calls
me = await graph.me.get()
```

This approach provides maximum flexibility and can be used in any scenario where tokens are available, not just within ActivityContext.

```

```
