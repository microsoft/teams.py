"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

# User identity types.
UserIdentityType = (
    Literal[
        "aadUser",
        "onPremiseAadUser",
        "anonymousGuest",
        "federatedUser",
    ]
    | str
)
