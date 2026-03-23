"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import warnings
from typing import Any, Dict

from ..core import InvokeSubmitActionData, SubmitAction, SubmitActionData


class InvokeAction(SubmitAction):
    """This class is deprecated. Please use InvokeSubmitActionData instead.
    This will be removed in version 2.0.0 GA."""

    def __init__(self, value: Dict[str, Any]):
        warnings.warn(
            "InvokeAction is deprecated. Use InvokeSubmitActionData instead. "
            "This will be removed in version 2.0.0 GA.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__()
        action_data = InvokeSubmitActionData().with_value(value)
        self.data = SubmitActionData(ms_teams=action_data.model_dump())
