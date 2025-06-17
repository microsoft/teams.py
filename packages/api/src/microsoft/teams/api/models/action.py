"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from enum import Enum


class Action(str, Enum):
    """
    Enum for the actions that can be taken on a file consent card.
    """

    ACCEPT = "accept"
    "User accepted the file upload."

    DECLINE = "decline"
    "User declined the file upload."
