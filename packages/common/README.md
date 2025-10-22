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

<a href="https://microsoft.github.io/teams-ai" target="_blank">
    <img src="https://img.shields.io/badge/📖 Getting Started-blue?style=for-the-badge" />
</a>

## Features

- **HTTP Client**: Async HTTP client with token support and interceptors
- **Event System**: Type-safe event emitter for application lifecycle management
- **Storage**: Local storage implementations for key-value and list data
- **Logging**: Console logging with formatting and filtering

## HTTP Client

```python
from microsoft.teams.common import Client, ClientOptions

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
from microsoft.teams.common import EventEmitter

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
from microsoft.teams.common import LocalStorage, ListLocalStorage

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

```python
from microsoft.teams.common import ConsoleLogger

# Create console logger
logger = ConsoleLogger().create_logger("my-app")
```
