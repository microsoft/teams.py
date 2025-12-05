"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from abc import ABC
from typing import Literal

from ...models import ActivityBase, CustomBaseModel


class ReadReceiptEventActivity(ActivityBase, CustomBaseModel, ABC):
    """
    Represents a read receipt event activity in Microsoft Teams.
    """

    type: Literal["event"] = "event"  #

    name: Literal["application/vnd.microsoft.readReceipt"] = "application/vnd.microsoft.readReceipt"
    """
    The name of the operation associated with an invoke or event activity.
    """
