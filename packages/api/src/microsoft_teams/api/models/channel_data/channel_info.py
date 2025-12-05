"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from ..custom_base_model import CustomBaseModel


class ChannelInfo(CustomBaseModel):
    """
    A channel info object which describes the channel.
    """

    id: str
    "Unique identifier representing a channel"

    name: Optional[str] = None
    "Name of the channel"

    type: Optional[Literal["standard", "shared", "private"]] = None
    "The type of the channel. Valid values are standard, shared and private."
