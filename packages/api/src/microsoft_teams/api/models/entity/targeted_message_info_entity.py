"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from microsoft_teams.common.experimental import experimental

from .entity_base import EntityBase


@experimental("ExperimentalTeamsTargeted")
class TargetedMessageInfoEntity(EntityBase):
    """Entity containing targeted message information for prompt preview.

    .. warning:: Preview
        This class is in preview and may change in the future.
        Diagnostic: ExperimentalTeamsTargeted
    """

    type: Literal["targetedMessageInfo"] = "targetedMessageInfo"
    "Type identifier for targeted message info"

    message_id: str
    "The ID of the targeted message this activity is replying to"
