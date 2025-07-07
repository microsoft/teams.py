"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Union

from .tab_fetch import TabFetchInvokeActivity
from .tab_submit import TabSubmitInvokeActivity

TabInvokeActivity = Union[TabFetchInvokeActivity, TabSubmitInvokeActivity]

__all__ = [
    "TabFetchInvokeActivity",
    "TabSubmitInvokeActivity",
    "TabInvokeActivity",
]
