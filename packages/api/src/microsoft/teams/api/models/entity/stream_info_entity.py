"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from ..custom_base_model import CustomBaseModel


class StreamInfoEntity(CustomBaseModel):
    """Entity containing streaming information"""

    type: Literal["streaminfo"] = "streaminfo"
    "Type identifier for stream info"

    stream_id: Optional[str] = None
    "ID of the stream. Assigned after the initial update is sent."

    stream_type: Optional[Literal["informative", "streaming", "final"]] = None
    """
        The type of message being sent.
        'informative' - An informative update.
        'streaming' - A chunk of partial message text.
        'final' - The final message.
    """

    stream_sequence: Optional[int] = None
    "Sequence number of the message in the stream. Starts at 1 for the first message and increments from there."
