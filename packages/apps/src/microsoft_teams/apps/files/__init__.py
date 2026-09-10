"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from .downloaded_file import DownloadedFile
from .errors import (
    FileActor,
    FileError,
    FileRetrievalError,
    FileRetrievalFailureReason,
    FileScopeNotSupportedError,
    FileUrlExpiredError,
)
from .files_accessor import FilesAccessor
from .incoming_file import IncomingFile
from .types import FileSource

__all__ = [
    "FileSource",
    "FileActor",
    "FileError",
    "FileRetrievalError",
    "FileRetrievalFailureReason",
    "FileScopeNotSupportedError",
    "FileUrlExpiredError",
    "DownloadedFile",
    "IncomingFile",
    "FilesAccessor",
]
