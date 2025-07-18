"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Annotated, Union

from pydantic import Field

from .adaptive_card import AdaptiveCardInvokeActivity
from .config import ConfigInvokeActivity
from .execute_action import ExecuteActionInvokeActivity
from .file_consent import FileConsentInvokeActivity
from .handoff_action import HandoffActionInvokeActivity
from .message import MessageInvokeActivity
from .message_extension import MessageExtensionInvokeActivity
from .sign_in import SignInInvokeActivity
from .tab import TabInvokeActivity
from .task import TaskInvokeActivity

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
