"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Union

# Define the literal types for known conversation types
KnownConversationType = Literal["personal", "groupChat", "channel"]

# Type alias for conversation type that can be either a known type or any other string
ConversationType = Union[KnownConversationType, str]
