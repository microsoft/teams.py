"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from pydantic import Field, model_validator

from ..custom_base_model import CustomBaseModel
from .message_reaction_type import MessageReactionType
from .message_user import MessageUser


class MessageReaction(CustomBaseModel):
    """
    Represents a reaction to a message.
    """

    type: MessageReactionType = Field(alias="reactionType")
    "The type of reaction given to the message."

    created_date_time: Optional[str] = None
    "Timestamp of when the user reacted to the message."

    user: Optional[MessageUser] = None
    "The user with which the reaction is associated."

    @model_validator(mode="before")
    @classmethod
    def unwrap_user(cls, data: object) -> object:
        """
        Teams API sometimes wraps the user object in an extra 'user' key
        (i.e. user.user.<fields>) in messaging extension payloads.
        Unwrap it so MessageUser sees the correct structure.
        """
        if isinstance(data, dict):
            user = data.get("user")
            if isinstance(user, dict) and "user" in user and "id" in user.get("user", {}):
                data = dict(data)
                data["user"] = user["user"]
        return data
