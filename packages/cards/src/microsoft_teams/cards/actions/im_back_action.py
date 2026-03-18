"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import warnings

from ..core import ImBackSubmitActionData, SubmitAction, SubmitActionData


class IMBackAction(SubmitAction):
    """This class is deprecated. Please use ImBackSubmitActionData instead.
    This will be removed in a future version of the SDK."""

    def __init__(self, value: str):
        warnings.warn(
            "IMBackAction is deprecated. Use ImBackSubmitActionData instead. "
            "This will be removed in a future version of the SDK.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__()
        action_data = ImBackSubmitActionData().with_value(value)
        self.data = SubmitActionData(ms_teams=action_data.model_dump())
