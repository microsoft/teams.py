"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from ...models import ConversationReference, O365ConnectorCardActionQuery
from ..invoke_activity import InvokeActivity
from ..utils import input_model


class ExecuteActionInvokeActivity(InvokeActivity):
    """
    Execute action invoke activity for actionableMessage/executeAction invokes.

    Represents an invoke activity when a user clicks on an action button
    in an O365 connector card message.
    """

    name: Literal["actionableMessage/executeAction"] = "actionableMessage/executeAction"  # pyright: ignore [reportIncompatibleVariableOverride]
    """The name of the operation associated with an invoke or event activity."""

    value: O365ConnectorCardActionQuery
    """A value that is associated with the activity."""

    relates_to: Optional[ConversationReference] = None
    """A reference to another conversation or activity."""


@input_model
class ExecuteActionInvokeActivityInput(ExecuteActionInvokeActivity):
    """
    Input type for ExecuteActionInvokeActivity where ActivityBase fields are optional
    but invoke-specific fields retain their required status.
    """

    pass
