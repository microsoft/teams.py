"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from typing import Any

import pytest
from microsoft_teams.api.activities.conversation.conversation_update import ConversationEventType
from microsoft_teams.api.activities.message import MessageActivityInput
from microsoft_teams.api.activities.message.message_update import MessageEventType
from microsoft_teams.api.models.account import AccountRole, AccountType
from microsoft_teams.api.models.action import Action
from microsoft_teams.api.models.adaptive_card.adaptive_card_invoke_action import AdaptiveCardInvokeActionType
from microsoft_teams.api.models.adaptive_card.adaptive_card_invoke_value import AdaptiveCardInvokeTrigger
from microsoft_teams.api.models.card.card_action import CardAction
from microsoft_teams.api.models.card.card_action_type import CardActionType
from microsoft_teams.api.models.channel_data.channel_info import ChannelType
from microsoft_teams.api.models.channel_data.feedback_loop import FeedbackLoopType
from microsoft_teams.api.models.channel_id import ChannelID
from microsoft_teams.api.models.conversation_type import ConversationType
from microsoft_teams.api.models.delivery_mode import DeliveryMode
from microsoft_teams.api.models.entity.ai_message_entity import AIMessageAdditionalType
from microsoft_teams.api.models.entity.citation_entity import CitationAppearance, CitationIconName
from microsoft_teams.api.models.entity.stream_info_entity import StreamInfoEntity
from microsoft_teams.api.models.file.file_consent_card import FileConsentCardResponse
from microsoft_teams.api.models.importance import Importance
from microsoft_teams.api.models.input_hint import InputHint
from microsoft_teams.api.models.message.application_identity_type import ApplicationIdentityType
from microsoft_teams.api.models.message.message import Message
from microsoft_teams.api.models.message.message_app import MessageApp
from microsoft_teams.api.models.message.message_body import MessageBodyContentType
from microsoft_teams.api.models.message.message_conversation import ConversationIdentityType
from microsoft_teams.api.models.message.message_reaction_type import MessageReactionType
from microsoft_teams.api.models.message.message_user import MessageUser
from microsoft_teams.api.models.message.user_identity_type import UserIdentityType
from microsoft_teams.api.models.messaging_extension.messaging_extension_action import (
    BotMessagePreviewAction,
    MessagingExtensionCommandContext,
)
from microsoft_teams.api.models.messaging_extension.messaging_extension_attachment_layout import (
    MessagingExtensionAttachmentLayout,
)
from microsoft_teams.api.models.messaging_extension.messaging_extension_result import MessagingExtensionResult
from microsoft_teams.api.models.messaging_extension.messaging_extension_result_type import MessagingExtensionResultType
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


@pytest.mark.unit
@pytest.mark.parametrize(
    ("model", "payload", "field"),
    [
        (CardAction, {"type": "futureAction", "title": "Future", "value": {}}, "type"),
        (FileConsentCardResponse, {"action": "futureAction"}, "action"),
        (Message, {"id": "message-id", "importance": "futureImportance"}, "importance"),
        (MessageUser, {"id": "user-id", "userIdentityType": "futureIdentity"}, "user_identity_type"),
        (MessageApp, {"id": "app-id", "applicationIdentityType": "futureIdentity"}, "application_identity_type"),
        (
            MessagingExtensionResult,
            {"attachmentLayout": "futureLayout", "type": "futureResult"},
            "attachment_layout",
        ),
        (
            CitationAppearance,
            {"name": "Document", "abstract": "Summary", "icon": "Future Icon"},
            "icon",
        ),
    ],
)
def test_enum_backed_wire_value_accepts_and_round_trips_unknown_string(
    model: Any, payload: dict[str, Any], field: str
) -> None:
    value = model.model_validate(payload)

    assert getattr(value, field).startswith("future") or getattr(value, field) == "Future Icon"
    assert value.model_dump(by_alias=True, exclude_none=True)[
        model.model_fields[field].serialization_alias or field
    ] == (getattr(value, field))


@pytest.mark.unit
@pytest.mark.parametrize(
    ("model", "payload", "field", "expected"),
    [
        (
            CardAction,
            {"type": "openUrl", "title": "Open", "value": "https://example.com"},
            "type",
            CardActionType.OPEN_URL,
        ),
        (FileConsentCardResponse, {"action": "accept"}, "action", Action.ACCEPT),
        (Message, {"id": "message-id", "importance": "high"}, "importance", Importance.HIGH),
        (
            MessageUser,
            {"id": "user-id", "userIdentityType": "aadUser"},
            "user_identity_type",
            UserIdentityType.AAD_USER,
        ),
        (
            MessageApp,
            {"id": "app-id", "applicationIdentityType": "aadApplication"},
            "application_identity_type",
            ApplicationIdentityType.AAD_APPLICATION,
        ),
        (
            MessagingExtensionResult,
            {"attachmentLayout": "grid", "type": "result"},
            "attachment_layout",
            MessagingExtensionAttachmentLayout.GRID,
        ),
        (
            CitationAppearance,
            {"name": "Document", "abstract": "Summary", "icon": "PDF"},
            "icon",
            CitationIconName.PDF,
        ),
    ],
)
def test_enum_backed_wire_value_preserves_known_enum(
    model: Any, payload: dict[str, Any], field: str, expected: Any
) -> None:
    assert getattr(model.model_validate(payload), field) is expected


@pytest.mark.unit
def test_messaging_extension_result_type_accepts_unknown_and_preserves_known_value() -> None:
    unknown = MessagingExtensionResult.model_validate({"type": "futureResult"})
    known = MessagingExtensionResult.model_validate({"type": "result"})

    assert unknown.type == "futureResult"
    assert unknown.model_dump(by_alias=True, exclude_none=True)["type"] == "futureResult"
    assert known.type is MessagingExtensionResultType.RESULT


@pytest.mark.unit
def test_attachment_layout_builder_accepts_future_string() -> None:
    activity = MessageActivityInput().with_attachment_layout("futureLayout")

    assert activity.attachment_layout == "futureLayout"
    assert activity.model_dump(by_alias=True, exclude_none=True)["attachmentLayout"] == "futureLayout"
