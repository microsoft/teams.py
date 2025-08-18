"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from fastapi import APIRouter

from .context import RouteContext
from .v3 import v3_router


def get_router(context: RouteContext):
    router = APIRouter()
    updated_context = RouteContext(port=context.port, log=context.log.getChild("v3"), process=context.process)
    res = v3_router(updated_context)
    router.include_router(res, prefix="/v3")
    return router
