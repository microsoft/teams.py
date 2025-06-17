"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from enum import Enum


class CardActionType(str, Enum):
    """Available card action types."""

    OPEN_URL = "openUrl"
    IM_BACK = "imBack"
    POST_BACK = "postBack"
    PLAY_AUDIO = "playAudio"
    PLAY_VIDEO = "playVideo"
    SHOW_IMAGE = "showImage"
    DOWNLOAD_FILE = "downloadFile"
    SIGN_IN = "signin"
    CALL = "call"
