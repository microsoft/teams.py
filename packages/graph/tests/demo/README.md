# Teams Graph Integration Demo

This demo application showcases how to use Microsoft Graph APIs within a Teams bot built with the
Teams AI SDK for Python using the new TokenProtocol approach.

## Features

- User authentication via Teams OAuth
- TokenProtocol-based token management with exact expiration times
- Profile information retrieval with Microsoft Graph
- Email listing with Mail.Read scope
- Proper error handling and user feedback
- Interactive command interface
- Structured token metadata with type safety

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

- **`get_graph_client()`** - Main factory function accepting TokenProtocol callable functions
- **`DirectTokenCredential`** - Azure TokenCredential implementation for TokenProtocol objects
- **TokenProtocol Approach** - Uses structured token metadata with exact expiration times

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

This approach provides:
- **Exact expiration handling** with `datetime.datetime` objects
- **Fresh token retrieval** on each Graph API request
- **Type safety** with Protocol compliance
- **Structured metadata** including token type and scope
