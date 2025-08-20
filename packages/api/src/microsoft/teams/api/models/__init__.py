"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from . import (
    adaptive_card,
    attachment,
    card,
    channel_data,
    config,
    conversation,
    entity,
    file,
    meetings,
    message,
    messaging_extension,
    o365,
    sign_in,
    tab,
    task_module,
    token,
    token_exchange,
)
from .account import Account, AccountRole, ConversationAccount
from .action import Action
from .activity import Activity as ActivityBase
from .activity import ActivityInput as ActivityInputBase
from .adaptive_card import *  # noqa: F403
from .app_based_link_query import AppBasedLinkQuery
from .attachment import *  # noqa: F403
from .cache_info import CacheInfo
from .card import *  # noqa: F403
from .channel_data import *  # noqa: F403
from .channel_id import ChannelID
from .config import *  # noqa: F403
from .conversation import *  # noqa: F403
from .custom_base_model import CustomBaseModel
from .delivery_mode import DeliveryMode
from .entity import *  # noqa: F403
from .error import ErrorResponse, HttpError, InnerHttpError
from .file import *  # noqa: F403
from .importance import Importance
from .input_hint import InputHint
from .invoke_response import (
    AdaptiveCardInvokeResponse,
    ConfigInvokeResponse,
    InvokeResponse,
    MessagingExtensionActionInvokeResponse,
    MessagingExtensionInvokeResponse,
    TabInvokeResponse,
    TaskModuleInvokeResponse,
    TokenExchangeInvokeResponseType,
    VoidInvokeResponse,
    is_invoke_response,
)
from .meetings import *  # noqa: F403
from .message import *  # noqa: F403
from .messaging_extension import *  # noqa: F403
from .o365 import *  # noqa: F403
from .sign_in import *  # noqa: F403
from .suggested_actions import SuggestedActions
from .tab import *  # noqa: F403
from .task_module import *  # noqa: F403
from .team_details import TeamDetails
from .text_format import TextFormat
from .token import *  # noqa: F403
from .token_exchange import *  # noqa: F403

# Combine all exports from submodules
__all__: list[str] = [
    "Account",
    "AccountRole",
    "Action",
    "ActivityBase",
    "ActivityInputBase",
    "AppBasedLinkQuery",
    "CacheInfo",
    "ChannelID",
    "ConversationAccount",
    "CustomBaseModel",
    "DeliveryMode",
    "ErrorResponse",
    "HttpError",
    "Importance",
    "InnerHttpError",
    "InputHint",
    "InvokeResponse",
    "SuggestedActions",
    "TeamDetails",
    "TextFormat",
    "InvokeResponse",
    "ConfigInvokeResponse",
    "VoidInvokeResponse",
    "MessagingExtensionInvokeResponse",
    "MessagingExtensionActionInvokeResponse",
    "TaskModuleInvokeResponse",
    "TabInvokeResponse",
    "AdaptiveCardInvokeResponse",
    "TokenExchangeInvokeResponseType",
    "is_invoke_response",
]
__all__.extend(adaptive_card.__all__)
__all__.extend(attachment.__all__)
__all__.extend(card.__all__)
__all__.extend(channel_data.__all__)
__all__.extend(config.__all__)
__all__.extend(conversation.__all__)
__all__.extend(entity.__all__)
__all__.extend(file.__all__)
__all__.extend(meetings.__all__)
__all__.extend(message.__all__)
__all__.extend(messaging_extension.__all__)
__all__.extend(o365.__all__)
__all__.extend(sign_in.__all__)
__all__.extend(tab.__all__)
__all__.extend(task_module.__all__)
__all__.extend(token.__all__)
__all__.extend(token_exchange.__all__)
