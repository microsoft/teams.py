"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

# Available card action types.
CardActionType = (
    Literal["openUrl", "imBack", "postBack", "playAudio", "playVideo", "showImage", "downloadFile", "signin", "call"]
    | str
)
