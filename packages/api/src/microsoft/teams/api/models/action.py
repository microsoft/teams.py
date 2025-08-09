"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

# Actions that can be taken on a file consent card.
Action = (
    Literal[
        "accept",  # User accepted the file upload.
        "decline",  # User declined the file upload.
    ]
    | str
)
