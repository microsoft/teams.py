"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from enum import Enum
from typing import Literal


class CallerIds(str, Enum):
    """Enum for caller ID types."""

    AZURE = "azure"
    GOV = "gov"
    BOT = "bot"


CallerType = Literal["azure", "gov", "bot"]
