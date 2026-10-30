"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Union

KnownConversationType = Literal["personal", "groupChat", "channel"]

ConversationType = Union[KnownConversationType, str]
