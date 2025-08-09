"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

# Enum for application identity types.
ApplicationIdentityType = (
    Literal[
        "aadApplication",
        "BOT",
        "tenantBot",
        "office365Connector",
        "webhook",
    ]
    | str
)
