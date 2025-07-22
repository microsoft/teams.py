"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Callable, Dict, NamedTuple, Optional, Type

from microsoft.teams.api import (
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
        input_type_name="MessageActivity",
    ),
    "messageDelete": ActivityConfig(
        name="messageDelete",
        method_name="onMessageDelete",
        input_model=MessageDeleteActivity,
        selector=lambda activity: isinstance(activity, MessageDeleteActivity),
        output_model=None,
        input_type_name="MessageDeleteActivity",
    ),
    "messageReaction": ActivityConfig(
        name="messageReaction",
        method_name="onMessageReaction",
        input_model=MessageReactionActivity,
        selector=lambda activity: isinstance(activity, MessageReactionActivity),
        output_model=None,
        input_type_name="MessageReactionActivity",
    ),
    "messageUpdate": ActivityConfig(
        name="messageUpdate",
        method_name="onMessageUpdate",
        input_model=MessageUpdateActivity,
        selector=lambda activity: isinstance(activity, MessageUpdateActivity),
        output_model=None,
        input_type_name="MessageUpdateActivity",
    ),
    # Command Activities
    "command": ActivityConfig(
        name="command",
        method_name="onCommand",
        input_model=CommandSendActivity,
        selector=lambda activity: isinstance(activity, CommandSendActivity),
        output_model=None,
        input_type_name="CommandSendActivity",
    ),
    "commandResult": ActivityConfig(
        name="commandResult",
        method_name="onCommandResult",
        input_model=CommandResultActivity,
        selector=lambda activity: isinstance(activity, CommandResultActivity),
        output_model=None,
        input_type_name="CommandResultActivity",
    ),
    # Conversation Activities
    "conversationUpdate": ActivityConfig(
        name="conversationUpdate",
        method_name="onConversationUpdate",
        input_model=ConversationUpdateActivity,
        selector=lambda activity: isinstance(activity, ConversationUpdateActivity),
        output_model=None,
        input_type_name="ConversationUpdateActivity",
    ),
    "endOfConversation": ActivityConfig(
        name="endOfConversation",
        method_name="onEndOfConversation",
        input_model=EndOfConversationActivity,
        selector=lambda activity: isinstance(activity, EndOfConversationActivity),
        output_model=None,
        input_type_name="EndOfConversationActivity",
    ),
    # Complex Union Activities (discriminated by sub-fields)
    "event": ActivityConfig(
        name="event",
        method_name="onEvent",
        input_model=EventActivity,
        selector=lambda activity: isinstance(activity, EventActivity),
        output_model=None,
        input_type_name="EventActivity",
    ),
    # Invoke Activities with specific names and response types
    "config.open": ActivityConfig(
        name="config.open",
        method_name="onConfigOpen",
        input_model=ConfigFetchInvokeActivity,
        selector=lambda activity: isinstance(activity, ConfigFetchInvokeActivity),
        output_model=ConfigInvokeResponse,
        output_type_name="ConfigInvokeResponse",
        input_type_name="ConfigFetchInvokeActivity",
    ),
    "config.submit": ActivityConfig(
        name="config.submit",
        method_name="onConfigSubmit",
        input_model=ConfigSubmitInvokeActivity,
        selector=lambda activity: isinstance(activity, ConfigSubmitInvokeActivity),
        output_model=ConfigInvokeResponse,
        output_type_name="ConfigInvokeResponse",
        input_type_name="ConfigSubmitInvokeActivity",
    ),
    "file.consent": ActivityConfig(
        name="file.consent",
        method_name="onFileConsent",
        input_model=FileConsentInvokeActivity,
        selector=lambda activity: isinstance(activity, InvokeActivity) and activity.name == "fileConsent/invoke",
        output_model=VoidInvokeResponse,
        output_type_name="VoidInvokeResponse",
        input_type_name="FileConsentInvokeActivity",
    ),
    "message.execute": ActivityConfig(
        name="message.execute",
        method_name="onMessageExecute",
        input_model=ExecuteActionInvokeActivity,
        selector=lambda activity: isinstance(activity, InvokeActivity)
        and activity.name == "actionableMessage/executeAction",
        output_model=VoidInvokeResponse,
        output_type_name="VoidInvokeResponse",
        input_type_name="ExecuteActionInvokeActivity",
    ),
    "message.ext.query-link": ActivityConfig(
        name="message.ext.query-link",
        method_name="onMessageExtQueryLink",
        input_model=MessageExtensionQueryLinkInvokeActivity,
        selector=lambda activity: isinstance(activity, InvokeActivity)
        and activity.name == "composeExtension/queryLink",
        output_model=MessagingExtensionInvokeResponse,
        output_type_name="MessagingExtensionInvokeResponse",
        input_type_name="MessageExtensionQueryLinkInvokeActivity",
    ),
    "message.ext.anon-query-link": ActivityConfig(
        name="message.ext.anon-query-link",
        method_name="onMessageExtAnonQueryLink",
        input_model=MessageExtensionAnonQueryLinkInvokeActivity,
        selector=lambda activity: isinstance(activity, InvokeActivity)
        and activity.name == "composeExtension/anonymousQueryLink",
        output_model=MessagingExtensionInvokeResponse,
        output_type_name="MessagingExtensionInvokeResponse",
        input_type_name="MessageExtensionAnonQueryLinkInvokeActivity",
    ),
    "message.ext.query": ActivityConfig(
        name="message.ext.query",
        method_name="onMessageExtQuery",
        input_model=MessageExtensionQueryInvokeActivity,
        selector=lambda activity: isinstance(activity, MessageExtensionQueryInvokeActivity)
        and activity.name == "composeExtension/query",
        output_model=MessagingExtensionInvokeResponse,
        output_type_name="MessagingExtensionInvokeResponse",
        input_type_name="MessageExtensionQueryInvokeActivity",
    ),
    "message.ext.select-item": ActivityConfig(
        name="message.ext.select-item",
        method_name="onMessageExtSelectItem",
        input_model=MessageExtensionSelectItemInvokeActivity,
        selector=lambda activity: isinstance(activity, MessageExtensionSelectItemInvokeActivity)
        and activity.name == "composeExtension/selectItem",
        output_model=MessagingExtensionInvokeResponse,
        output_type_name="MessagingExtensionInvokeResponse",
        input_type_name="MessageExtensionSelectItemInvokeActivity",
    ),
    "message.ext.submit": ActivityConfig(
        name="message.ext.submit",
        method_name="onMessageExtSubmit",
        input_model=MessageExtensionSubmitActionInvokeActivity,
        selector=lambda activity: isinstance(activity, MessageExtensionSubmitActionInvokeActivity)
        and activity.name == "composeExtension/submitAction",
        output_model=MessagingExtensionActionInvokeResponse,
        output_type_name="MessagingExtensionActionInvokeResponse",
        input_type_name="MessageExtensionSubmitActionInvokeActivity",
    ),
    "message.ext.open": ActivityConfig(
        name="message.ext.open",
        method_name="onMessageExtOpen",
        input_model=MessageExtensionFetchTaskInvokeActivity,
        selector=lambda activity: isinstance(activity, MessageExtensionFetchTaskInvokeActivity)
        and activity.name == "composeExtension/fetchTask",
        output_model=MessagingExtensionActionInvokeResponse,
        output_type_name="MessagingExtensionActionInvokeResponse",
        input_type_name="MessageExtensionFetchTaskInvokeActivity",
    ),
    "message.ext.query-settings-url": ActivityConfig(
        name="message.ext.query-settings-url",
        method_name="onMessageExtQuerySettingsUrl",
        input_model=MessageExtensionQuerySettingUrlInvokeActivity,
        selector=lambda activity: isinstance(activity, MessageExtensionQuerySettingUrlInvokeActivity)
        and activity.name == "composeExtension/querySettingUrl",
        output_model=MessagingExtensionInvokeResponse,
        output_type_name="MessagingExtensionInvokeResponse",
        input_type_name="MessageExtensionQuerySettingUrlInvokeActivity",
    ),
    "message.ext.setting": ActivityConfig(
        name="message.ext.setting",
        method_name="onMessageExtSetting",
        input_model=MessageExtensionSettingInvokeActivity,
        selector=lambda activity: isinstance(activity, MessageExtensionSettingInvokeActivity)
        and activity.name == "composeExtension/setting",
        output_model=MessagingExtensionInvokeResponse,
        output_type_name="MessagingExtensionInvokeResponse",
        input_type_name="MessageExtensionSettingInvokeActivity",
    ),
    "message.ext.card-button-clicked": ActivityConfig(
        name="message.ext.card-button-clicked",
        method_name="onMessageExtCardButtonClicked",
        input_model=MessageExtensionCardButtonClickedInvokeActivity,
        selector=lambda activity: isinstance(activity, MessageExtensionCardButtonClickedInvokeActivity),
        output_model=VoidInvokeResponse,
        output_type_name="VoidInvokeResponse",
        input_type_name="MessageExtensionCardButtonClickedInvokeActivity",
    ),
    "dialog.open": ActivityConfig(
        name="dialog.open",
        method_name="onDialogOpen",
        input_model=TaskFetchInvokeActivity,
        selector=lambda activity: isinstance(activity, InvokeActivity) and activity.name == "task/fetch",
        output_model=TaskModuleInvokeResponse,
        output_type_name="TaskModuleInvokeResponse",
        input_type_name="TaskFetchInvokeActivity",
    ),
    "dialog.submit": ActivityConfig(
        name="dialog.submit",
        method_name="onDialogSubmit",
        input_model=TaskSubmitInvokeActivity,
        selector=lambda activity: isinstance(activity, InvokeActivity) and activity.name == "task/submit",
        output_model=TaskModuleInvokeResponse,
        output_type_name="TaskModuleInvokeResponse",
        input_type_name="TaskSubmitInvokeActivity",
    ),
    "tab.open": ActivityConfig(
        name="tab.open",
        method_name="onTabOpen",
        input_model=TabFetchInvokeActivity,
        selector=lambda activity: isinstance(activity, InvokeActivity) and activity.name == "tab/fetch",
        output_model=TabInvokeResponse,
        output_type_name="TabInvokeResponse",
        input_type_name="TabFetchInvokeActivity",
    ),
    "tab.submit": ActivityConfig(
        name="tab.submit",
        method_name="onTabSubmit",
        input_model=TabSubmitInvokeActivity,
        selector=lambda activity: isinstance(activity, InvokeActivity) and activity.name == "tab/submit",
        output_model=TabInvokeResponse,
        output_type_name="TabInvokeResponse",
        input_type_name="TabSubmitInvokeActivity",
    ),
    "message.submit": ActivityConfig(
        name="message.submit",
        method_name="onMessageSubmit",
        input_model=MessageInvokeActivity,
        selector=lambda activity: isinstance(activity, InvokeActivity) and activity.name == "message/submitAction",
        output_model=VoidInvokeResponse,
        output_type_name="VoidInvokeResponse",
        input_type_name="MessageInvokeActivity",
    ),
    "handoff.action": ActivityConfig(
        name="handoff.action",
        method_name="onHandoffAction",
        input_model=HandoffActionInvokeActivity,
        selector=lambda activity: isinstance(activity, InvokeActivity) and activity.name == "handoff/action",
        output_model=VoidInvokeResponse,
        output_type_name="VoidInvokeResponse",
        input_type_name="HandoffActionInvokeActivity",
    ),
    "signin.token-exchange": ActivityConfig(
        name="signin.token-exchange",
        method_name="onSigninTokenExchange",
        input_model=SignInTokenExchangeInvokeActivity,
        selector=lambda activity: isinstance(activity, InvokeActivity) and activity.name == "signin/tokenExchange",
        output_model=TokenExchangeInvokeResponseType,
        output_type_name="TokenExchangeInvokeResponseType",
        input_type_name="SignInTokenExchangeInvokeActivity",
    ),
    "signin.verify-state": ActivityConfig(
        name="signin.verify-state",
        method_name="onSigninVerifyState",
        input_model=SignInVerifyStateInvokeActivity,
        selector=lambda activity: isinstance(activity, InvokeActivity) and activity.name == "signin/verifyState",
        output_model=VoidInvokeResponse,
        output_type_name="VoidInvokeResponse",
        input_type_name="SignInVerifyStateInvokeActivity",
    ),
    "card.action": ActivityConfig(
        name="card.action",
        method_name="onCardAction",
        input_model=AdaptiveCardInvokeActivity,
        selector=lambda activity: isinstance(activity, InvokeActivity) and activity.name == "adaptiveCard/action",
        output_model=AdaptiveCardInvokeResponse,
        output_type_name="AdaptiveCardInvokeResponse",
        input_type_name="AdaptiveCardInvokeActivity",
    ),
    # Generic invoke handler (fallback for any invoke not matching specific aliases)
    "invoke": ActivityConfig(
        name="invoke",
        method_name="onInvoke",
        input_model=InvokeActivity,
        selector=lambda activity: isinstance(activity, InvokeActivity),
        output_model=None,
        input_type_name="InvokeActivity",
    ),
    "installationUpdate": ActivityConfig(
        name="installationUpdate",
        method_name="onInstallationUpdate",
        input_model=InstallUpdateActivity,
        selector=lambda activity: isinstance(activity, InstallUpdateActivity),
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
        input_type_name="TypingActivity",
    ),
    "trace": ActivityConfig(
        name="trace",
        method_name="onTrace",
        input_model=TraceActivity,
        selector=lambda activity: isinstance(activity, TraceActivity),
        output_model=None,
        input_type_name="TraceActivity",
    ),
    "handoff": ActivityConfig(
        name="handoff",
        method_name="onHandoff",
        input_model=HandoffActivity,
        selector=lambda activity: isinstance(activity, HandoffActivity),
        output_model=None,
        input_type_name="HandoffActivity",
    ),
    # Generic Activity Handler (catch-all)
    "activity": ActivityConfig(
        name="activity",
        method_name="onActivity",
        input_model=ActivityBase,
        selector=lambda activity: True,
        output_model=None,
        input_type_name="ActivityBase",
    ),
}
