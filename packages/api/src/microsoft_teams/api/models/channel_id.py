"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Union

KnownChannelID = Literal["webchat", "msteams"]

ChannelID = Union[KnownChannelID, str]
