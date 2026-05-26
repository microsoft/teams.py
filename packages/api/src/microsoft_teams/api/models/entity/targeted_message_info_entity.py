"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ..custom_base_model import CustomBaseModel


class TargetedMessageInfoEntity(CustomBaseModel):
    """References the targeted inbound message for Teams prompt preview."""

    type: Literal["targetedMessageInfo"] = "targetedMessageInfo"
    message_id: str
