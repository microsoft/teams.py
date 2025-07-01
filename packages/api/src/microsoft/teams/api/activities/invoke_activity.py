"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from abc import ABC, abstractmethod

from ..models.activity import Activity


class InvokeActivity(Activity, ABC):
    """
    Abstract base class for all invoke activities.

    Invoke activities represent operations that expect a response and are used for
    interactive functionality like adaptive cards, messaging extensions, and task modules.
    """

    type: str = "invoke"
    """The activity type is always 'invoke' for invoke activities."""

    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the operation associated with the invoke activity."""
        pass
