"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from ..custom_base_model import CustomBaseModel


class ClientInfoEntity(CustomBaseModel):
    """Client information entity"""

    type: Literal["clientInfo"] = "clientInfo"
    "Type identifier for client info"

    locale: Optional[str] = None
    "Client locale (ex en-US)"

    country: Optional[str] = None
    "Client country code (ex US)"

    platform: Optional[str] = None
    "Client platform (ex Web)"

    timezone: Optional[str] = None
    "Client timezone (ex America/New_York)"
