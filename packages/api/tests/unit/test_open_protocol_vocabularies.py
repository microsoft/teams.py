"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from typing import Any

import pytest
from microsoft_teams.api.activities.conversation.conversation_update import ConversationEventType
from microsoft_teams.api.activities.message.message_update import MessageEventType
from microsoft_teams.api.models.account import AccountRole, AccountType
from microsoft_teams.api.models.adaptive_card.adaptive_card_invoke_action import AdaptiveCardInvokeActionType
from microsoft_teams.api.models.adaptive_card.adaptive_card_invoke_value import AdaptiveCardInvokeTrigger
from microsoft_teams.api.models.channel_data.channel_info import ChannelType
from microsoft_teams.api.models.channel_data.feedback_loop import FeedbackLoopType
from microsoft_teams.api.models.channel_id import ChannelID
from microsoft_teams.api.models.conversation_type import ConversationType
from microsoft_teams.api.models.delivery_mode import DeliveryMode
from microsoft_teams.api.models.entity.ai_message_entity import AIMessageAdditionalType
from microsoft_teams.api.models.entity.stream_info_entity import StreamInfoEntity
from microsoft_teams.api.models.input_hint import InputHint
from microsoft_teams.api.models.message.message_body import MessageBodyContentType
from microsoft_teams.api.models.message.message_conversation import ConversationIdentityType
from microsoft_teams.api.models.message.message_reaction_type import MessageReactionType
from microsoft_teams.api.models.messaging_extension.messaging_extension_action import (
    BotMessagePreviewAction,
    MessagingExtensionCommandContext,
)
from microsoft_teams.api.models.reaction_feedback import ReactionFeedback
from microsoft_teams.api.models.search.search_value import SearchInvokeType
from microsoft_teams.api.models.stream_type import StreamType
from microsoft_teams.api.models.tab.tab_response import TabResponseType
from microsoft_teams.api.models.task_module.task_module_task_info import TaskModuleDimension
from microsoft_teams.api.models.team_type import TeamType
from microsoft_teams.api.models.text_format import TextFormat
from pydantic import TypeAdapter, ValidationError


@pytest.mark.unit
@pytest.mark.parametrize(
    "vocabulary",
    [
        AccountRole,
        AccountType,
        AdaptiveCardInvokeActionType,
        AdaptiveCardInvokeTrigger,
        AIMessageAdditionalType,
        BotMessagePreviewAction,
        ChannelID,
        ChannelType,
        ConversationEventType,
        ConversationIdentityType,
        ConversationType,
        DeliveryMode,
        FeedbackLoopType,
        ReactionFeedback,
        InputHint,
        MessageBodyContentType,
        MessageEventType,
        MessageReactionType,
        MessagingExtensionCommandContext,
        SearchInvokeType,
        StreamType,
        TabResponseType,
        TaskModuleDimension,
        TeamType,
        TextFormat,
    ],
)
def test_protocol_vocabulary_accepts_and_round_trips_unknown_string(vocabulary: Any) -> None:
    adapter = TypeAdapter(vocabulary)

    value = adapter.validate_python("futureValue")

    assert value == "futureValue"
    assert adapter.dump_python(value) == "futureValue"


@pytest.mark.unit
def test_concrete_discriminator_remains_exact() -> None:
    with pytest.raises(ValidationError):
        StreamInfoEntity.model_validate({"type": "futureEntity", "streamType": "futureValue"})
