"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict

from ..core import SubmitActionData, TaskFetchSubmitActionData

RESERVED_KEYWORD = "dialog_id"


class OpenDialogData(SubmitActionData):
    """
    Represents the data required to open a dialog in Microsoft Teams using a submit action.

    This class extends `SubmitActionData` and is used to construct the payload for opening a dialog,
    including a reserved dialog identifier and any additional data.

    Example:
        >>> data = OpenDialogData("myDialogId", {"foo": "bar"})
        >>> # Use `data` as the payload for a Teams card submit action to open a dialog.

    Args:
        dialog_identifier (str): The unique identifier for the dialog to open.
        extra_data (Dict[str, Any] | None): Optional additional data to include in the payload.
    """

    def __init__(self, dialog_identifier: str, extra_data: Dict[str, Any] | None = None):
        """
        Initialize an OpenDialogData instance.

        Args:
            dialog_identifier (str): The unique identifier for the dialog to open.
            extra_data (Dict[str, Any] | None): Optional additional data to include in the payload.
        """
        super().__init__()
        self.with_ms_teams(TaskFetchSubmitActionData().model_dump())
        if extra_data:
            data = {**extra_data}
        else:
            data = {}
        data[RESERVED_KEYWORD] = dialog_identifier
        self.with_data(data)
