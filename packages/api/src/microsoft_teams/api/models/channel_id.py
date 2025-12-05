"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Union

# Define the literal types for known channel IDs
KnownChannelID = Literal["webchat", "msteams"]

# Type alias for channel ID that can be either a known type or any other string
ChannelID = Union[KnownChannelID, str]
