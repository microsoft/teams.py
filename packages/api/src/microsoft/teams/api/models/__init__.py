"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from .account import Account, AccountRole, ConversationAccount
from .action import Action
from .activity import Activity
from .adaptive_card import *  # noqa: F403
from .adaptive_card import __all__ as adaptive_card_all
from .app_based_link_query import AppBasedLinkQuery
from .attachment import *  # noqa: F403
from .attachment import __all__ as attachment_all
from .cache_info import CacheInfo
from .card import *  # noqa: F403
from .card import __all__ as card_all
from .channel_data import *  # noqa: F403
from .channel_data import __all__ as channel_data_all
from .channel_id import ChannelID
from .config import *  # noqa: F403
from .config import __all__ as config_all
from .conversation import *  # noqa: F403  # noqa: F403
from .conversation import __all__ as conversation_all
from .custom_base_model import CustomBaseModel
from .delivery_mode import DeliveryMode
from .entity import *  # noqa: F403  # noqa: F403
from .entity import __all__ as entity_all
from .error import ErrorResponse, HttpError, InnerHttpError
from .file import *  # noqa: F403  # noqa: F403
from .file import __all__ as file_all
from .importance import Importance
from .input_hint import InputHint
from .meetings import *  # noqa: F403
from .meetings import __all__ as meetings_all
from .message import *  # noqa: F403
from .message import __all__ as message_all
from .messaging_extension import *  # noqa: F403
from .messaging_extension import __all__ as messaging_extension_all
from .o365 import *  # noqa: F403
from .o365 import __all__ as o365_all
from .resource import Resource
from .sign_in import *  # noqa: F403
from .sign_in import __all__ as sign_in_all
from .suggested_actions import SuggestedActions
from .tab import *  # noqa: F403
from .tab import __all__ as tab_all
from .task_module import *  # noqa: F403
from .task_module import __all__ as task_module_all
from .team_details import TeamDetails
from .text_format import TextFormat
from .token import *  # noqa: F403
from .token import __all__ as token_all
from .token_exchange import *  # noqa: F403
from .token_exchange import __all__ as token_exchange_all

__all__ = [
    *entity_all,
    *file_all,
    *meetings_all,
    *message_all,
    *messaging_extension_all,
    "Action",
    "CustomBaseModel",
    "Importance",
    *adaptive_card_all,
    *attachment_all,
    *card_all,
    *channel_data_all,
    *config_all,
    *conversation_all,
    "CustomBaseModel",
    "Account",
    "ConversationAccount",
    "Activity",
    "AccountRole",
    "ConversationAccount",
    "ChannelID",
    *conversation_all,
    *sign_in_all,
    "TeamDetails",
    *token_all,
    *token_exchange_all,
    "AppBasedLinkQuery",
    "CacheInfo",
    "DeliveryMode",
    "ErrorResponse",
    "HttpError",
    "InnerHttpError",
    "InputHint",
    "Resource",
    "SuggestedActions",
    "TeamDetails",
    "TextFormat",
    *tab_all,
    *task_module_all,
    *o365_all,
]
