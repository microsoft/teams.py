# Microsoft Teams Graph Integration

This package provides seamless access to Microsoft Graph APIs from Teams bots and agents built with the Microsoft Teams AI SDK for Python.

## Features

- Zero Configuration: Works with existing Teams OAuth setup
- Automatic Token Management: Handles refresh and expiration automatically  
- Type Safe: Full typing support with intellisense
- High Performance: Intelligent caching and minimal overhead
- Pythonic: Follows Python and Teams SDK conventions

## Quick Start

```python
from microsoft.teams.graph import get_graph_client
from microsoft.teams.app import App, ActivityContext
from microsoft.teams.api import MessageActivity

app = App()

@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    if not ctx.is_signed_in:
        await ctx.sign_in()
        return
    
    # Get Graph client
    graph = await get_graph_client(ctx)
    
    # Make Graph API calls
    me = await graph.me.get()
    await ctx.send(f"Hello {me.display_name}\!")
```

## Authentication

The package automatically uses the Teams OAuth infrastructure. Ensure your app is configured with the appropriate OAuth connection (typically named "graph") in your Azure Bot registration.

## Custom Scopes

```python
# Request specific scopes
graph = await get_graph_client(ctx, scopes=["User.Read", "Mail.Read"])

# Access user's emails
messages = await graph.me.messages.get()
```

## Requirements

- Teams AI SDK for Python
- Microsoft Graph SDK for Python (msgraph-sdk)
- Azure Identity library (azure-identity)
EOF < /dev/null
