"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ...models import SearchInvokeValue
from ..invoke_activity import InvokeActivity


class SearchInvokeActivity(InvokeActivity):
    """
    Represents an activity that is sent when an Adaptive Card dynamic typeahead
    'Input.ChoiceSet' (via 'choices.data' / 'Data.Query') requests choices.
    """

    type: Literal["invoke"] = "invoke"  #

    name: Literal["application/search"] = "application/search"  #
    """The name of the operation associated with an invoke or event activity."""

    value: SearchInvokeValue
    """A value that is associated with the activity."""
