"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from fastapi import APIRouter

from ..context import RouteContext
from .conversations import conversations_router


def get_router(ctx: RouteContext):
    router = APIRouter()
    updated_context = RouteContext(port=ctx.port, log=ctx.log.getChild("conversations"), process=ctx.process)
    res = conversations_router(updated_context)
    router.include_router(res, prefix="/conversations")
    return router
