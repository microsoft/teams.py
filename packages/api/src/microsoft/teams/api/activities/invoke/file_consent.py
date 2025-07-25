"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from ...models import ConversationReference, FileConsentCardResponse
from ..invoke_activity import InvokeActivity
from ..utils import input_model


class FileConsentInvokeActivity(InvokeActivity):
    """
    File consent invoke activity for fileConsent/invoke invokes.

    Represents an invoke activity when a user acts on a file consent card
    (either accepting or declining file upload).
    """

    name: Literal["fileConsent/invoke"] = "fileConsent/invoke"  # pyright: ignore [reportIncompatibleVariableOverride]
    """The name of the operation associated with an invoke or event activity."""

    value: FileConsentCardResponse
    """A value that is associated with the activity."""

    relates_to: Optional[ConversationReference] = None
    """A reference to another conversation or activity."""


@input_model
class FileConsentInvokeActivityInput(FileConsentInvokeActivity):
    """
    Input type for FileConsentInvokeActivity where ActivityBase fields are optional
    but invoke-specific fields retain their required status.
    """

    pass
