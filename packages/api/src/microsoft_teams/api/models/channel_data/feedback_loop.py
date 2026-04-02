"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ..custom_base_model import CustomBaseModel


class FeedbackLoop(CustomBaseModel):
    """Configuration for a custom feedback loop on a message."""

    type: Literal["custom", "default"] = "custom"
    """The type of feedback loop. Use 'custom' to show a task module dialog."""
