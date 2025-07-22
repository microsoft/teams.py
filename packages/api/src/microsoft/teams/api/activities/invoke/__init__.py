"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Annotated, Union

from pydantic import Field

from .adaptive_card import AdaptiveCardInvokeActivity
from .config import *  # noqa: F403
from .config import ConfigInvokeActivity
from .config import __all__ as config_invoke_all
from .execute_action import ExecuteActionInvokeActivity
from .file_consent import FileConsentInvokeActivity
from .handoff_action import HandoffActionInvokeActivity
from .message import MessageInvokeActivity
from .message_extension import *  # noqa: F403
from .message_extension import MessageExtensionInvokeActivity
from .message_extension import __all__ as message_extension_invoke_all
from .sign_in import *  # noqa: F403
from .sign_in import SignInInvokeActivity
from .sign_in import __all__ as sign_in_invoke_all
from .tab import *  # noqa: F403
from .tab import TabInvokeActivity
from .tab import __all__ as tab_invoke_all
from .task import *  # noqa: F403
from .task import TaskInvokeActivity
from .task import __all__ as task_invoke_all

InvokeActivity = Annotated[
    Union[
        FileConsentInvokeActivity,
        ExecuteActionInvokeActivity,
        MessageExtensionInvokeActivity,
        ConfigInvokeActivity,
        TabInvokeActivity,
        TaskInvokeActivity,
        MessageInvokeActivity,
        HandoffActionInvokeActivity,
        SignInInvokeActivity,
        AdaptiveCardInvokeActivity,
    ],
    Field(discriminator="name"),
]


__all__ = [
    *config_invoke_all,
    *message_extension_invoke_all,
    *sign_in_invoke_all,
    *tab_invoke_all,
    *task_invoke_all,
    "InvokeActivity",
    "FileConsentInvokeActivity",
    "ExecuteActionInvokeActivity",
    "MessageExtensionInvokeActivity",
    "ConfigInvokeActivity",
    "TabInvokeActivity",
    "TaskInvokeActivity",
    "MessageInvokeActivity",
    "HandoffActionInvokeActivity",
    "SignInInvokeActivity",
    "AdaptiveCardInvokeActivity",
]
