"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Optional

from ..custom_base_model import CustomBaseModel


class FileInfoCard(CustomBaseModel):
    """
    File info card.
    """

    unique_id: Optional[str] = None
    "Unique Id for the file."

    file_type: Optional[str] = None
    "Type of file."

    etag: Optional[Any] = None
    "ETag for the file."
