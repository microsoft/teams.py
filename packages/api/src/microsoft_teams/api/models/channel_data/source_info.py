"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from pydantic import ConfigDict

from ..custom_base_model import CustomBaseModel


class SourceInfo(CustomBaseModel):
    """
    Describes where an activity was fired or invoked from.

    `name` is `message` for an activity fired from a message (a card button or feedback), and `compose` for one
    fired from a compose extension.

    This API is in preview and may change in the future.
    Diagnostic: ExperimentalTeamsThreading
    """

    model_config = ConfigDict(frozen=True)

    name: Optional[str] = None
    "The name of the source, for example `message` or `compose`."
