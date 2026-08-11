"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..custom_base_model import CustomBaseModel

FILE_DOWNLOAD_INFO_CONTENT_TYPE = "application/vnd.microsoft.teams.file.download.info"
"""
Content type of an inbound uploaded-file attachment.
Its `content` is a `FileDownloadInfo` describing a file fetchable from a short-lived, pre-authorized download URL.
"""


class FileDownloadInfo(CustomBaseModel):
    """
    The content of a `file.download.info` attachment, describing an uploaded file received in a personal (1:1) chat.
    The file is fetched from the short-lived, pre-authorized `download_url` with a plain GET (no bearer token).
    """

    download_url: Optional[str] = None
    "Pre-authorized, short-lived URL the file can be fetched from with a plain GET (no bearer token)."

    unique_id: Optional[str] = None
    "The OneDrive/ODSP drive-item id for the file. This is the storage-specific file identity a Graph fetch keys off."

    file_type: Optional[str] = None
    "Type of file (extension, e.g. `pdf`, `docx`)."

    etag: Optional[str] = None
    """
    A server-assigned version tag identifying this version of the file's contents, for detecting whether the file
    changed between reads. Read-only; populated when Teams provides it with the file.
    """
