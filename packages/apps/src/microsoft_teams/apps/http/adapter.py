"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Dict, Literal, Protocol, TypedDict, runtime_checkable

HttpMethod = Literal["POST"]


class HttpRequest(TypedDict):
    body: Dict[str, object]
    headers: Dict[str, str]


class HttpResponse(TypedDict):
    status: int
    body: object


class HttpRouteHandler(Protocol):
    async def __call__(self, request: HttpRequest) -> HttpResponse: ...


@runtime_checkable
class HttpServerAdapter(Protocol):
    """Protocol for framework-specific HTTP server adapters.

    Implement this adapter to plug in any HTTP framework (FastAPI, Starlette, Flask, etc.).
    The SDK calls these methods with framework-agnostic ``HttpRequest``/``HttpResponse``
    objects so the adapter can translate to/from the underlying framework.
    """

    def register_route(self, method: HttpMethod, path: str, handler: HttpRouteHandler) -> None:
        """Register a route handler. Required."""
        ...

    def serve_static(self, path: str, directory: str) -> None:
        """Serve static files from a directory. Optional — no-op by default."""

    async def start(self, port: int) -> None:
        """Start the server. Optional — raises if not implemented."""
        raise NotImplementedError("This adapter does not support managed server lifecycle. Start the server yourself.")

    async def stop(self) -> None:
        """Stop the server. Optional — no-op by default."""
