"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict

from ..core import SubmitActionData

RESERVED_KEYWORD = "action"


class EnhancedSubmitActionData(SubmitActionData):
    """
    Utility class for creating submit action data with action-based routing.

    This class extends the base SubmitActionData with a convenience constructor that
    accepts an action identifier for routing submissions to specific handlers.

    Args:
        action: The action identifier that determines which handler processes the submission.
        data: Optional additional data to include with the submission.

    Example:
        >>> submit_data = SubmitActionData(action="submit_user_form", data={"user_id": "123"})
        >>> submit_action = SubmitAction(title="Submit").with_data(submit_data)
    """

    def __init__(self, action: str, data: Dict[str, Any] | None = None):
        super().__init__()
        if data:
            merged_data = {**data}
        else:
            merged_data = {}
        merged_data[RESERVED_KEYWORD] = action
        self.with_data(merged_data)
