"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional, Union

from ..custom_base_model import CustomBaseModel

ChannelType = Union[Literal["standard", "shared", "private"], str]


class ChannelInfo(CustomBaseModel):
    """
    A channel info object which describes the channel.
    """

    id: Optional[str] = None
    "Unique identifier representing a channel"

    name: Optional[str] = None
    "Name of the channel"

    type: Optional[ChannelType] = None
    "The type of the channel. Valid values are standard, shared and private."
