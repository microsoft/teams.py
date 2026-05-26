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
    INVOKE = "invoke"
    SUBMIT = "Action.Submit"
    """Suggested action of type Action.Submit. The action's value is delivered to the bot
    as a suggestedActions/submit invoke without sending a chat-visible message."""
