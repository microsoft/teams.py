"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ....models import AdaptiveCardInvokeValue
from ...invoke_activity import InvokeActivity


class AdaptiveCardInvokeActivity(InvokeActivity):
    """
    Represents an activity that is sent when an adaptive card action is invoked.
    """

    type: Literal["invoke"] = "invoke"  #

    name: Literal["adaptiveCard/action"] = "adaptiveCard/action"  #
    """The name of the operation associated with an invoke or event activity."""

    value: AdaptiveCardInvokeValue
    """A value that is associated with the activity."""
