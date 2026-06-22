# HTTP Adapters Examples

Examples showing how to use shipped `HttpServerAdapter` implementations and non-managed server patterns with the Teams Python SDK.

## Examples

### 1. Starlette Adapter (`starlette_echo.py`)

The shipped `StarletteAdapter` implementation for [Starlette](https://www.starlette.io/).

**Pattern**: Custom adapter, SDK-managed server lifecycle (`app.start()`)

```bash
python src/starlette_echo.py
```

### 2. Non-Managed FastAPI (`fastapi_non_managed.py`)

Use your own FastAPI app with your own routes, and let the SDK register `/api/messages` on it. You manage the server lifecycle yourself.

**Pattern**: Default `FastAPIAdapter` with user-provided FastAPI instance, user-managed server (`app.register_routes()` + `await app.start_plugins()` + your own `uvicorn.Server`)

```bash
python src/fastapi_non_managed.py
```

## Key Concepts

### Managed vs Non-Managed

| | Managed | Non-Managed |
|---|---|---|
| **Entry point** | `app.start(port)` | `app.register_routes()` + `await app.start_plugins()` + start server yourself |
| **Who starts the server** | The SDK (via adapter) | You |
| **When to use** | New apps, simple setup | Existing apps, custom server config |

`app.register_routes()` is synchronous and registers the Teams messaging route
without running async plugin initialization. Run `await app.start_plugins()` from
your host's startup hook when the event loop is available.

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
