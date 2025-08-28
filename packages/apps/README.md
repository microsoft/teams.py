> [!CAUTION]
> This project is in active development and not ready for production use. It has not been publicly announced yet.

# Microsoft Teams App Framework

High-level framework for building Microsoft Teams applications.
Handles activity routing, authentication, and provides Microsoft Graph integration.

## Features

- **Activity Routing**: Decorator-based routing for different activity types
- **OAuth Integration**: Built-in OAuth flow handling for user authentication
- **Microsoft Graph Integration**: Optional Graph client access via `user_graph` and `app_graph`
- **Plugin System**: Extensible plugin architecture for adding functionality

## Basic Usage

```python
from microsoft.teams.apps import App, ActivityContext
from microsoft.teams.api import MessageActivity

app = App()

@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    await ctx.send(f"You said: {ctx.activity.text}")

# Start the app
await app.start()
```

## OAuth and Graph Integration

```python
@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    if ctx.is_signed_in:
        # Access user's Graph data
        if ctx.user_graph:
            me = await ctx.user_graph.me.get()
            await ctx.send(f"Hello {me.display_name}!")
    else:
        # Prompt user to sign in
        await ctx.sign_in()
```

## Optional Graph Dependencies

Microsoft Graph functionality requires additional dependencies:

```bash
# Recommended: Using uv
uv add microsoft-teams-apps[graph]

# Alternative: Using pip
pip install microsoft-teams-apps[graph]
```

If Graph dependencies are not installed, `user_graph` and `app_graph` return `None`.
