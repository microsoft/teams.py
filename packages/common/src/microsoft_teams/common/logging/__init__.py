"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import warnings

from .ansi import ANSI
from .console import ConsoleLogger, ConsoleLoggerOptions
from .filter import ConsoleFilter
from .formatter import ConsoleFormatter

# Issue deprecation warning
warnings.warn(
    "The 'ConsoleLogger' class is deprecated and will be removed in version 2.0.0 GA."
    + " Please update your imports to use the standard Python logging library instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["ANSI", "ConsoleFormatter", "ConsoleFilter", "ConsoleLogger", "ConsoleLoggerOptions"]
