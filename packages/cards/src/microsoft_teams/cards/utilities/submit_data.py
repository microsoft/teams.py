"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict, Optional

from ..core import SubmitActionData

RESERVED_KEYWORD = "action"


class SubmitData(SubmitActionData):
    """
    Utility class for creating submit data with action-based routing.

    This class extends the base ``SubmitActionData`` (``microsoft_teams.cards.core.SubmitActionData``)
    with a convenience constructor that accepts an ``action`` identifier, which is used by
    ``@app.on_dialog_submit("action")`` for routing. The base class is a plain data container
    with no routing support.

    Args:
        action: The action identifier that determines which handler processes the submission.
        data: Optional additional data to include with the submission.

    Example:
        >>> submit_data = SubmitData(action="submit_user_form", data={"user_id": "123"})
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
            if data:
                for k, v in data.items():
                    setattr(self, k, v)
            setattr(self, RESERVED_KEYWORD, action)
        else:
            # Otherwise, use standard Pydantic initialization for model_validate
            super().__init__(**kwargs)
