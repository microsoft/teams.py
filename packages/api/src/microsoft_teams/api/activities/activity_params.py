"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# Union of activity input types that can be sent via the
# /v3/conversations/{id}/activities create/update endpoints.
# Other *ActivityInput classes exist for model symmetry but represent
# inbound-only event notifications (messageDelete, messageUpdate, etc.).
# NOTE: MessageReactionActivityInput is temporarily included here even
# though reactions have a dedicated /activities/{id}/reactions endpoint
# exposed via ReactionClient.
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
