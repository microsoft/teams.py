"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Union

from .anon_query_link import MessageExtensionAnonQueryLinkInvokeActivity
from .card_button_clicked import MessageExtensionCardButtonClickedInvokeActivity
from .fetch_task import MessageExtensionFetchTaskInvokeActivity
from .query import MessageExtensionQueryInvokeActivity
from .query_link import MessageExtensionQueryLinkInvokeActivity
from .query_setting_url import MessageExtensionQuerySettingUrlInvokeActivity
from .select_item import MessageExtensionSelectItemInvokeActivity
from .setting import MessageExtensionSettingInvokeActivity
from .submit_action import MessageExtensionSubmitActionInvokeActivity

MessageExtensionInvokeActivity = Union[
    MessageExtensionAnonQueryLinkInvokeActivity,
    MessageExtensionCardButtonClickedInvokeActivity,
    MessageExtensionFetchTaskInvokeActivity,
    MessageExtensionQueryInvokeActivity,
    MessageExtensionQueryLinkInvokeActivity,
    MessageExtensionQuerySettingUrlInvokeActivity,
    MessageExtensionSelectItemInvokeActivity,
    MessageExtensionSettingInvokeActivity,
    MessageExtensionSubmitActionInvokeActivity,
]

__all__ = [
    "MessageExtensionAnonQueryLinkInvokeActivity",
    "MessageExtensionCardButtonClickedInvokeActivity",
    "MessageExtensionFetchTaskInvokeActivity",
    "MessageExtensionQueryInvokeActivity",
    "MessageExtensionQueryLinkInvokeActivity",
    "MessageExtensionQuerySettingUrlInvokeActivity",
    "MessageExtensionSelectItemInvokeActivity",
    "MessageExtensionSettingInvokeActivity",
    "MessageExtensionSubmitActionInvokeActivity",
    "MessageExtensionInvokeActivity",
]
