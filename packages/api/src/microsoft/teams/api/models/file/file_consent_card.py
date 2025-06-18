"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Optional

from ..action import Action
from ..custom_base_model import CustomBaseModel
from .file_upload_info import FileUploadInfo


class FileConsentCard(CustomBaseModel):
    """
    File consent card attachment.
    """

    description: Optional[str] = None
    "File description."

    size_in_bytes: Optional[int] = None
    "Size of the file to be uploaded in Bytes."

    accept_context: Optional[Any] = None
    """
    Context sent back to the Bot if user consented to
    upload. This is free flow schema and is sent back
    in Value field of Activity.
    """

    decline_context: Optional[Any] = None
    """
    Context sent back to the Bot if user declined.
    This is free flow schema and is sent back in Value
    field of Activity.
    """


class FileConsentCardResponse(CustomBaseModel):
    """
    Represents the value of the invoke activity sent when the user acts on a file consent card
    """

    action: Action
    "The action the user took. Possible values include: 'accept', 'decline'"

    context: Optional[Any] = None
    "The context associated with the action."

    upload_info: Optional[FileUploadInfo] = None
    "If the user accepted the file, contains information about the file to be uploaded."
