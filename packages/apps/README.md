> [!CAUTION]
> This project is in public preview. We’ll do our best to maintain compatibility, but there may be breaking changes in upcoming releases. 

# Microsoft Teams Apps Framework

<p>
    <a href="https://pypi.org/project/microsoft-teams-apps" target="_blank">
        <img src="https://img.shields.io/pypi/v/microsoft-teams-apps" />
    </a>
    <a href="https://pypi.org/project/microsoft-teams-apps" target="_blank">
        <img src="https://img.shields.io/pypi/dw/microsoft-teams-apps" />
    </a>
</p>

High-level framework for building Microsoft Teams applications.
Handles activity routing, authentication, and provides Microsoft Graph integration.

<a href="https://microsoft.github.io/teams-ai" target="_blank">
    <img src="https://img.shields.io/badge/📖 Getting Started-blue?style=for-the-badge" />
</a>

## Features

- **Activity Routing**: Decorator-based routing for different activity types
- **OAuth Integration**: Built-in OAuth flow handling for user authentication
- **Microsoft Graph Integration**: Type-safe Graph client access via `user_graph` and `app_graph` properties
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
        try:
            # Access user's Graph data
            me = await ctx.user_graph.me.get()
            await ctx.send(f"Hello {me.display_name}!")
        except (ValueError, RuntimeError, ImportError) as e:
            await ctx.send(f"Graph access failed: {e}")
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

If Graph dependencies are not installed, `user_graph` and `app_graph` will raise an `ImportError` when accessed. If the user is not signed in or tokens are unavailable, they will raise `ValueError`.
