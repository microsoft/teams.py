"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict

from ..core import SubmitActionData, TaskFetchSubmitActionData

RESERVED_KEYWORD = "dialog_id"


class OpenDialogData(SubmitActionData):
    def __init__(self, dialog_identifier: str, extra_data: Dict[str, Any] | None = None):
        super().__init__()
        self.with_ms_teams(TaskFetchSubmitActionData().model_dump())
        if extra_data:
            data = {**extra_data}
        else:
            data = {}
        data[RESERVED_KEYWORD] = dialog_identifier
        self.with_data(data)
