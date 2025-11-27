"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from . import v3
from .context import RouteContext
from .router import get_router
from .v3 import *  # noqa: F401, F403

# Combine all exports from submodules
__all__: list[str] = ["get_router", "RouteContext"]
__all__.extend(v3.__all__)
