"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..custom_base_model import CustomBaseModel


class Meeting(CustomBaseModel):
    """
    Meeting details.
    """

    role: Optional[str] = None
    "Meeting role of the user."

    in_meeting: Optional[bool] = None
    "Indicates if the participant is in the meeting."
