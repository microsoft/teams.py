"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

MessageReactionType = (
    Literal[
        "like",
        "heart",
        "laugh",
        "surprised",
        "sad",
        "angry",
        "plusOne",
    ]
    | str
)
