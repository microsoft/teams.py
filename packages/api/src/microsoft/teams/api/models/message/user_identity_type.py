"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from enum import Enum


class UserIdentityType(str, Enum):
    """Enum for user identity types."""

    AAD_USER = "aadUser"
    ON_PREMISE_AAD_USER = "onPremiseAadUser"
    ANONYMOUS_GUEST = "anonymousGuest"
    FEDERATED_USER = "federatedUser"
