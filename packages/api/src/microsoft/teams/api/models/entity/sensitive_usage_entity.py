"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from pydantic import ConfigDict

from ..custom_base_model import CustomBaseModel
from .message_entity import MessageEntity


class SensitiveUsagePattern(CustomBaseModel):
    """Pattern information for sensitive usage"""

    model_config = ConfigDict(
        **CustomBaseModel.model_config,
        extra="allow",
    )

    at_type: Literal["DefinedTerm"] = "DefinedTerm"

    in_defined_term_set: str
    name: str
    term_code: str


class SensitiveUsage(CustomBaseModel):
    """Sensitive usage information"""

    model_config = ConfigDict(
        **CustomBaseModel.model_config,
        extra="allow",
    )

    type: Literal["https://schema.org/Message"] = "https://schema.org/Message"

    at_type: Literal["CreativeWork"]

    name: str
    "Title of the content"

    description: Optional[str] = None
    "Description of the content"

    pattern: Optional[SensitiveUsagePattern] = None
    "The pattern"


class SensitiveUsageEntity(MessageEntity):
    """
    Sensitive usage entity extending MessageEntity
    """

    model_config = ConfigDict(
        **CustomBaseModel.model_config,
        extra="allow",
    )

    usage_info: Optional[SensitiveUsage] = None
    "As part of the usage field"
