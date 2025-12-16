"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from fastapi import APIRouter

from ...context import RouteContext
from .activities import activities_router


def get_router(ctx: RouteContext):
    router = APIRouter()
    updated_context = RouteContext(port=ctx.port, log=ctx.log.getChild("activities"), process=ctx.process)
    res = activities_router(updated_context)
    router.include_router(res, prefix="/{conversationId}/activities")
    return router
