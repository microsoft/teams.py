"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Starlette Adapter
=================
A custom HttpServerAdapter implementation for Starlette.

This shows how to implement the adapter protocol for any ASGI framework.
The adapter translates between the framework's request/response model
and the SDK's pure handler pattern: ({ body, headers }) -> { status, body }.
"""

from typing import Optional

import uvicorn
from microsoft_teams.apps.http.adapter import HttpMethod, HttpRequest, HttpResponse, HttpRouteHandler
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles


class StarletteAdapter:
    """
    HttpServerAdapter implementation wrapping Starlette + uvicorn.

    Usage:
        adapter = StarletteAdapter()
        app = App(http_server_adapter=adapter)
        await app.start(3978)

    Or bring your own Starlette instance:
        starlette_app = Starlette()
        adapter = StarletteAdapter(starlette_app)
        app = App(http_server_adapter=adapter)
        await app.initialize()  # Just registers routes, doesn't start server
    """

    def __init__(self, app: Optional[Starlette] = None):
        self._app = app or Starlette()
        self._is_user_provided = app is not None
        self._server: Optional[uvicorn.Server] = None
        self._routes: list[Route] = []

    @property
    def app(self) -> Starlette:
        """The underlying Starlette instance."""
        return self._app

    def register_route(self, method: HttpMethod, path: str, handler: HttpRouteHandler) -> None:
        """Register a route handler on the Starlette app."""

        async def starlette_handler(request: Request) -> Response:
            body = await request.json()
            headers = dict(request.headers)
            http_request = HttpRequest(body=body, headers=headers)
            result: HttpResponse = await handler(http_request)
            status = result["status"]
            resp_body = result.get("body")
            if resp_body is not None:
                return JSONResponse(content=resp_body, status_code=status)
            return Response(status_code=status)

        route = Route(path, starlette_handler, methods=[method])
        self._routes.append(route)
        self._app.routes.insert(0, route)

    def serve_static(self, path: str, directory: str) -> None:
        """Mount a static files directory."""
        name = path.strip("/").replace("/", "-") or "static"
        mount = Mount(path, app=StaticFiles(directory=directory, check_dir=True, html=True), name=name)
        self._app.routes.append(mount)

    async def start(self, port: int) -> None:
        """Start the uvicorn server. Blocks until stopped."""
        if self._is_user_provided:
            raise RuntimeError(
                "Cannot call start() when a Starlette instance was provided by user. "
                "Manage the server lifecycle yourself."
            )

        config = uvicorn.Config(app=self._app, host="0.0.0.0", port=port, log_level="info")
        self._server = uvicorn.Server(config)
        await self._server.serve()

    async def stop(self) -> None:
        """Signal the server to stop."""
        if self._server:
            self._server.should_exit = True
