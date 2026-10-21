"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from pydantic import ConfigDict

from ..custom_base_model import CustomBaseModel


class EncryptedChatInfo(CustomBaseModel):
    """
    The encrypted form of the id of a chat scope.

    This API is in preview and may change in the future.
    Diagnostic: ExperimentalTeamsThreading
    """

    model_config = ConfigDict(frozen=True)

    id: Optional[str] = None
    "The encrypted id of the chat scope."


class ChatInfo(CustomBaseModel):
    """
    Identifies the chat scope that contains an inbound activity.

    This API is in preview and may change in the future.
    Diagnostic: ExperimentalTeamsThreading
    """

    model_config = ConfigDict(frozen=True)

    id: Optional[str] = None
    """
    The id of the chat scope, without any reply chain (thread).
    This is the unencrypted id, and it can differ from `conversation.id`.
    It is not sent for channels, where `channel_data.channel.id` plays this role.
    Use it as the conversation id to send a top-level message to the chat scope, or to reply in a reply chain.
    """

    encrypted: Optional[EncryptedChatInfo] = None
    "The encrypted form of the chat scope's id."
