"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Union

from ..custom_base_model import CustomBaseModel

FeedbackLoopType = Union[Literal["custom", "default"], str]


class FeedbackLoop(CustomBaseModel):
    """Configuration for a custom feedback loop on a message."""

    type: FeedbackLoopType = "default"
    """The type of feedback loop. Use `custom` to show a task module dialog"""
