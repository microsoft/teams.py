"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging

from .devtools_plugin import DevToolsPlugin
from .page import Page

logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__: list[str] = ["DevToolsPlugin", "Page"]
