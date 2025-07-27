"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from . import auth, events
from .app import App
from .auth import *  # noqa: F403
from .events import *  # noqa: F401, F403
from .http_plugin import HttpPlugin
from .options import AppOptions
from .plugin import PluginProtocol
from .routing import ActivityContext

# Combine all exports from submodules
__all__: list[str] = ["App", "AppOptions", "HttpPlugin", "PluginProtocol", "ActivityContext"]
__all__.extend(auth.__all__)
__all__.extend(events.__all__)
