# Teams Graph Integration Demo

This demo application showcases how to use Microsoft Graph APIs within a Teams bot built with the
Teams AI SDK for Python using the new TokenProtocol approach.

## Features

- User authentication via Teams OAuth
- TokenProtocol-based token management with exact expiration times
- Profile information retrieval with Microsoft Graph
- Email listing with Mail.Read scope
- Simple authentication with pre-authorized Teams tokens

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
4. Create a `.env` file with required environment variables (copy from `.env.example`):
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
$env:PYTHONPATH="..\..\packages\graph\src;..\..\packages\api\src;..\..\packages\app\src;..\..\packages\common\src"
python src\main.py
```

```bash
# Bash (Linux/macOS)
PYTHONPATH="../../packages/graph/src:../../packages/api/src:../../packages/app/src:../../packages/common/src" python src/main.py
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

- **`get_graph_client()`** - Main factory function accepting TokenProtocol callable functions
- **`DirectTokenCredential`** - Azure TokenCredential implementation for TokenProtocol objects
- **TokenProtocol Approach** - Uses structured token metadata with exact expiration times
- **Pre-authorized Authentication** - Works seamlessly with Teams OAuth tokens without complex validation

### Key Implementation Details

```python
import datetime
from typing import Optional

class TokenData:
    """Token data class that implements TokenProtocol."""

    def __init__(self, access_token: str, expires_in_seconds: int = 3600):
        self.access_token = access_token
        # Calculate exact expiration time
        self.expires_at: Optional[datetime.datetime] = datetime.datetime.now(
            datetime.timezone.utc
        ) + datetime.timedelta(seconds=expires_in_seconds)
        self.token_type: Optional[str] = "Bearer"
        self.scope: Optional[str] = "https://graph.microsoft.com/.default"

# Get token directly from Teams API
token_params = GetUserTokenParams(
    channel_id=ctx.activity.channel_id,
    user_id=ctx.activity.from_.id,
    connection_name=ctx.connection_name,
)

def get_fresh_token():
    """Callable that returns fresh token data implementing TokenProtocol."""
    token_response = asyncio.get_event_loop().run_until_complete(
        ctx.api.users.token.get(token_params)
    )
    return TokenData(token_response.token, expires_in_seconds=3600)

# Create Graph client with TokenProtocol callable
graph = await get_graph_client(get_fresh_token, connection_name=ctx.connection_name)

# Make Graph API calls
me = await graph.me.get()
```
