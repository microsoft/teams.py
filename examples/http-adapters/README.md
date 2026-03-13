# HTTP Adapters Examples

Examples showing how to use custom `HttpServerAdapter` implementations and non-managed server patterns with the Teams Python SDK.

## Examples

### 1. Starlette Adapter (`starlette_echo.py`)

A custom `HttpServerAdapter` implementation for [Starlette](https://www.starlette.io/). Demonstrates how to write an adapter for any ASGI framework.

**Pattern**: Custom adapter, SDK-managed server lifecycle (`app.start()`)

```bash
python src/starlette_echo.py
```

### 2. Non-Managed FastAPI (`fastapi_non_managed.py`)

Use your own FastAPI app with your own routes, and let the SDK register `/api/messages` on it. You manage the server lifecycle yourself.

**Pattern**: Default `FastAPIAdapter` with user-provided FastAPI instance, user-managed server (`app.initialize()` + your own `uvicorn.Server`)

```bash
python src/fastapi_non_managed.py
```

## Key Concepts

### Managed vs Non-Managed

| | Managed | Non-Managed |
|---|---|---|
| **Entry point** | `app.start(port)` | `app.initialize()` + start server yourself |
| **Who starts the server** | The SDK (via adapter) | You |
| **When to use** | New apps, simple setup | Existing apps, custom server config |

### Writing a Custom Adapter

Implement the `HttpServerAdapter` protocol:

```python
class MyAdapter:
    def register_route(self, method, path, handler): ...
    def serve_static(self, path, directory): ...
    async def start(self, port): ...
    async def stop(self): ...
```

The handler signature is framework-agnostic:

```python
async def handler(request: HttpRequest) -> HttpResponse:
    # request = { "body": dict, "headers": dict }
    # return   { "status": int, "body": object }
```
