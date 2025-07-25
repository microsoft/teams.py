"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Annotated, Union

from pydantic import Field

from . import config, message_extension, sign_in, tab, task
from .adaptive_card import AdaptiveCardInvokeActivity
from .config import *  # noqa: F403
from .config import ConfigInvokeActivity
from .execute_action import ExecuteActionInvokeActivity
from .file_consent import FileConsentInvokeActivity
from .handoff_action import HandoffActionInvokeActivity
from .message import MessageSubmitActionInvokeActivity
from .message_extension import *  # noqa: F403
from .message_extension import MessageExtensionInvokeActivity
from .sign_in import *  # noqa: F403
from .sign_in import SignInInvokeActivity
from .tab import *  # noqa: F403
from .tab import TabInvokeActivity
from .task import *  # noqa: F403
from .task import TaskInvokeActivity

InvokeActivity = Annotated[
    Union[
        FileConsentInvokeActivity,
        ExecuteActionInvokeActivity,
        MessageExtensionInvokeActivity,
        ConfigInvokeActivity,
        TabInvokeActivity,
        TaskInvokeActivity,
        MessageSubmitActionInvokeActivity,
        HandoffActionInvokeActivity,
        SignInInvokeActivity,
        AdaptiveCardInvokeActivity,
    ],
    Field(discriminator="name"),
]

__all__ = [
    "InvokeActivity",
    "FileConsentInvokeActivity",
    "ExecuteActionInvokeActivity",
    "MessageExtensionInvokeActivity",
    "ConfigInvokeActivity",
    "TabInvokeActivity",
    "TaskInvokeActivity",
    "MessageSubmitActionInvokeActivity",
    "HandoffActionInvokeActivity",
    "SignInInvokeActivity",
    "AdaptiveCardInvokeActivity",
]

__all__.extend(config.__all__)
__all__.extend(message_extension.__all__)
__all__.extend(sign_in.__all__)
__all__.extend(tab.__all__)
__all__.extend(task.__all__)
