# Teams Graph Integration Demo

This demo application showcases how to use Microsoft Graph APIs within a Teams bot.

## Features

- **User Authentication**: Teams OAuth integration with automatic token management
- **Token Implementation**: Uses callable-based tokens for exact expiration handling
- **Profile Information**: Retrieve and display user profile data
- **Email Access**: List recent emails with Mail.Read scope
- **Automatic Token Refresh**: Intelligent token lifecycle management

## Commands

- `signin` - Authenticate with Microsoft Graph
- `profile` - Display user profile information (requires User.Read)
- `emails` - Show recent emails (requires Mail.Read permission)
- `signout` - Sign out of Microsoft Graph
- `help` - Show available commands and implementation details

## Setup

1. Configure OAuth connection in Azure Bot registration
2. Set connection name to "graph" (or update `default_connection_name` in app options)
3. Configure appropriate Microsoft Graph permissions:
   - `User.Read` (for profile access)
   - `Mail.Read` (for email access)
4. Create a `.env` file with required environment variables (copy from `sample.env`):
   ```
   CONNECTION_NAME=graph
   # PORT=3979  # Optional: specify custom port (defaults to 3979)
   ```

## Running

### Option 1: Using the PowerShell Script (Recommended)

From the `tests/graph/` directory:

```powershell
.\run_demo.ps1
```

### Option 2: Manual PYTHONPATH Setup

From the `tests/graph/` directory:

```powershell
# PowerShell
$env:PYTHONPATH="..\..\packages\graph\src;..\..\packages\api\src;..\..\packages\apps\src;..\..\packages\common\src"
python src\main.py
```

```bash
# Bash (Linux/macOS)
PYTHONPATH="../../packages/graph/src:../../packages/api/src:../../packages/apps/src:../../packages/common/src" python src/main.py
```

### Option 3: Install Packages in Development Mode

From the repository root:

```bash
# Install the graph package in development mode
pip install -e packages/graph
pip install -e packages/api
pip install -e packages/app
pip install -e packages/common

# Then run the demo
python tests/graph/src/main.py
```

## Architecture

The demo uses the `microsoft.teams.graph` package which provides:

- **Token Integration**: Uses callable tokens for exact expiration handling
- **Automatic Token Resolution**: Seamless integration with Teams OAuth tokens
- **Graph Client Factory**: `get_graph_client()` function for creating authenticated clients

## Example Usage

```python
from microsoft.teams.graph import get_graph_client

# Get user's Graph client using their token
graph = get_graph_client(ctx.user_token)

# Access user profile
me = await graph.me.get()

# Access Teams membership
teams = await graph.me.joined_teams.get()

# Access emails
messages = await graph.me.messages.get()
```

## Token Lifecycle

1. User initiates `signin` command
2. Teams OAuth flow completes and stores user token
3. Graph client created with callable token that:
   - Fetches fresh token on each call
   - Includes exact expiration metadata
   - Handles token refresh automatically
4. Graph API calls use current valid token
5. User can `signout` to clear tokens

This approach provides better reliability and eliminates common token expiration issues.

- **`get_graph_client()`** - Main factory function accepting Token values (strings, callables, etc.)
- **`DirectTokenCredential`** - Azure TokenCredential implementation using the unified Token type

### Key Implementation Details

```python
from microsoft.teams.api.clients.user.params import GetUserTokenParams
from microsoft.teams.graph import get_graph_client

# Get token directly from Teams API
token_params = GetUserTokenParams(
    channel_id=ctx.activity.channel_id,
    user_id=ctx.activity.from_.id,
    connection_name=ctx.connection_name,
)

# Get user token and create Graph client directly
token_response = await ctx.api.users.token.get(token_params)

# Create Graph client with string token (simplest approach)
graph = get_graph_client(token_response.token, connection_name=ctx.connection_name)

# Make Graph API calls
me = await graph.me.get()
```
