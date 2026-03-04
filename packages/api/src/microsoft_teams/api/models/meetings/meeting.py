"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..custom_base_model import CustomBaseModel


class Meeting(CustomBaseModel):
    """
    A participant's meeting-specific details, including their
    role and current presence status within the meeting.
    """

    role: Optional[str] = None
    "Meeting role of the user."

    in_meeting: Optional[bool] = None
    "Indicates if the participant is in the meeting."
