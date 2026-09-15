"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..custom_base_model import CustomBaseModel


class FileInfoCard(CustomBaseModel):
    """
    File info card.
    """

    unique_id: Optional[str] = None
    "Unique Id for the file."

    file_type: Optional[str] = None
    "Type of file."

    etag: Optional[str] = None
    """
    A server-assigned version tag identifying the uploaded file's contents.
    Populated from the storage service's upload response.
    """
