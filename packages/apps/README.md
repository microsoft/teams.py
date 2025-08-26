> [!CAUTION]
> This project is in active development and not ready for production use. It has not been publicly announced yet.

# Microsoft Teams App Framework

High-level framework for building Microsoft Teams bots and applications.
Handles routing, middleware, events, and provides OAuth integration for Teams apps.

## Features

- **Activity Routing**: Flexible routing system for handling different activity types
- **Middleware Support**: Extensible middleware chain for request processing
- **OAuth Integration**: Built-in OAuth flow handling for user authentication
- **Microsoft Graph Integration**: Direct access to Graph APIs through `user_graph` and `app_graph` properties
- **Plugin System**: Extensible plugin architecture for adding functionality
- **Event Handling**: Comprehensive event system for application lifecycle management

## Graph Clients

The framework provides seamless Microsoft Graph integration through two client types:

### User Graph Client (`ctx.user_graph`)

Authenticated with the signed-in user's token for user-specific operations:

```python
@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    if ctx.is_signed_in:
        # User is signed in, now we can safely access user_graph
        if ctx.user_graph:
            me = await ctx.user_graph.me.get()
            await ctx.send(f"Hello {me.display_name}!")
    else:
        # User needs to sign in first
        await ctx.sign_in()
```

### App Graph Client (`ctx.app_graph`)

Authenticated with the application's token for app-only operations:

```python
@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    if ctx.app_graph:
        # App-only operations
        app_info = await ctx.app_graph.applications.by_application_id("app-id").get()
        await ctx.send(f"App: {app_info.display_name}")
```

Both clients are lazily initialized and automatically handle authentication through the framework's token management system.
