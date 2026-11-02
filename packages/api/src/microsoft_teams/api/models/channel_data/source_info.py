"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from pydantic import ConfigDict

from ..custom_base_model import CustomBaseModel


class SourceInfo(CustomBaseModel):
    """
    Describes the source of an activity
    """

    model_config = ConfigDict(frozen=True)

    name: Optional[str] = None
    "Name of the source"
