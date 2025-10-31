> [!CAUTION]
> This project is in public preview. We’ll do our best to maintain compatibility, but there may be breaking changes in upcoming releases. 

# Microsoft Teams DevTools

<p>
    <a href="https://pypi.org/project/microsoft-teams-devtools" target="_blank">
        <img src="https://img.shields.io/pypi/v/microsoft-teams-devtools" />
    </a>
    <a href="https://pypi.org/project/microsoft-teams-devtools" target="_blank">
        <img src="https://img.shields.io/pypi/dw/microsoft-teams-devtools" />
    </a>
</p>

Developer tools for locally testing and debugging Teams applications. Streamlines the development process by eliminating the need to deploy apps or expose public endpoints during development.

<a href="https://microsoft.github.io/teams-ai" target="_blank">
    <img src="https://img.shields.io/badge/📖 Getting Started-blue?style=for-the-badge" />
</a>

## Features

- **Local Testing**: Test Teams apps locally without deployment
- **Bot Emulator**: Simulate Teams conversations and interactions
- **Web Interface**: Browser-based UI for testing bot responses
- **Activity Inspector**: View and inspect incoming/outgoing activities
- **No Tunneling Required**: Works entirely locally without ngrok or similar tools

## Installation

```bash
# Using uv (recommended)
uv add microsoft-teams-devtools

# Using pip
pip install microsoft-teams-devtools
```

## Quick Start

```python
from microsoft.teams.apps import App
from microsoft.teams.devtools import DevToolsPlugin

app = App()

# Add DevTools plugin (automatically enabled in development)
app.use(DevToolsPlugin(port=3979))

# Start your app
await app.start()

# Open http://localhost:3979/devtools in your browser
```

## Using the Web Interface

Once your app is running with DevTools enabled:

1. Navigate to `http://localhost:3979/devtools`
2. Send messages to your bot through the interface
3. View bot responses and activity logs in real-time
4. Inspect activity payloads and debug issues

## Configuration

```python
# Customize DevTools settings
devtools = DevToolsPlugin(
    port=3979,  # DevTools UI port
    host="localhost",  # Bind address
    auto_open=True  # Open browser automatically
)

app.use(devtools)
```

## Environment-Based Activation

```python
import os

# Only enable DevTools in development
if os.getenv("ENVIRONMENT") == "development":
    app.use(DevToolsPlugin())
```

## Debugging Tips

- Use the activity inspector to examine message payloads
- Test different message types (text, cards, attachments)
- Verify authentication flows locally
- Debug action handlers without Teams client
