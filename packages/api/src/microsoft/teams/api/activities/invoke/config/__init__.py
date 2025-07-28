"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Annotated, Union

from pydantic import Field

from .config_fetch import ConfigFetchInvokeActivity
from .config_submit import ConfigSubmitInvokeActivity

ConfigInvokeActivity = Annotated[
    Union[ConfigFetchInvokeActivity, ConfigSubmitInvokeActivity], Field(discriminator="name")
]

__all__ = [
    "ConfigFetchInvokeActivity",
    "ConfigSubmitInvokeActivity",
    "ConfigInvokeActivity",
]
