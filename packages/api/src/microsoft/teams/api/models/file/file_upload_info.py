"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..custom_base_model import CustomBaseModel


class FileUploadInfo(CustomBaseModel):
    """
    Information about the file to be uploaded.
    """

    name: Optional[str] = None
    "Name of the file."

    upload_url: Optional[str] = None
    "URL to an upload session that the bot can use to set the file contents."

    content_url: Optional[str] = None
    "URL to file."

    unique_id: Optional[str] = None
    "ID that uniquely identifies the file."

    file_type: Optional[str] = None
    "Type of the file."
