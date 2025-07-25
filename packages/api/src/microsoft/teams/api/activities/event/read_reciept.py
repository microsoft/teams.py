"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from abc import ABC
from typing import Literal

from ...models import ActivityBase, CustomBaseModel
from ..utils import input_model


class ReadReceiptEventActivity(ActivityBase, CustomBaseModel, ABC):
    """
    Represents a read receipt event activity in Microsoft Teams.
    """

    type: Literal["event"] = "event"  # pyright: ignore [reportIncompatibleVariableOverride]

    name: Literal["application/vnd.microsoft.readReceipt"] = "application/vnd.microsoft.readReceipt"
    """
    The name of the operation associated with an invoke or event activity.
    """


@input_model
class ReadReceiptEventActivityInput(ReadReceiptEventActivity):
    """
    Input type for ReadReceiptEventActivity where ActivityBase fields are optional
    but event-specific fields retain their required status.
    """

    pass
