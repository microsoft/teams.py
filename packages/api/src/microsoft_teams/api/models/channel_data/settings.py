"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from ..custom_base_model import CustomBaseModel
from .channel_info import ChannelInfo


class ChannelDataSettings(CustomBaseModel):
    """
    Settings within teams channel data specific to messages received in Microsoft Teams.
    """

    selected_channel: ChannelInfo
    "Information about the selected Teams channel."
