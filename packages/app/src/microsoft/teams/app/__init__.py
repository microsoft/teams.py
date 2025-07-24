"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from . import auth
from .app import App
from .auth import *  # noqa: F403
from .http_plugin import HttpPlugin
from .options import AppOptions
from .plugin import PluginProtocol

# Combine all exports from submodules
__all__: list[str] = [
    "App",
    "AppOptions",
    "HttpPlugin",
    "PluginProtocol",
]
__all__.extend(auth.__all__)
