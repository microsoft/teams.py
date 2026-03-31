"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# Union of activity input types that APX actually accepts on outbound send.
# Other *ActivityInput classes exist for model symmetry but are not sendable —
# the Teams service rejects them (messageDelete, messageUpdate, etc.
# are inbound-only event notifications, not outbound activity types).
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
