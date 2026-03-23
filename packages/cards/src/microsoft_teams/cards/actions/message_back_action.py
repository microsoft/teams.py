"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import warnings
from typing import Any, Dict, Optional, Union

from ..core import MessageBackSubmitActionData, SubmitAction, SubmitActionData


class MessageBackAction(SubmitAction):
    """This class is deprecated. Please use MessageBackSubmitActionData instead.
    This will be removed in version 2.0.0 GA."""

    def __init__(self, text: str, value: Union[str, Dict[str, Any]], display_text: Optional[str] = None):
        warnings.warn(
            "MessageBackAction is deprecated. Use MessageBackSubmitActionData instead. "
            "This will be removed in version 2.0.0 GA.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__()
        action_value = {"value": value} if isinstance(value, str) else value
        action_data = MessageBackSubmitActionData().with_value(action_value).with_text(text)

        if display_text:
            action_data = action_data.with_display_text(display_text)

        self.data = SubmitActionData(ms_teams=action_data.model_dump())
