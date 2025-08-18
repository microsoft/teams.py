# Microsoft Teams Graph Integration

This package provides seamless access to Microsoft Graph APIs from Teams bots and agents built with the Microsoft Teams AI SDK for Python.

## Requirements

- Teams AI SDK for Python
- Microsoft Graph SDK for Python (msgraph-sdk)
- Azure Core library (azure-core)
- Azure Identity library (azure-identity)
- Cryptography library (cryptography)
- PyJWT with crypto support (PyJWT[crypto])

## Features

- **TokenProtocol Support**: Uses structured token metadata with exact expiration times
- **Callable-Based Pattern**: Accepts only callable functions that return TokenProtocol-compliant objects

## Quick Start

```python
from microsoft.teams.graph import get_graph_client
from microsoft.teams.app import App, ActivityContext
from microsoft.teams.api import MessageActivity
from microsoft.teams.api.clients.user.params import GetUserTokenParams
import datetime
from typing import Optional

app = App()

class TokenData:
    """Token data class that implements TokenProtocol."""

    def __init__(self, access_token: str, expires_in_seconds: int = 3600):
        self.access_token = access_token
        self.expires_at: Optional[datetime.datetime] = datetime.datetime.now(
            datetime.timezone.utc
        ) + datetime.timedelta(seconds=expires_in_seconds)
        self.token_type: Optional[str] = "Bearer"
        self.scope: Optional[str] = "https://graph.microsoft.com/.default"

@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    if not ctx.is_signed_in:
        await ctx.sign_in()
        return

    # Get user token directly from Teams API
    token_params = GetUserTokenParams(
        channel_id=ctx.activity.channel_id,
        user_id=ctx.activity.from_.id,
        connection_name=ctx.connection_name,
    )

    # Get user token once before creating the client to avoid event loop conflicts
    token_response = await ctx.api.users.token.get(token_params)

    def get_fresh_token():
        """Callable that returns fresh token implementing TokenProtocol."""
        # Return the token we already retrieved to avoid async/sync conflicts
        return TokenData(token_response.token, expires_in_seconds=3600)

    # Create Graph client with TokenProtocol callable
    graph = await get_graph_client(get_fresh_token, connection_name="graph")

    # Make Graph API calls
    me = await graph.me.get()
    await ctx.send(f"Hello {me.display_name}!")
```

## TokenProtocol Usage

The package uses the TokenProtocol interface for structured token metadata. You must provide a callable that returns an object implementing the TokenProtocol.

### TokenProtocol Interface

```python
from typing import Protocol, Optional
import datetime

class TokenProtocol(Protocol):
    """Protocol for structured token metadata."""
    access_token: str
    expires_at: Optional[datetime.datetime]
    token_type: Optional[str]
    scope: Optional[str]
```

### Creating Token Data

```python
import datetime
from typing import Optional

class MyTokenData:
    """Custom implementation of TokenProtocol."""

    def __init__(self, access_token: str, expires_in_seconds: int = 3600):
        self.access_token = access_token
        # Use exact datetime objects for precise expiration handling
        self.expires_at: Optional[datetime.datetime] = datetime.datetime.now(
            datetime.timezone.utc
        ) + datetime.timedelta(seconds=expires_in_seconds)
        self.token_type: Optional[str] = "Bearer"
        self.scope: Optional[str] = "https://graph.microsoft.com/.default"

# Create a callable that returns TokenProtocol-compliant data
def get_token():
    # Get your access token from wherever (Teams API, cache, etc.)
    raw_token = get_access_token_from_somewhere()
    return MyTokenData(raw_token, expires_in_seconds=3600)

# Use the callable with get_graph_client
graph = await get_graph_client(get_token)
```

### Dynamic Token Retrieval

```python
def get_fresh_token():
    """Callable that fetches a fresh token on each invocation."""
    # This will be called each time the Graph client needs a token
    fresh_token = fetch_latest_token_from_api()
    return MyTokenData(fresh_token, expires_in_seconds=3600)

graph = await get_graph_client(get_fresh_token)
```

## Authentication

The package uses TokenProtocol-based token management for structured metadata and exact expiration handling. Teams tokens are pre-authorized through the OAuth connection configured in your Azure Bot registration.

## API Usage Examples

```python
# Get user profile
me = await graph.me.get()

# Get recent emails with specific fields
from msgraph.generated.users.item.messages.messages_request_builder import MessagesRequestBuilder

query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
    select=["subject", "from", "receivedDateTime"],
    top=5
)
request_config = MessagesRequestBuilder.MessagesRequestBuilderGetRequestConfiguration(
    query_parameters=query_params
)
messages = await graph.me.messages.get(request_configuration=request_config)
```
