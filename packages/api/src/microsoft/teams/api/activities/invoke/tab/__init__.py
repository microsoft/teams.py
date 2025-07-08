"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Annotated, Union

from pydantic import Field

from .tab_fetch import TabFetchInvokeActivity
from .tab_submit import TabSubmitInvokeActivity

TabInvokeActivity = Annotated[
    Union[TabFetchInvokeActivity, TabSubmitInvokeActivity],
    Field(discriminator="name"),
]

__all__ = [
    "TabFetchInvokeActivity",
    "TabSubmitInvokeActivity",
    "TabInvokeActivity",
]
