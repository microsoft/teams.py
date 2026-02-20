> [!CAUTION]
> This project is in public preview. We’ll do our best to maintain compatibility, but there may be breaking changes in upcoming releases.

# Microsoft Teams Common Utilities

<p>
    <a href="https://pypi.org/project/microsoft-teams-common" target="_blank">
        <img src="https://img.shields.io/pypi/v/microsoft-teams-common" />
    </a>
    <a href="https://pypi.org/project/microsoft-teams-common" target="_blank">
        <img src="https://img.shields.io/pypi/dw/microsoft-teams-common" />
    </a>
</p>

Shared utilities including HTTP client, logging, storage, and event handling.
Provides common functionality used across other Teams SDK packages.

<a href="https://microsoft.github.io/teams-sdk" target="_blank">
    <img src="https://img.shields.io/badge/📖 Getting Started-blue?style=for-the-badge" />
</a>

## Features

- **HTTP Client**: Async HTTP client with token support and interceptors
- **Event System**: Type-safe event emitter for application lifecycle management
- **Storage**: Local storage implementations for key-value and list data
- **Logging**: Console logging with formatting and filtering

## HTTP Client

```python
from microsoft_teams.common import Client, ClientOptions

# Create HTTP client
client = Client(ClientOptions(
    base_url="https://api.example.com",
    headers={"User-Agent": "Teams-Bot/1.0"}
))

# Make requests
response = await client.get("/users/me")
data = await client.post("/messages", json={"text": "Hello"})
```

## Event System

```python
from microsoft_teams.common import EventEmitter

# Create type-safe event emitter
emitter = EventEmitter[str]()

# Register handler
def handle_message(data: str):
    print(f"Received: {data}")

subscription_id = emitter.on("message", handle_message)

# Emit event
emitter.emit("message", "Hello World")

# Remove handler
emitter.off(subscription_id)
```

## Storage

```python
from microsoft_teams.common import LocalStorage, ListLocalStorage

# Key-value storage
storage = LocalStorage[str]()
storage.set("key", {"data": "value"})
data = storage.get("key")

# Async operations
await storage.async_set("key", {"data": "value"})
data = await storage.async_get("key")

# List storage
list_storage = ListLocalStorage[str]()
list_storage.append("new-item")
items = list_storage.items()
```

## Logging

The SDK uses Python's standard `logging` module. The library doesn't configure logging - your application should.

```python
import logging

# Configure logging once at application startup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Use module-level loggers in your code
logger = logging.getLogger(__name__)
logger.info("Application started")
```

**Custom Formatting**

The SDK provides optional formatters and filters if you want colored console output:

```python
import logging
from microsoft_teams.common.logging import ConsoleFormatter, ConsoleFilter

# Create handler with custom formatter
handler = logging.StreamHandler()
handler.setFormatter(ConsoleFormatter())
handler.addFilter(ConsoleFilter("microsoft_teams.*"))  # Filter by pattern

# Configure root logger
logging.root.addHandler(handler)
logging.root.setLevel(logging.DEBUG)
```

**Advanced Configuration**

For production, use `dictConfig` for greater control:

```python
import logging.config

logging.config.dictConfig({
    "version": 1,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default"
        }
    },
    "loggers": {
        "microsoft_teams": {
            "level": "DEBUG",
            "handlers": ["console"]
        }
    }
})
```
