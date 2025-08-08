"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass
from typing import Callable, Dict, Optional, Type, cast

from microsoft.teams.api import (
    ActivityBase,
    CommandResultActivity,
    CommandSendActivity,
    ConfigFetchInvokeActivity,
    ConfigInvokeResponse,
    ConfigSubmitInvokeActivity,
    ConversationUpdateActivity,
    CustomBaseModel,
    EndOfConversationActivity,
    EventActivity,
    ExecuteActionInvokeActivity,
    FileConsentInvokeActivity,
    HandoffActionInvokeActivity,
    HandoffActivity,
    InstalledActivity,
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
    MessageReactionActivity,
    MessageSubmitActionInvokeActivity,
    MessageUpdateActivity,
    MessagingExtensionActionInvokeResponse,
    MessagingExtensionInvokeResponse,
    ReadReceiptEventActivity,
    SignInTokenExchangeInvokeActivity,
    SignInVerifyStateInvokeActivity,
    TabFetchInvokeActivity,
    TabInvokeResponse,
    TabSubmitInvokeActivity,
    TaskFetchInvokeActivity,
    TaskModuleInvokeResponse,
    TaskSubmitInvokeActivity,
    TraceActivity,
    TypingActivity,
    UninstalledActivity,
)

RouteSelector = Callable[[ActivityBase], bool]


@dataclass(frozen=True)
class ActivityConfig:
    """Configuration for an activity handler."""

    name: str
    """The activity type string (e.g., 'message', 'invoke')."""

    method_name: str
    """The generated method name (e.g., 'onMessage', 'onInvoke')."""

    input_model: str | Type[ActivityBase]
    """The input activity class type."""

    selector: RouteSelector
    """Function that determines if this route matches the given activity."""

    output_model: Optional[Type[CustomBaseModel]] = None
    """The output model class type. None if no specific output type."""

    output_type_name: Optional[str] = None
    """Override for the output type name in generated code. If None, uses output_model.__name__."""

    is_invoke: bool = False
    """Whether this config is for an invoke activity. Defaults to False."""


ACTIVITY_ROUTES: Dict[str, ActivityConfig] = {
    # Message Activities
    "message": ActivityConfig(
        name="message",
        method_name="on_message",
        input_model=MessageActivity,
        selector=lambda activity: isinstance(activity, MessageActivity),
        output_model=None,
    ),
    "message_delete": ActivityConfig(
        name="message_delete",
        method_name="on_message_delete",
        input_model=MessageDeleteActivity,
        selector=lambda activity: isinstance(activity, MessageDeleteActivity),
        output_model=None,
    ),
    "soft_delete_message": ActivityConfig(
        name="soft_delete_message",
        method_name="on_soft_delete_message",
        input_model=MessageDeleteActivity,
        selector=lambda activity: isinstance(activity, MessageDeleteActivity)
        and activity.channel_data.event_type == "softDeleteMessage",
        output_model=None,
    ),
    "message_reaction": ActivityConfig(
        name="message_reaction",
        method_name="on_message_reaction",
        input_model=MessageReactionActivity,
        selector=lambda activity: isinstance(activity, MessageReactionActivity),
        output_model=None,
    ),
    "message_update": ActivityConfig(
        name="message_update",
        method_name="on_message_update",
        input_model=MessageUpdateActivity,
        selector=lambda activity: isinstance(activity, MessageUpdateActivity),
        output_model=None,
    ),
    "undelete_message": ActivityConfig(
        name="undelete_message",
        method_name="on_undelete_message",
        input_model=MessageUpdateActivity,
        selector=lambda activity: isinstance(activity, MessageUpdateActivity)
        and activity.channel_data.event_type == "undeleteMessage",
        output_model=None,
    ),
    "edit_message": ActivityConfig(
        name="edit_message",
        method_name="on_edit_message",
        input_model=MessageUpdateActivity,
        selector=lambda activity: isinstance(activity, MessageUpdateActivity)
        and activity.channel_data.event_type == "editMessage",
        output_model=None,
    ),
    # Command Activities
    "command": ActivityConfig(
        name="command",
        method_name="on_command",
        input_model=CommandSendActivity,
        selector=lambda activity: isinstance(activity, CommandSendActivity),
        output_model=None,
    ),
    "command_result": ActivityConfig(
        name="command_result",
        method_name="on_command_result",
        input_model=CommandResultActivity,
        selector=lambda activity: isinstance(activity, CommandResultActivity),
        output_model=None,
    ),
    # Conversation Activities
    "conversation_update": ActivityConfig(
        name="conversation_update",
        method_name="on_conversation_update",
        input_model=ConversationUpdateActivity,
        selector=lambda activity: isinstance(activity, ConversationUpdateActivity),
        output_model=None,
    ),
    "channel_created": ActivityConfig(
        name="channel_created",
        method_name="on_channel_created",
        input_model=ConversationUpdateActivity,
        selector=lambda activity: isinstance(activity, ConversationUpdateActivity)
        and activity.channel_data.event_type == "channelCreated",
        output_model=None,
    ),
    "channel_deleted": ActivityConfig(
        name="channel_deleted",
        method_name="on_channel_deleted",
        input_model=ConversationUpdateActivity,
        selector=lambda activity: isinstance(activity, ConversationUpdateActivity)
        and activity.channel_data.event_type == "channelDeleted",
        output_model=None,
    ),
    "channel_renamed": ActivityConfig(
        name="channel_renamed",
        method_name="on_channel_renamed",
        input_model=ConversationUpdateActivity,
        selector=lambda activity: isinstance(activity, ConversationUpdateActivity)
        and activity.channel_data.event_type == "channelRenamed",
        output_model=None,
    ),
    "channel_restored": ActivityConfig(
        name="channel_restored",
        method_name="on_channel_restored",
        input_model=ConversationUpdateActivity,
        selector=lambda activity: isinstance(activity, ConversationUpdateActivity)
        and activity.channel_data.event_type == "channelRestored",
        output_model=None,
    ),
    "team_archived": ActivityConfig(
        name="team_archived",
        method_name="on_team_archived",
        input_model=ConversationUpdateActivity,
        selector=lambda activity: isinstance(activity, ConversationUpdateActivity)
        and activity.channel_data.event_type == "teamArchived",
        output_model=None,
    ),
    "team_deleted": ActivityConfig(
        name="team_deleted",
        method_name="on_team_deleted",
        input_model=ConversationUpdateActivity,
        selector=lambda activity: isinstance(activity, ConversationUpdateActivity)
        and activity.channel_data.event_type == "teamDeleted",
        output_model=None,
    ),
    "team_hard_deleted": ActivityConfig(
        name="team_hard_deleted",
        method_name="on_team_hard_deleted",
        input_model=ConversationUpdateActivity,
        selector=lambda activity: isinstance(activity, ConversationUpdateActivity)
        and activity.channel_data.event_type == "teamHardDeleted",
        output_model=None,
    ),
    "team_renamed": ActivityConfig(
        name="team_renamed",
        method_name="on_team_renamed",
        input_model=ConversationUpdateActivity,
        selector=lambda activity: isinstance(activity, ConversationUpdateActivity)
        and activity.channel_data.event_type == "teamRenamed",
        output_model=None,
    ),
    "team_restored": ActivityConfig(
        name="team_restored",
        method_name="on_team_restored",
        input_model=ConversationUpdateActivity,
        selector=lambda activity: isinstance(activity, ConversationUpdateActivity)
        and activity.channel_data.event_type == "teamRestored",
        output_model=None,
    ),
    "team_unarchived": ActivityConfig(
        name="team_unarchived",
        method_name="on_team_unarchived",
        input_model=ConversationUpdateActivity,
        selector=lambda activity: isinstance(activity, ConversationUpdateActivity)
        and activity.channel_data.event_type == "teamUnarchived",
        output_model=None,
    ),
    "end_of_conversation": ActivityConfig(
        name="end_of_conversation",
        method_name="on_end_of_conversation",
        input_model=EndOfConversationActivity,
        selector=lambda activity: isinstance(activity, EndOfConversationActivity),
        output_model=None,
    ),
    # Complex Union Activities (discriminated by sub-fields)
    "event": ActivityConfig(
        name="event",
        method_name="on_event",
        input_model="EventActivity",
        selector=lambda activity: activity.type == "event",
        output_model=None,
    ),
    "read_receipt": ActivityConfig(
        name="read_receipt",
        method_name="on_read_receipt",
        input_model=ReadReceiptEventActivity,
        selector=lambda activity: activity.type == "event"
        and cast(EventActivity, activity).name == "application/vnd.microsoft.readReceipt",
        output_model=None,
    ),
    "meeting_start": ActivityConfig(
        name="meeting_start",
        method_name="on_meeting_start",
        input_model=MeetingStartEventActivity,
        selector=lambda activity: activity.type == "event"
        and cast(EventActivity, activity).name == "application/vnd.microsoft.meetingStart",
        output_model=None,
    ),
    "meeting_end": ActivityConfig(
        name="meeting_end",
        method_name="on_meeting_end",
        input_model=MeetingEndEventActivity,
        selector=lambda activity: activity.type == "event"
        and cast(EventActivity, activity).name == "application/vnd.microsoft.meetingEnd",
        output_model=None,
    ),
    "meeting_participant_join": ActivityConfig(
        name="meeting_participant_join",
        method_name="on_meeting_participant_join",
        input_model=MeetingParticipantJoinEventActivity,
        selector=lambda activity: activity.type == "event"
        and cast(EventActivity, activity).name == "application/vnd.microsoft.meetingParticipantJoin",
        output_model=None,
    ),
    "meeting_participant_leave": ActivityConfig(
        name="meeting_participant_leave",
        method_name="on_meeting_participant_leave",
        input_model=MeetingParticipantLeaveEventActivity,
        selector=lambda activity: activity.type == "event"
        and cast(EventActivity, activity).name == "application/vnd.microsoft.meetingParticipantLeave",
        output_model=None,
    ),
    # Invoke Activities with specific names and response types
    "config.open": ActivityConfig(
        name="config.open",
        method_name="on_config_open",
        input_model=ConfigFetchInvokeActivity,
        selector=lambda activity: isinstance(activity, ConfigFetchInvokeActivity),
        output_model=ConfigInvokeResponse,
        output_type_name="ConfigInvokeResponse",
        is_invoke=True,
    ),
    "config.submit": ActivityConfig(
        name="config.submit",
        method_name="on_config_submit",
        input_model=ConfigSubmitInvokeActivity,
        selector=lambda activity: isinstance(activity, ConfigSubmitInvokeActivity),
        output_model=ConfigInvokeResponse,
        output_type_name="ConfigInvokeResponse",
        is_invoke=True,
    ),
    "file.consent": ActivityConfig(
        name="file.consent",
        method_name="on_file_consent",
        input_model=FileConsentInvokeActivity,
        selector=lambda activity: activity.type == "invoke"
        and cast(InvokeActivity, activity).name == "fileConsent/invoke",
        output_model=None,
        is_invoke=True,
    ),
    "message.execute": ActivityConfig(
        name="message.execute",
        method_name="on_message_execute",
        input_model=ExecuteActionInvokeActivity,
        selector=lambda activity: activity.type == "invoke"
        and cast(InvokeActivity, activity).name == "actionableMessage/executeAction",
        output_model=None,
        is_invoke=True,
    ),
    "message.ext.query-link": ActivityConfig(
        name="message.ext.query-link",
        method_name="on_message_ext_query_link",
        input_model=MessageExtensionQueryLinkInvokeActivity,
        selector=lambda activity: activity.type == "invoke"
        and cast(InvokeActivity, activity).name == "composeExtension/queryLink",
        output_model=MessagingExtensionInvokeResponse,
        output_type_name="MessagingExtensionInvokeResponse",
        is_invoke=True,
    ),
    "message.ext.anon-query-link": ActivityConfig(
        name="message.ext.anon-query-link",
        method_name="on_message_ext_anon_query_link",
        input_model=MessageExtensionAnonQueryLinkInvokeActivity,
        selector=lambda activity: activity.type == "invoke"
        and cast(InvokeActivity, activity).name == "composeExtension/anonymousQueryLink",
        output_model=MessagingExtensionInvokeResponse,
        output_type_name="MessagingExtensionInvokeResponse",
        is_invoke=True,
    ),
    "message.ext.query": ActivityConfig(
        name="message.ext.query",
        method_name="on_message_ext_query",
        input_model=MessageExtensionQueryInvokeActivity,
        selector=lambda activity: isinstance(activity, MessageExtensionQueryInvokeActivity)
        and activity.name == "composeExtension/query",
        output_model=MessagingExtensionInvokeResponse,
        output_type_name="MessagingExtensionInvokeResponse",
        is_invoke=True,
    ),
    "message.ext.select-item": ActivityConfig(
        name="message.ext.select-item",
        method_name="on_message_ext_select_item",
        input_model=MessageExtensionSelectItemInvokeActivity,
        selector=lambda activity: isinstance(activity, MessageExtensionSelectItemInvokeActivity)
        and activity.name == "composeExtension/selectItem",
        output_model=MessagingExtensionInvokeResponse,
        output_type_name="MessagingExtensionInvokeResponse",
        is_invoke=True,
    ),
    "message.ext.submit": ActivityConfig(
        name="message.ext.submit",
        method_name="on_message_ext_submit",
        input_model=MessageExtensionSubmitActionInvokeActivity,
        selector=lambda activity: isinstance(activity, MessageExtensionSubmitActionInvokeActivity)
        and activity.name == "composeExtension/submitAction",
        output_model=MessagingExtensionActionInvokeResponse,
        output_type_name="MessagingExtensionActionInvokeResponse",
        is_invoke=True,
    ),
    "message.ext.open": ActivityConfig(
        name="message.ext.open",
        method_name="on_message_ext_open",
        input_model=MessageExtensionFetchTaskInvokeActivity,
        selector=lambda activity: isinstance(activity, MessageExtensionFetchTaskInvokeActivity)
        and activity.name == "composeExtension/fetchTask",
        output_model=MessagingExtensionActionInvokeResponse,
        output_type_name="MessagingExtensionActionInvokeResponse",
        is_invoke=True,
    ),
    "message.ext.query-settings-url": ActivityConfig(
        name="message.ext.query-settings-url",
        method_name="on_message_ext_query_settings_url",
        input_model=MessageExtensionQuerySettingUrlInvokeActivity,
        selector=lambda activity: isinstance(activity, MessageExtensionQuerySettingUrlInvokeActivity)
        and activity.name == "composeExtension/querySettingUrl",
        output_model=MessagingExtensionInvokeResponse,
        output_type_name="MessagingExtensionInvokeResponse",
        is_invoke=True,
    ),
    "message.ext.setting": ActivityConfig(
        name="message.ext.setting",
        method_name="on_message_ext_setting",
        input_model=MessageExtensionSettingInvokeActivity,
        selector=lambda activity: isinstance(activity, MessageExtensionSettingInvokeActivity)
        and activity.name == "composeExtension/setting",
        output_model=MessagingExtensionInvokeResponse,
        output_type_name="MessagingExtensionInvokeResponse",
        is_invoke=True,
    ),
    "message.ext.card-button-clicked": ActivityConfig(
        name="message.ext.card-button-clicked",
        method_name="on_message_ext_card_button_clicked",
        input_model=MessageExtensionCardButtonClickedInvokeActivity,
        selector=lambda activity: isinstance(activity, MessageExtensionCardButtonClickedInvokeActivity),
        output_model=None,
        is_invoke=True,
    ),
    "dialog.open": ActivityConfig(
        name="dialog.open",
        method_name="on_dialog_open",
        input_model=TaskFetchInvokeActivity,
        selector=lambda activity: activity.type == "invoke" and cast(InvokeActivity, activity).name == "task/fetch",
        output_model=TaskModuleInvokeResponse,
        output_type_name="TaskModuleInvokeResponse",
        is_invoke=True,
    ),
    "dialog.submit": ActivityConfig(
        name="dialog.submit",
        method_name="on_dialog_submit",
        input_model=TaskSubmitInvokeActivity,
        selector=lambda activity: activity.type == "invoke" and cast(InvokeActivity, activity).name == "task/submit",
        output_model=TaskModuleInvokeResponse,
        output_type_name="TaskModuleInvokeResponse",
        is_invoke=True,
    ),
    "tab.open": ActivityConfig(
        name="tab.open",
        method_name="on_tab_open",
        input_model=TabFetchInvokeActivity,
        selector=lambda activity: activity.type == "invoke" and cast(InvokeActivity, activity).name == "tab/fetch",
        output_model=TabInvokeResponse,
        output_type_name="TabInvokeResponse",
        is_invoke=True,
    ),
    "tab.submit": ActivityConfig(
        name="tab.submit",
        method_name="on_tab_submit",
        input_model=TabSubmitInvokeActivity,
        selector=lambda activity: activity.type == "invoke" and cast(InvokeActivity, activity).name == "tab/submit",
        output_model=TabInvokeResponse,
        output_type_name="TabInvokeResponse",
        is_invoke=True,
    ),
    "message.submit": ActivityConfig(
        name="message.submit",
        method_name="on_message_submit",
        input_model=MessageSubmitActionInvokeActivity,
        selector=lambda activity: activity.type == "invoke"
        and cast(InvokeActivity, activity).name == "message/submitAction",
        output_model=None,
        is_invoke=True,
    ),
    "handoff.action": ActivityConfig(
        name="handoff.action",
        method_name="on_handoff_action",
        input_model=HandoffActionInvokeActivity,
        selector=lambda activity: activity.type == "invoke" and cast(InvokeActivity, activity).name == "handoff/action",
        output_model=None,
        is_invoke=True,
    ),
    "signin.token-exchange": ActivityConfig(
        name="signin.token-exchange",
        method_name="on_signin_token_exchange",
        input_model=SignInTokenExchangeInvokeActivity,
        selector=lambda activity: activity.type == "invoke"
        and cast(InvokeActivity, activity).name == "signin/tokenExchange",
        output_type_name="TokenExchangeInvokeResponseType",
        is_invoke=True,
    ),
    "signin.verify-state": ActivityConfig(
        name="signin.verify-state",
        method_name="on_signin_verify_state",
        input_model=SignInVerifyStateInvokeActivity,
        selector=lambda activity: activity.type == "invoke"
        and cast(InvokeActivity, activity).name == "signin/verifyState",
        output_model=None,
        is_invoke=True,
    ),
    "card.action": ActivityConfig(
        name="card.action",
        method_name="on_card_action",
        input_model="AdaptiveCardInvokeActivity",
        selector=lambda activity: activity.type == "invoke"
        and cast(InvokeActivity, activity).name == "adaptiveCard/action",
        output_type_name="AdaptiveCardInvokeResponse",
        is_invoke=True,
    ),
    # Generic invoke handler (fallback for any invoke not matching specific aliases)
    "invoke": ActivityConfig(
        name="invoke",
        method_name="on_invoke",
        input_model="InvokeActivity",
        selector=lambda activity: activity.type == "invoke",
        output_model=None,
    ),
    "installation_update": ActivityConfig(
        name="installation_update",
        method_name="on_installation_update",
        input_model="InstallUpdateActivity",
        selector=lambda activity: activity.type == "installationUpdate",
        output_model=None,
    ),
    "install.add": ActivityConfig(
        name="install.add",
        method_name="on_install_add",
        input_model=InstalledActivity,
        selector=lambda activity: isinstance(activity, InstalledActivity),
        output_model=None,
    ),
    "install.remove": ActivityConfig(
        name="install.remove",
        method_name="on_install_remove",
        input_model=UninstalledActivity,
        selector=lambda activity: isinstance(activity, UninstalledActivity),
        output_model=None,
    ),
    # Other Core Activities
    "typing": ActivityConfig(
        name="typing",
        method_name="on_typing",
        input_model=TypingActivity,
        selector=lambda activity: isinstance(activity, TypingActivity),
        output_model=None,
    ),
    "trace": ActivityConfig(
        name="trace",
        method_name="on_trace",
        input_model=TraceActivity,
        selector=lambda activity: isinstance(activity, TraceActivity),
        output_model=None,
    ),
    "handoff": ActivityConfig(
        name="handoff",
        method_name="on_handoff",
        input_model=HandoffActivity,
        selector=lambda activity: isinstance(activity, HandoffActivity),
        output_model=None,
    ),
    # Generic Activity Handler (catch-all)
    "activity": ActivityConfig(
        name="activity",
        method_name="on_activity",
        input_model="Activity",
        selector=lambda activity: True,
        output_model=None,
    ),
}
