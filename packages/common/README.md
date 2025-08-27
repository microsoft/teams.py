> [!CAUTION]
> This project is in active development and not ready for production use. It has not been publicly announced yet.

# Microsoft Teams Common Utilities

Shared utilities including HTTP client, logging, storage, and event handling.
Provides common functionality used across other Teams SDK packages.

## Features

- **HTTP Client**: Robust async HTTP client with interceptors and middleware
- **Token Resolution**: Unified Token type supporting strings, callables, and async functions
- **Event System**: Type-safe event emitter for application lifecycle management
- **Storage Abstraction**: Local and distributed storage interfaces
- **Logging Framework**: Structured logging with Teams-specific formatters
- **Utility Functions**: Common helpers for Teams development

## HTTP Client

```python
from microsoft.teams.common import Client, ClientOptions

# Create HTTP client with options
client = Client(ClientOptions(
    base_url="https://api.example.com",
    headers={"User-Agent": "Teams-Bot/1.0"},
    timeout=30.0
))

# Make requests
response = await client.get("/users/me")
data = await client.post("/messages", json={"text": "Hello"})
```

## Token System

```python
from microsoft.teams.common.http.client_token import Token, resolve_token

# String token
token: Token = "bearer-token-string"

# Callable token (synchronous)
def get_token() -> str:
    return fetch_current_token()

# Async callable token
async def get_async_token() -> str:
    return await fetch_token_async()

# Resolve any token type to string
token_string = await resolve_token(token)
```

## Event System

```python
from microsoft.teams.common import EventEmitter

# Type-safe event emitter
emitter = EventEmitter[str]()

# Register handler
@emitter.on("message")
async def handle_message(data: str):
    print(f"Received: {data}")

# Emit event
await emitter.emit("message", "Hello World")
```

## Storage

```python
from microsoft.teams.common import LocalStorage, ListLocalStorage

# Key-value storage
storage = LocalStorage()
await storage.write("key", {"data": "value"})
data = await storage.read("key")

# List storage
list_storage = ListLocalStorage()
await list_storage.append("items", "new-item")
items = await list_storage.read("items")
```