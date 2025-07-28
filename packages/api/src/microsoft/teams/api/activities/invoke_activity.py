"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from abc import ABC
from typing import Literal

from ..models import ActivityBase


class InvokeActivity(ActivityBase, ABC):
    """
    Abstract base class for all invoke activities.

    Invoke activities represent operations that expect a response and are used for
    interactive functionality like adaptive cards, messaging extensions, and task modules.
    """

    type: Literal["invoke"] = "invoke"  #
    """The activity type is always 'invoke' for invoke activities."""

    name: str
    """The name of the operation associated with the invoke activity."""
