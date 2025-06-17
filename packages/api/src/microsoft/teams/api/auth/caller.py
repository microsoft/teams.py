"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

CallerType = Literal["azure", "gov", "bot"]

CALLER_IDS = {
    "azure": "urn:botframework:azure",
    "gov": "urn:botframework:azureusgov",
    "bot": "urn:botframework:aadappid",
}
