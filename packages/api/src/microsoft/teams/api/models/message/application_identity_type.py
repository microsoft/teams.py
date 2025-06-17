"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from enum import Enum


class ApplicationIdentityType(str, Enum):
    """Enum for application identity types."""

    AAD_APPLICATION = "aadApplication"
    BOT = "BOT"
    TENANT_BOT = "tenantBot"
    OFFICE_365_CONNECTOR = "office365Connector"
    WEBHOOK = "webhook"
