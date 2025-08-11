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

- **Direct Token Support**: Works with tokens directly using the flexible Token pattern from the Teams SDK
- **Flexible Input**: Accepts strings, callables, async functions, and other token types
- **Automatic Token Management**: Handles expiration validation with intelligent caching
- **Type Safe**: Full typing support with intellisense
- **High Performance**: Intelligent caching and minimal overhead
- **Pythonic**: Follows Python and Teams SDK conventions

## Quick Start

```python
from microsoft.teams.graph import get_graph_client
from microsoft.teams.app import App, ActivityContext
from microsoft.teams.api import MessageActivity, GetUserTokenParams

app = App()

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
    token_response = await ctx.api.users.token.get(token_params)

    # Create Graph client with direct token
    graph = await get_graph_client(token_response.token, connection_name="graph")

    # Make Graph API calls
    me = await graph.me.get()
    await ctx.send(f"Hello {me.display_name}!")
```

## Token Usage

The package uses the flexible Token pattern from the Teams SDK, accepting various token types:

### Using String Tokens

```python
# Raw token string (expiration defaults to 1 hour)
token_string = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIs..."
graph = await get_graph_client(token_string)
```

### Using Token Factories

```python
# Callable that returns a token
def get_token():
    return get_access_token_from_somewhere()

graph = await get_graph_client(get_token)

# Async callable for dynamic token retrieval
async def get_token_async():
    return await fetch_token_from_api()

graph = await get_graph_client(get_token_async)
```

## Authentication

The package uses direct token management with the Teams SDK Token pattern. Ensure your app is configured with the appropriate OAuth connection (typically named "graph") in your Azure Bot registration. The package does not handle token refresh - use fresh tokens from the Teams API or your token source.

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
