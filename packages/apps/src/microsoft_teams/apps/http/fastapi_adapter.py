"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import warnings
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Any, Callable, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.types import ASGIApp, Lifespan

from .adapter import HttpMethod, HttpRequest, HttpResponse, HttpRouteHandler


class FastAPIAdapter:
    """Default HttpServerAdapter implementation wrapping FastAPI + uvicorn."""

    lifespans: List[Lifespan[ASGIApp]]

    def __init__(
        self,
        app: Optional[FastAPI] = None,
        server_factory: Optional[Callable[[FastAPI], uvicorn.Server]] = None,
    ):
        self.lifespans = []
        self._fastapi = app or FastAPI()
        self._server: Optional[uvicorn.Server] = None
        self._server_factory = server_factory

        # Replace the FastAPI app's lifespan with one that chains plugin lifespans
        original_lifespan = self._fastapi.router.lifespan_context

        @asynccontextmanager
        async def combined_lifespan(app: ASGIApp):
            async with AsyncExitStack() as stack:
                for lifespan in self.lifespans:
                    await stack.enter_async_context(lifespan(app))
                await stack.enter_async_context(original_lifespan(app))
                yield

        self._fastapi.router.lifespan_context = combined_lifespan

        if server_factory:
            self._server = server_factory(self._fastapi)
            if self._server.config.app is not self._fastapi:
                raise ValueError(
                    "server_factory must return a uvicorn.Server configured with the provided FastAPI app instance."
                )

    @property
    def app(self) -> FastAPI:
        """The underlying FastAPI instance."""
        return self._fastapi

    def register_route(self, method: HttpMethod, path: str, handler: HttpRouteHandler) -> None:
        """Register a route handler on the FastAPI app."""

        async def fastapi_handler(request: Request) -> Response:
            body: Dict[str, Any] = await request.json()
            headers: Dict[str, str] = dict(request.headers)
            http_request = HttpRequest(body=body, headers=headers)
            result: HttpResponse = await handler(http_request)
            status = result["status"]
            resp_body = result.get("body")
            if resp_body is not None:
                return JSONResponse(content=resp_body, status_code=status)
            return Response(status_code=status)

        if method != "POST":
            raise ValueError(f"Unsupported HTTP method: {method}")
        self._fastapi.post(path)(fastapi_handler)

    def serve_static(self, path: str, directory: str) -> None:
        """Mount a static files directory."""
        name = path.strip("/").replace("/", "-") or "static"
        self._fastapi.mount(path, StaticFiles(directory=directory, check_dir=True, html=True), name=name)

    async def start(self, port: int) -> None:
        """Start the uvicorn server. Blocks until stopped."""
        if self._server:
            if self._server.config.port != port:
                warnings.warn(
                    f"server_factory configured port {self._server.config.port}, "
                    f"but app.start() requested port {port}. Using server_factory port.",
                    stacklevel=2,
                )
        else:
            config = uvicorn.Config(app=self._fastapi, host="0.0.0.0", port=port, log_level="info")
            self._server = uvicorn.Server(config)

        await self._server.serve()

    async def stop(self) -> None:
        """Signal the server to stop."""
        if self._server:
            self._server.should_exit = True
