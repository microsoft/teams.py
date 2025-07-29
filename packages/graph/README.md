# Microsoft Teams Graph Integration

Microsoft Graph integration for the Teams AI Python SDK. This package provides seamless access to Microsoft Graph APIs from within Teams applications with zero-configuration authentication.

## Quick Start

```python
from microsoft.teams.app import App
from microsoft.teams.api import MessageActivity
from microsoft.teams.graph import enable_graph_integration

# Enable Graph integration
app = App()
enable_graph_integration()

@app.on_message
async def handle_message(context: ActivityContext[MessageActivity]):
    if not context.is_signed_in:
        await context.sign_in()
        return
    
    # Zero-configuration Graph access!
    me = await context.graph.me.get()
    await context.reply(f"Hello {me.display_name}!")
```

## Features

- **Zero Configuration**: Automatic authentication using Teams SDK context
- **Full Graph SDK Power**: Complete access to Microsoft Graph Python SDK capabilities
- **Type Safety**: Comprehensive type hints and IDE support
- **Async-First**: Native async/await support throughout
- **Error Handling**: Consistent error patterns with Teams SDK

## Installation

```bash
pip install microsoft-teams-graph
```

## Requirements

- Python 3.9+
- microsoft-teams-app
- microsoft-teams-api
- azure-identity
- msgraph-sdk

## Status

🚧 **Alpha** - Under active development