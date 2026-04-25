"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from . import conversations
from .conversations import *  # noqa: F401, F403
from .router import get_router as v3_router

# Combine all exports from submodules
__all__: list[str] = ["v3_router"]
__all__.extend(conversations.__all__)
