# Microsoft Teams Graph Integration

This package provides seamless access to Microsoft Graph APIs from Teams bots and agents built with the Microsoft Teams AI SDK for Python.

## Requirements

- Teams AI SDK for Python
- Microsoft Graph SDK for Python (msgraph-sdk)
- Azure Core library (azure-core)
- Microsoft Teams Common library (microsoft-teams-common)

## Features

- **Token Type Support**: Uses the unified Token type from microsoft-teams-common
- **Flexible Token Handling**: Accepts strings, StringLike objects, callables, async callables, or None
- **Automatic Token Resolution**: Leverages the common resolve_token utility for consistent token handling

## Quick Start

```python
from microsoft.teams.graph import get_graph_client
from microsoft.teams.apps import App, ActivityContext
from microsoft.teams.api import MessageActivity
from microsoft.teams.api.clients.user.params import GetUserTokenParams

app = App()

@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    if not ctx.is_signed_in:
        await ctx.sign_in()
        return

    # Use the user token that's already available in the context
    graph = get_graph_client(ctx.user_token)

    # Make Graph API calls
    me = await graph.me.get()
    await ctx.send(f"Hello {me.display_name}!")

    # Make Graph API calls
    me = await graph.me.get()
    await ctx.send(f"Hello {me.display_name}!")
```

## Token Type Usage

The package uses the Token type from microsoft-teams-common for flexible token handling. You can provide tokens in several formats:

### String Token (Simplest)

```python
# Direct string token
graph = get_graph_client("eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIs...")
```

### Callable Token (Dynamic)

```python
def get_token():
    """Callable that returns a string token."""
    # Get your access token from wherever (Teams API, cache, etc.)
    return get_access_token_from_somewhere()

# Use the callable with get_graph_client
graph = get_graph_client(get_token)
```

### Async Callable Token

```python
async def get_token_async():
    """Async callable that returns a string token."""
    # Fetch token asynchronously
    token_response = await some_api_call()
    return token_response.access_token

graph = get_graph_client(get_token_async)
```

### Dynamic Token Retrieval

```python
def get_fresh_token():
    """Callable that fetches a fresh token on each invocation."""
    # This will be called each time the Graph client needs a token
    fresh_token = fetch_latest_token_from_api()
    return fresh_token

graph = get_graph_client(get_fresh_token)
```

## Authentication

The package uses Token-based authentication with automatic resolution through the common library. Teams tokens are pre-authorized through the OAuth connection configured in your Azure Bot registration.

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
