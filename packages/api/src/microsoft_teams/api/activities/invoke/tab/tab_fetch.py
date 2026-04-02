"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ....models import TabRequest
from ...invoke_activity import InvokeActivity


class TabFetchInvokeActivity(InvokeActivity):
    """
    Tab fetch invoke activity for tab/fetch invokes.

    Represents an invoke activity when a tab needs to fetch content
    or configuration for display.
    """

    name: Literal["tab/fetch"] = "tab/fetch"  #
    """The name of the operation associated with an invoke or event activity."""

    value: TabRequest
    """A value that is associated with the activity."""
