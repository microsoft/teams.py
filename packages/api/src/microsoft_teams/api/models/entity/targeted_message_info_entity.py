"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ..custom_base_model import CustomBaseModel


class TargetedMessageInfoEntity(CustomBaseModel):
    """Entity containing targeted message information for prompt preview."""

    type: Literal["targetedMessageInfo"] = "targetedMessageInfo"
    "Type identifier for targeted message info"

    message_id: str
    "The ID of the targeted message this activity is replying to"
