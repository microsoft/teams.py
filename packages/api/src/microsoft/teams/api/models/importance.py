"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from enum import Enum


class Importance(str, Enum):
    """Enum for user identity types."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
