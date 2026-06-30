"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Annotated, Union

from pydantic import Field

from . import config, html_widget, message_extension, sign_in, tab, task
from .adaptive_card import AdaptiveCardInvokeActivity
from .config import *  # noqa: F403
from .config import ConfigInvokeActivity
from .execute_action import ExecuteActionInvokeActivity
from .file_consent import FileConsentInvokeActivity
from .handoff_action import HandoffActionInvokeActivity
from .html_widget import HtmlWidgetCallToolInvokeActivity
from .message import (
    MessageFetchTaskActionValue,
    MessageFetchTaskData,
    MessageFetchTaskInvokeActivity,
    MessageFetchTaskInvokeValue,
    MessageSubmitActionInvokeActivity,
)
from .message_extension import *  # noqa: F403
from .message_extension import MessageExtensionInvokeActivity
from .sign_in import *  # noqa: F403
from .sign_in import SignInInvokeActivity
from .suggested_action_submit import SuggestedActionSubmitInvokeActivity
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
        MessageFetchTaskInvokeActivity,
        MessageSubmitActionInvokeActivity,
        HandoffActionInvokeActivity,
        SignInInvokeActivity,
        AdaptiveCardInvokeActivity,
        SuggestedActionSubmitInvokeActivity,
        HtmlWidgetCallToolInvokeActivity,
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
    "MessageFetchTaskActionValue",
    "MessageFetchTaskData",
    "MessageFetchTaskInvokeActivity",
    "MessageFetchTaskInvokeValue",
    "MessageSubmitActionInvokeActivity",
    "HandoffActionInvokeActivity",
    "SignInInvokeActivity",
    "AdaptiveCardInvokeActivity",
    "SuggestedActionSubmitInvokeActivity",
    "HtmlWidgetCallToolInvokeActivity",
]

__all__.extend(config.__all__)
__all__.extend(html_widget.__all__)
__all__.extend(message_extension.__all__)
__all__.extend(sign_in.__all__)
__all__.extend(tab.__all__)
__all__.extend(task.__all__)
