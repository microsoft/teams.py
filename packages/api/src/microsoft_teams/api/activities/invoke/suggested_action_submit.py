"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Literal, Optional

from microsoft_teams.common.experimental import experimental

from ..invoke_activity import InvokeActivity


@experimental("ExperimentalTeamsSuggestedAction")
class SuggestedActionSubmitInvokeActivity(InvokeActivity):
    """
    Sent when the user clicks a suggested action of type Action.Submit.

    The structured payload authored on the suggested action is delivered via value.
    """

    name: Literal["suggestedActions/submit"] = "suggestedActions/submit"
    """The name of the invoke operation."""

    value: Optional[Any] = None
    """The structured value from the suggested action."""
