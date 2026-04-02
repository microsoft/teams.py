"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Union

MessageReactionType = Union[
    Literal["like", "heart", "1f440_eyes", "2705_whiteheavycheckmark", "launch", "1f4cc_pushpin"], str
]
