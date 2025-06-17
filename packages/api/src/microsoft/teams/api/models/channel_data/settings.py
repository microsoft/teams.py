"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from pydantic import ConfigDict

from ..custom_base_model import CustomBaseModel
from .channel_info import ChannelInfo


class ChannelDataSettings(CustomBaseModel):
    """
    Settings within teams channel data specific to messages received in Microsoft Teams.
    """

    model_config = ConfigDict(
        **CustomBaseModel.model_config,
        extra="allow",
    )

    selected_channel: ChannelInfo
    "Information about the selected Teams channel."
