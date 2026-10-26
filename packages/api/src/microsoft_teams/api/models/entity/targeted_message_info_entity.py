"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from .entity_base import EntityBase


class TargetedMessageInfoEntity(EntityBase):
    """Entity containing targeted message information for prompt preview."""

    type: Literal["targetedMessageInfo"] = "targetedMessageInfo"
    "Type identifier for targeted message info"

    message_id: str
    "The ID of the targeted message this activity is replying to"
