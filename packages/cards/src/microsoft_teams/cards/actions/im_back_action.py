"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from ..core import ImBackSubmitActionData, SubmitAction, SubmitActionData


class IMBackAction(SubmitAction):
    """Initial data that input fields will be combined with. These are essentially ‘hidden’ properties."""

    def __init__(self, value: str):
        super().__init__()
        action_data = ImBackSubmitActionData().with_value(value)
        self.data = SubmitActionData(ms_teams=action_data.model_dump())
