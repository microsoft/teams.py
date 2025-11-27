"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Generic, Optional, TypeVar, Union

from .adaptive_card.adaptive_card_action_response import AdaptiveCardActionResponse
from .config.config_response import ConfigResponse
from .custom_base_model import CustomBaseModel
from .messaging_extension.messaging_extension_action_response import MessagingExtensionActionResponse
from .messaging_extension.messaging_extension_response import MessagingExtensionResponse
from .tab.tab_response import TabResponse
from .task_module.task_module_response import TaskModuleResponse
from .token_exchange.invoke_response import TokenExchangeInvokeResponse

# Union type for all possible invoke response bodies
InvokeResponseBody = Union[
    ConfigResponse,  # config/fetch, config/submit
    None,  # fileConsent/invoke, actionableMessage/executeAction, message/submitAction,
    # handoff/action, signin/verifyState, composeExtension/onCardButtonClicked
    MessagingExtensionResponse,  # composeExtension/queryLink, composeExtension/anonymousQueryLink,
    # composeExtension/query, composeExtension/selectItem, composeExtension/querySettingUrl,
    # composeExtension/setting
    MessagingExtensionActionResponse,  # composeExtension/submitAction, composeExtension/fetchTask
    TaskModuleResponse,  # task/fetch, task/submit
    TabResponse,  # tab/fetch, tab/submit
    AdaptiveCardActionResponse,  # adaptiveCard/action
    TokenExchangeInvokeResponse,  # signin/tokenExchange
]  # Type variable for generic invoke response

T = TypeVar("T", bound=InvokeResponseBody)


class InvokeResponse(CustomBaseModel, Generic[T]):
    """
    Represents a response returned by a bot when it receives an `invoke` activity.

    This class supports the framework and is not intended to be called directly for your code.
    """

    status: int = 200
    """The HTTP status code of the response."""

    body: Optional[T] = None
    """Optional. The body of the response."""


def is_invoke_response(value: Any) -> bool:
    """
    Type guard to check if a value is an InvokeResponse.

    Args:
        value: Value to compare

    Returns:
        True if value is type of InvokeResponse
    """
    return (isinstance(value, dict) and "status" in value and isinstance(value["status"], int)) or isinstance(
        value, InvokeResponse
    )


# Specific invoke response types for different invoke names
ConfigInvokeResponse = ConfigResponse
VoidInvokeResponse = None
MessagingExtensionInvokeResponse = MessagingExtensionResponse
MessagingExtensionActionInvokeResponse = MessagingExtensionActionResponse
TaskModuleInvokeResponse = TaskModuleResponse
TabInvokeResponse = TabResponse
AdaptiveCardInvokeResponse = AdaptiveCardActionResponse
TokenExchangeInvokeResponseType = Union[TokenExchangeInvokeResponse, None]
