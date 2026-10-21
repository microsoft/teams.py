"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from pydantic import ConfigDict

from ..custom_base_model import CustomBaseModel


class ReplyChainInfo(CustomBaseModel):
    """
    Identifies the reply chain (thread) that an inbound activity belongs to, by the message at the root of the chain.

    This API is in preview and may change in the future.
    Diagnostic: ExperimentalTeamsThreading
    """

    model_config = ConfigDict(frozen=True)

    id: Optional[str] = None
    """
    The id of the message at the root of the reply chain (thread).
    Use it as the reply chain id when replying in a reply chain (e.g. threading).
    """
