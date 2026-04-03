"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# Union of all activity input types (each defined next to their respective activities)
from typing import Annotated, Union

from pydantic import Field

from .message import (
    MessageActivityInput,
    MessageReactionActivityInput,
)
from .typing import TypingActivityInput

ActivityParams = Annotated[
    Union[
        MessageActivityInput,
        MessageReactionActivityInput,
        TypingActivityInput,
    ],
    Field(discriminator="type"),
]
