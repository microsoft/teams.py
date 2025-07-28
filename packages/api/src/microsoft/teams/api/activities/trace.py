"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Literal, Optional

from ..models import ActivityBase, ActivityInputBase, ConversationReference, CustomBaseModel


class _TraceBase(CustomBaseModel):
    """Base class containing shared trace activity fields (all Optional except type)."""

    type: Literal["trace"] = "trace"

    name: Optional[str] = None
    """"
    The name of the operation associated with an invoke or event activity.
    """

    label: Optional[str] = None
    """
    A descriptive label for the activity.
    """

    value_type: Optional[str] = None
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


class TraceActivity(_TraceBase, ActivityBase):
    """Output model for received trace activities with required fields and read-only properties."""

    label: str  # pyright: ignore [reportGeneralTypeIssues]
    """
    A descriptive label for the activity.
    """

    value_type: str  # pyright: ignore [reportGeneralTypeIssues]
    """
    The type of the activity's value object.
    """


class TraceActivityInput(_TraceBase, ActivityInputBase):
    """Input model for creating trace activities with builder methods."""
