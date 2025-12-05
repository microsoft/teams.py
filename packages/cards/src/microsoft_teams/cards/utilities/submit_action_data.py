"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict, Optional

from ..core import SubmitActionData as BaseSubmitActionData

RESERVED_KEYWORD = "action"


class EnhancedSubmitActionData(BaseSubmitActionData):
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

    def __init__(
        self,
        action: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ):
        # If action is provided, use convenience constructor
        if action is not None:
            super().__init__(**kwargs)
            merged_data = data.copy() if data else {}
            merged_data[RESERVED_KEYWORD] = action
            self.with_data(merged_data)
        else:
            # Otherwise, use standard Pydantic initialization for model_validate
            super().__init__(**kwargs)
