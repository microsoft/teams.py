"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Dict, Literal, NotRequired, Optional, Protocol, TypedDict, runtime_checkable

from microsoft_teams.api import Credentials, TokenProtocol
from microsoft_teams.api.auth.cloud_environment import CloudEnvironment

HttpMethod = Literal["POST"]


class HttpServerInitializeDeps(TypedDict, total=False):
    """App-level dependencies forwarded to the adapter at initialization, before ``start()``."""

    credentials: Optional[Credentials]
    cloud: Optional[CloudEnvironment]


class HttpRequest(TypedDict):
    body: Dict[str, object]
    headers: Dict[str, str]
    # Pre-authenticated caller identity for transports that authenticate at the
    # connection level (e.g. Socket Mode) rather than per request. When set,
    # HttpServer trusts it and skips per-request token validation. HTTP adapters
    # leave this unset so normal Authorization-header validation runs.
    token: NotRequired[Optional[TokenProtocol]]


class HttpResponse(TypedDict):
    status: int
    body: object


class HttpRouteHandler(Protocol):
    async def __call__(self, request: HttpRequest) -> HttpResponse: ...


@runtime_checkable
class HttpServerAdapter(Protocol):
    """Protocol for framework-specific inbound transport adapters.

    Implement this adapter to plug in any HTTP framework (FastAPI, Starlette, Flask, etc.),
    or a non-HTTP transport. The SDK calls these methods with framework-agnostic
    ``HttpRequest``/``HttpResponse`` objects so the adapter can translate to/from the
    underlying transport.

    method (sync) to receive app-level ``credentials``/``cloud`` before ``start()``.
    It's not part of this Protocol (so existing adapters aren't forced to implement it) —
    ``HttpServer.initialize()`` calls it via ``getattr(...)`` when present. Most HTTP adapters
    (e.g. ``FastAPIAdapter``) don't need it; transports that authenticate the connection itself
    (e.g. Socket Mode) implement it to get credentials/cloud through this seam.
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
