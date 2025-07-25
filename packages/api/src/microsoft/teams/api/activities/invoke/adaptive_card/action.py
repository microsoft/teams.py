"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ....models import AdaptiveCardInvokeValue
from ...invoke_activity import InvokeActivity
from ...utils import input_model


class AdaptiveCardInvokeActivity(InvokeActivity):
    """
    Represents an activity that is sent when an adaptive card action is invoked.
    """

    type: Literal["invoke"] = "invoke"  # pyright: ignore [reportIncompatibleVariableOverride]

    name: Literal["adaptiveCard/action"] = "adaptiveCard/action"  # pyright: ignore [reportIncompatibleVariableOverride]
    """The name of the operation associated with an invoke or event activity."""

    value: AdaptiveCardInvokeValue
    """A value that is associated with the activity."""


@input_model
class AdaptiveCardInvokeActivityInput(AdaptiveCardInvokeActivity):
    """
    Input type for AdaptiveCardInvokeActivity where ActivityBase fields are optional
    but invoke-specific fields retain their required status.
    """

    pass
