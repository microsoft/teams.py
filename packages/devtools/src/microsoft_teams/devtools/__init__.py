"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
import warnings

from .devtools_plugin import DevToolsPlugin
from .page import Page

logging.getLogger(__name__).addHandler(logging.NullHandler())

warnings.warn(
    "microsoft-teams-devtools is deprecated and will no longer be maintained. "
    "We recommend testing with Microsoft Teams directly, or with the Agents Playground: "
    "https://learn.microsoft.com/en-us/microsoftteams/platform/toolkit/debug-your-agents-playground",
    FutureWarning,
    stacklevel=2,
)

__all__: list[str] = ["DevToolsPlugin", "Page"]
