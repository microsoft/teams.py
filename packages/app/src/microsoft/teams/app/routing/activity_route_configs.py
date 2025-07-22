"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Callable, Dict, NamedTuple, Optional, Type

from microsoft.teams.api import (
    Activity,
    ActivityBase,
    AdaptiveCardInvokeActivity,
    CommandResultActivity,
    CommandSendActivity,
    ConfigFetchInvokeActivity,
    ConfigSubmitInvokeActivity,
    ConversationUpdateActivity,
    EndOfConversationActivity,
    EventActivity,
    ExecuteActionInvokeActivity,
    FileConsentInvokeActivity,
    HandoffActionInvokeActivity,
    HandoffActivity,
    InstallUpdateActivity,
    InvokeActivity,
    MeetingEndEventActivity,
    MeetingParticipantJoinEventActivity,
    MeetingParticipantLeaveEventActivity,
    MeetingStartEventActivity,
    MessageActivity,
    MessageDeleteActivity,
    MessageExtensionAnonQueryLinkInvokeActivity,
    MessageExtensionCardButtonClickedInvokeActivity,
    MessageExtensionFetchTaskInvokeActivity,
    MessageExtensionQueryInvokeActivity,
    MessageExtensionQueryLinkInvokeActivity,
    MessageExtensionQuerySettingUrlInvokeActivity,
    MessageExtensionSelectItemInvokeActivity,
    MessageExtensionSettingInvokeActivity,
    MessageExtensionSubmitActionInvokeActivity,
    MessageInvokeActivity,
    MessageReactionActivity,
    MessageUpdateActivity,
    SignInTokenExchangeInvokeActivity,
    SignInVerifyStateInvokeActivity,
    TabFetchInvokeActivity,
    TabSubmitInvokeActivity,
    TaskFetchInvokeActivity,
    TaskSubmitInvokeActivity,
    TraceActivity,
    TypingActivity,
)
from microsoft.teams.api.activities.event.read_reciept import ReadReceiptEventActivity
from microsoft.teams.api.models.invoke_response import (
    AdaptiveCardInvokeResponse,
    ConfigInvokeResponse,
    MessagingExtensionActionInvokeResponse,
    MessagingExtensionInvokeResponse,
    TabInvokeResponse,
    TaskModuleInvokeResponse,
    TokenExchangeInvokeResponseType,
    VoidInvokeResponse,
)

RouteSelector = Callable[[ActivityBase], bool]


class ActivityConfig(NamedTuple):
    """Configuration for an activity handler."""

    name: str
    """The activity type string (e.g., 'message', 'invoke')."""

    method_name: str
    """The generated method name (e.g., 'onMessage', 'onInvoke')."""

    input_model: Type[ActivityBase]
    """The input activity class type."""

    selector: RouteSelector
    """Function that determines if this route matches the given activity."""

    output_model: Optional[Type] = None
    """The output model class type. None if no specific output type."""

    input_type_name: Optional[str] = None
    """Override for the input type name in generated code. If None, uses input_model.__name__."""

    output_type_name: Optional[str] = None
    """Override for the output type name in generated code. If None, uses output_model.__name__."""


ACTIVITY_ROUTES: Dict[str, ActivityConfig] = {
    # Message Activities
    "message": ActivityConfig(
        name="message",
        method_name="onMessage",
        input_model=MessageActivity,
        selector=lambda activity: isinstance(activity, MessageActivity),
        output_model=None,
    ),
    "messageDelete": ActivityConfig(
        name="messageDelete",
        method_name="onMessageDelete",
        input_model=MessageDeleteActivity,
        selector=lambda activity: isinstance(activity, MessageDeleteActivity),
        output_model=None,
    ),
    "softDeleteMessage": ActivityConfig(
        name="softDeleteMessage",
        method_name="onSoftDeleteMessage",
        input_model=MessageDeleteActivity,
        selector=lambda activity: isinstance(activity, MessageDeleteActivity)
        and activity.channel_data.event_type == "softDeleteMessage",
        output_model=None,
    ),
    "messageReaction": ActivityConfig(
        name="messageReaction",
        method_name="onMessageReaction",
        input_model=MessageReactionActivity,
        selector=lambda activity: isinstance(activity, MessageReactionActivity),
        output_model=None,
    ),
    "messageUpdate": ActivityConfig(
        name="messageUpdate",
        method_name="onMessageUpdate",
        input_model=MessageUpdateActivity,
        selector=lambda activity: isinstance(activity, MessageUpdateActivity),
        output_model=None,
    ),
    "undeleteMessage": ActivityConfig(
        name="undeleteMessage",
        method_name="onUndeleteMessage",
        input_model=MessageUpdateActivity,
        selector=lambda activity: isinstance(activity, MessageUpdateActivity)
        and activity.channel_data.event_type == "undeleteMessage",
        output_model=None,
    ),
    "editMessage": ActivityConfig(
        name="editMessage",
        method_name="onEditMessage",
        input_model=MessageUpdateActivity,
        selector=lambda activity: isinstance(activity, MessageUpdateActivity)
        and activity.channel_data.event_type == "editMessage",
        output_model=None,
    ),
    # Command Activities
    "command": ActivityConfig(
        name="command",
        method_name="onCommand",
        input_model=CommandSendActivity,
        selector=lambda activity: isinstance(activity, CommandSendActivity),
        output_model=None,
    ),
    "commandResult": ActivityConfig(
        name="commandResult",
        method_name="onCommandResult",
        input_model=CommandResultActivity,
        selector=lambda activity: isinstance(activity, CommandResultActivity),
        output_model=None,
    ),
    # Conversation Activities
    "conversationUpdate": ActivityConfig(
        name="conversationUpdate",
        method_name="onConversationUpdate",
        input_model=ConversationUpdateActivity,
        selector=lambda activity: isinstance(activity, ConversationUpdateActivity),
        output_model=None,
    ),
    "channelCreated": ActivityConfig(
        name="channelCreated",
        method_name="onChannelCreated",
        input_model=ConversationUpdateActivity,
        selector=lambda activity: isinstance(activity, ConversationUpdateActivity)
        and activity.channel_data.event_type == "channelCreated",
        output_model=None,
    ),
    "channelDeleted": ActivityConfig(
        name="channelDeleted",
        method_name="onChannelDeleted",
        input_model=ConversationUpdateActivity,
        selector=lambda activity: isinstance(activity, ConversationUpdateActivity)
        and activity.channel_data.event_type == "channelDeleted",
        output_model=None,
    ),
    "channelRenamed": ActivityConfig(
        name="channelRenamed",
        method_name="onChannelRenamed",
        input_model=ConversationUpdateActivity,
        selector=lambda activity: isinstance(activity, ConversationUpdateActivity)
        and activity.channel_data.event_type == "channelRenamed",
        output_model=None,
    ),
    "channelRestored": ActivityConfig(
        name="channelRestored",
        method_name="onChannelRestored",
        input_model=ConversationUpdateActivity,
        selector=lambda activity: isinstance(activity, ConversationUpdateActivity)
        and activity.channel_data.event_type == "channelRestored",
        output_model=None,
    ),
    "teamArchived": ActivityConfig(
        name="teamArchived",
        method_name="onTeamArchived",
        input_model=ConversationUpdateActivity,
        selector=lambda activity: isinstance(activity, ConversationUpdateActivity)
        and activity.channel_data.event_type == "teamArchived",
        output_model=None,
    ),
    "teamDeleted": ActivityConfig(
        name="teamDeleted",
        method_name="onTeamDeleted",
        input_model=ConversationUpdateActivity,
        selector=lambda activity: isinstance(activity, ConversationUpdateActivity)
        and activity.channel_data.event_type == "teamDeleted",
        output_model=None,
    ),
    "teamHardDeleted": ActivityConfig(
        name="teamHardDeleted",
        method_name="onTeamHardDeleted",
        input_model=ConversationUpdateActivity,
        selector=lambda activity: isinstance(activity, ConversationUpdateActivity)
        and activity.channel_data.event_type == "teamHardDeleted",
        output_model=None,
    ),
    "teamRenamed": ActivityConfig(
        name="teamRenamed",
        method_name="onTeamRenamed",
        input_model=ConversationUpdateActivity,
        selector=lambda activity: isinstance(activity, ConversationUpdateActivity)
        and activity.channel_data.event_type == "teamRenamed",
        output_model=None,
    ),
    "teamRestored": ActivityConfig(
        name="teamRestored",
        method_name="onTeamRestored",
        input_model=ConversationUpdateActivity,
        selector=lambda activity: isinstance(activity, ConversationUpdateActivity)
        and activity.channel_data.event_type == "teamRestored",
        output_model=None,
    ),
    "teamUnarchived": ActivityConfig(
        name="teamUnarchived",
        method_name="onTeamUnarchived",
        input_model=ConversationUpdateActivity,
        selector=lambda activity: isinstance(activity, ConversationUpdateActivity)
        and activity.channel_data.event_type == "teamUnarchived",
        output_model=None,
    ),
    "endOfConversation": ActivityConfig(
        name="endOfConversation",
        method_name="onEndOfConversation",
        input_model=EndOfConversationActivity,
        selector=lambda activity: isinstance(activity, EndOfConversationActivity),
        output_model=None,
    ),
    # Complex Union Activities (discriminated by sub-fields)
    "event": ActivityConfig(
        name="event",
        method_name="onEvent",
        input_model=EventActivity,
        selector=lambda activity: activity.type == "event",
        output_model=None,
        input_type_name="EventActivity",
    ),
    "readReceipt": ActivityConfig(
        name="readReceipt",
        method_name="onReadReceipt",
        input_model=ReadReceiptEventActivity,
        selector=lambda activity: activity.type == "event" and activity.name == "application/vnd.microsoft.readReceipt",
        output_model=None,
    ),
    "meetingStart": ActivityConfig(
        name="meetingStart",
        method_name="onMeetingStart",
        input_model=MeetingStartEventActivity,
        selector=lambda activity: activity.type == "event"
        and activity.name == "application/vnd.microsoft.meetingStart",
        output_model=None,
    ),
    "meetingEnd": ActivityConfig(
        name="meetingEnd",
        method_name="onMeetingEnd",
        input_model=MeetingEndEventActivity,
        selector=lambda activity: activity.type == "event" and activity.name == "application/vnd.microsoft.meetingEnd",
        output_model=None,
    ),
    "meetingParticipantJoin": ActivityConfig(
        name="meetingParticipantJoin",
        method_name="onMeetingParticipantJoin",
        input_model=MeetingParticipantJoinEventActivity,
        selector=lambda activity: activity.type == "event"
        and activity.name == "application/vnd.microsoft.meetingParticipantJoin",
        output_model=None,
    ),
    "meetingParticipantLeave": ActivityConfig(
        name="meetingParticipantLeave",
        method_name="onMeetingParticipantLeave",
        input_model=MeetingParticipantLeaveEventActivity,
        selector=lambda activity: activity.type == "event"
        and activity.name == "application/vnd.microsoft.meetingParticipantLeave",
        output_model=None,
    ),
    # Invoke Activities with specific names and response types
    "config.open": ActivityConfig(
        name="config.open",
        method_name="onConfigOpen",
        input_model=ConfigFetchInvokeActivity,
        selector=lambda activity: isinstance(activity, ConfigFetchInvokeActivity),
        output_model=ConfigInvokeResponse,
        output_type_name="ConfigInvokeResponse",
    ),
    "config.submit": ActivityConfig(
        name="config.submit",
        method_name="onConfigSubmit",
        input_model=ConfigSubmitInvokeActivity,
        selector=lambda activity: isinstance(activity, ConfigSubmitInvokeActivity),
        output_model=ConfigInvokeResponse,
        output_type_name="ConfigInvokeResponse",
    ),
    "file.consent": ActivityConfig(
        name="file.consent",
        method_name="onFileConsent",
        input_model=FileConsentInvokeActivity,
        selector=lambda activity: activity.type == "invoke" and activity.name == "fileConsent/invoke",
        output_model=VoidInvokeResponse,
        output_type_name="VoidInvokeResponse",
    ),
    "message.execute": ActivityConfig(
        name="message.execute",
        method_name="onMessageExecute",
        input_model=ExecuteActionInvokeActivity,
        selector=lambda activity: activity.type == "invoke" and activity.name == "actionableMessage/executeAction",
        output_model=VoidInvokeResponse,
        output_type_name="VoidInvokeResponse",
    ),
    "message.ext.query-link": ActivityConfig(
        name="message.ext.query-link",
        method_name="onMessageExtQueryLink",
        input_model=MessageExtensionQueryLinkInvokeActivity,
        selector=lambda activity: activity.type == "invoke" and activity.name == "composeExtension/queryLink",
        output_model=MessagingExtensionInvokeResponse,
        output_type_name="MessagingExtensionInvokeResponse",
    ),
    "message.ext.anon-query-link": ActivityConfig(
        name="message.ext.anon-query-link",
        method_name="onMessageExtAnonQueryLink",
        input_model=MessageExtensionAnonQueryLinkInvokeActivity,
        selector=lambda activity: activity.type == "invoke" and activity.name == "composeExtension/anonymousQueryLink",
        output_model=MessagingExtensionInvokeResponse,
        output_type_name="MessagingExtensionInvokeResponse",
    ),
    "message.ext.query": ActivityConfig(
        name="message.ext.query",
        method_name="onMessageExtQuery",
        input_model=MessageExtensionQueryInvokeActivity,
        selector=lambda activity: isinstance(activity, MessageExtensionQueryInvokeActivity)
        and activity.name == "composeExtension/query",
        output_model=MessagingExtensionInvokeResponse,
        output_type_name="MessagingExtensionInvokeResponse",
    ),
    "message.ext.select-item": ActivityConfig(
        name="message.ext.select-item",
        method_name="onMessageExtSelectItem",
        input_model=MessageExtensionSelectItemInvokeActivity,
        selector=lambda activity: isinstance(activity, MessageExtensionSelectItemInvokeActivity)
        and activity.name == "composeExtension/selectItem",
        output_model=MessagingExtensionInvokeResponse,
        output_type_name="MessagingExtensionInvokeResponse",
    ),
    "message.ext.submit": ActivityConfig(
        name="message.ext.submit",
        method_name="onMessageExtSubmit",
        input_model=MessageExtensionSubmitActionInvokeActivity,
        selector=lambda activity: isinstance(activity, MessageExtensionSubmitActionInvokeActivity)
        and activity.name == "composeExtension/submitAction",
        output_model=MessagingExtensionActionInvokeResponse,
        output_type_name="MessagingExtensionActionInvokeResponse",
    ),
    "message.ext.open": ActivityConfig(
        name="message.ext.open",
        method_name="onMessageExtOpen",
        input_model=MessageExtensionFetchTaskInvokeActivity,
        selector=lambda activity: isinstance(activity, MessageExtensionFetchTaskInvokeActivity)
        and activity.name == "composeExtension/fetchTask",
        output_model=MessagingExtensionActionInvokeResponse,
        output_type_name="MessagingExtensionActionInvokeResponse",
    ),
    "message.ext.query-settings-url": ActivityConfig(
        name="message.ext.query-settings-url",
        method_name="onMessageExtQuerySettingsUrl",
        input_model=MessageExtensionQuerySettingUrlInvokeActivity,
        selector=lambda activity: isinstance(activity, MessageExtensionQuerySettingUrlInvokeActivity)
        and activity.name == "composeExtension/querySettingUrl",
        output_model=MessagingExtensionInvokeResponse,
        output_type_name="MessagingExtensionInvokeResponse",
    ),
    "message.ext.setting": ActivityConfig(
        name="message.ext.setting",
        method_name="onMessageExtSetting",
        input_model=MessageExtensionSettingInvokeActivity,
        selector=lambda activity: isinstance(activity, MessageExtensionSettingInvokeActivity)
        and activity.name == "composeExtension/setting",
        output_model=MessagingExtensionInvokeResponse,
        output_type_name="MessagingExtensionInvokeResponse",
    ),
    "message.ext.card-button-clicked": ActivityConfig(
        name="message.ext.card-button-clicked",
        method_name="onMessageExtCardButtonClicked",
        input_model=MessageExtensionCardButtonClickedInvokeActivity,
        selector=lambda activity: isinstance(activity, MessageExtensionCardButtonClickedInvokeActivity),
        output_model=VoidInvokeResponse,
        output_type_name="VoidInvokeResponse",
    ),
    "dialog.open": ActivityConfig(
        name="dialog.open",
        method_name="onDialogOpen",
        input_model=TaskFetchInvokeActivity,
        selector=lambda activity: activity.type == "invoke" and activity.name == "task/fetch",
        output_model=TaskModuleInvokeResponse,
        output_type_name="TaskModuleInvokeResponse",
    ),
    "dialog.submit": ActivityConfig(
        name="dialog.submit",
        method_name="onDialogSubmit",
        input_model=TaskSubmitInvokeActivity,
        selector=lambda activity: activity.type == "invoke" and activity.name == "task/submit",
        output_model=TaskModuleInvokeResponse,
        output_type_name="TaskModuleInvokeResponse",
    ),
    "tab.open": ActivityConfig(
        name="tab.open",
        method_name="onTabOpen",
        input_model=TabFetchInvokeActivity,
        selector=lambda activity: activity.type == "invoke" and activity.name == "tab/fetch",
        output_model=TabInvokeResponse,
        output_type_name="TabInvokeResponse",
    ),
    "tab.submit": ActivityConfig(
        name="tab.submit",
        method_name="onTabSubmit",
        input_model=TabSubmitInvokeActivity,
        selector=lambda activity: activity.type == "invoke" and activity.name == "tab/submit",
        output_model=TabInvokeResponse,
        output_type_name="TabInvokeResponse",
    ),
    "message.submit": ActivityConfig(
        name="message.submit",
        method_name="onMessageSubmit",
        input_model=MessageInvokeActivity,
        selector=lambda activity: activity.type == "invoke" and activity.name == "message/submitAction",
        output_model=VoidInvokeResponse,
        output_type_name="VoidInvokeResponse",
        input_type_name="MessageInvokeActivity",
    ),
    "handoff.action": ActivityConfig(
        name="handoff.action",
        method_name="onHandoffAction",
        input_model=HandoffActionInvokeActivity,
        selector=lambda activity: activity.type == "invoke" and activity.name == "handoff/action",
        output_model=VoidInvokeResponse,
        output_type_name="VoidInvokeResponse",
    ),
    "signin.token-exchange": ActivityConfig(
        name="signin.token-exchange",
        method_name="onSigninTokenExchange",
        input_model=SignInTokenExchangeInvokeActivity,
        selector=lambda activity: activity.type == "invoke" and activity.name == "signin/tokenExchange",
        output_model=TokenExchangeInvokeResponseType,
        output_type_name="TokenExchangeInvokeResponseType",
    ),
    "signin.verify-state": ActivityConfig(
        name="signin.verify-state",
        method_name="onSigninVerifyState",
        input_model=SignInVerifyStateInvokeActivity,
        selector=lambda activity: activity.type == "invoke" and activity.name == "signin/verifyState",
        output_model=VoidInvokeResponse,
        output_type_name="VoidInvokeResponse",
    ),
    "card.action": ActivityConfig(
        name="card.action",
        method_name="onCardAction",
        input_model=AdaptiveCardInvokeActivity,
        selector=lambda activity: activity.type == "invoke" and activity.name == "adaptiveCard/action",
        output_model=AdaptiveCardInvokeResponse,
        output_type_name="AdaptiveCardInvokeResponse",
        input_type_name="AdaptiveCardInvokeActivity",
    ),
    # Generic invoke handler (fallback for any invoke not matching specific aliases)
    "invoke": ActivityConfig(
        name="invoke",
        method_name="onInvoke",
        input_model=InvokeActivity,
        selector=lambda activity: activity.type == "invoke",
        output_model=None,
        input_type_name="InvokeActivity",
    ),
    "installationUpdate": ActivityConfig(
        name="installationUpdate",
        method_name="onInstallationUpdate",
        input_model=InstallUpdateActivity,
        selector=lambda activity: activity.type == "installationUpdate",
        output_model=None,
        input_type_name="InstallUpdateActivity",
    ),
    # Other Core Activities
    "typing": ActivityConfig(
        name="typing",
        method_name="onTyping",
        input_model=TypingActivity,
        selector=lambda activity: isinstance(activity, TypingActivity),
        output_model=None,
    ),
    "trace": ActivityConfig(
        name="trace",
        method_name="onTrace",
        input_model=TraceActivity,
        selector=lambda activity: isinstance(activity, TraceActivity),
        output_model=None,
    ),
    "handoff": ActivityConfig(
        name="handoff",
        method_name="onHandoff",
        input_model=HandoffActivity,
        selector=lambda activity: isinstance(activity, HandoffActivity),
        output_model=None,
    ),
    # Generic Activity Handler (catch-all)
    "activity": ActivityConfig(
        name="activity",
        method_name="onActivity",
        input_model=Activity,
        selector=lambda activity: True,
        output_model=None,
        input_type_name="Activity",
    ),
}
