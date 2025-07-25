"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from abc import ABC
from typing import Any, Literal, Optional

from ..models import ActivityBase, ConversationReference, CustomBaseModel
from .utils import input_model


class TraceActivity(ActivityBase, CustomBaseModel, ABC):
    type: Literal["trace"] = "trace"  # pyright: ignore [reportIncompatibleVariableOverride]

    name: Optional[str] = None
    """"
    The name of the operation associated with an invoke or event activity.
    """

    label: str
    """
    A descriptive label for the activity.
    """

    value_type: str
    """
    The type of the activity's value object.
    """

    value: Optional[Any] = None
    """
    A value that is associated with the activity.
    """

    relates_to: Optional[ConversationReference] = None
    """
    A reference to another conversation or activity.
    """


@input_model
class TraceActivityInput(TraceActivity):
    """
    Input type for TraceActivity where ActivityBase fields are optional
    but trace-specific fields retain their required status.
    """

    pass
