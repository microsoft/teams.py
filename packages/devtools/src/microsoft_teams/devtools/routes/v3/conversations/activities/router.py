"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from fastapi import APIRouter, Request, Response

from ....context import RouteContext
from .create import create


def get_router(context: RouteContext):
    router = APIRouter()

    # Define the POST route
    @router.post("")
    async def create_endpoint(request: Request, response: Response):  # type: ignore
        updated_context = RouteContext(port=context.port, log=context.log.getChild("create"), process=context.process)
        handler = await create(updated_context)
        return await handler(request, response)

    return router
