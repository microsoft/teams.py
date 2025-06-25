"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ....models import AdaptiveCardInvokeValue, CustomBaseModel
from ...activity import IActivity


class AdaptiveCardActionInvokeActivity(IActivity[Literal["invoke"]], CustomBaseModel):
    """
    Represents an activity that is sent when an adaptive card action is invoked.
    """

    name: Literal["adaptiveCard/action"] = "adaptiveCard/action"
    """The name of the operation associated with an invoke or event activity."""

    value: AdaptiveCardInvokeValue
    """A value that is associated wtih the activity."""
