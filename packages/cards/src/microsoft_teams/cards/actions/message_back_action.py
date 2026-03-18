"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import warnings
from typing import Optional

from ..core import MessageBackSubmitActionData, SubmitAction, SubmitActionData


class MessageBackAction(SubmitAction):
    """This class is deprecated. Please use MessageBackSubmitActionData instead.
    This will be removed in a future version of the SDK."""

    def __init__(self, text: str, value: str, display_text: Optional[str] = None):
        warnings.warn(
            "MessageBackAction is deprecated. Use MessageBackSubmitActionData instead. "
            "This will be removed in a future version of the SDK.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__()
        action_data = MessageBackSubmitActionData().with_value(value).with_text(text)

        if display_text:
            action_data = action_data.with_display_text(display_text)

        self.data = SubmitActionData(ms_teams=action_data.model_dump())
