"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Union

DeliveryMode = Union[Literal["normal", "notification", "expectReplies", "ephemeral"], str]
