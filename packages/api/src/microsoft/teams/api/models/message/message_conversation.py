"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from ..custom_base_model import CustomBaseModel


class MessageConversation(CustomBaseModel):
    """
    Represents a team or channel entity.
    """

    conversation_identity_type: Optional[Literal["team", "channel"]] = None
    "The type of conversation, whether a team or channel."

    id: str
    "The id of the team or channel."

    display_name: Optional[str] = None
    "The plaintext display name of the team or channel entity."
