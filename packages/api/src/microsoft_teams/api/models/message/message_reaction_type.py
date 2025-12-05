"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Union

MessageReactionType = Union[Literal["like", "heart", "laugh", "surprised", "sad", "angry", "plusOne"], str]
