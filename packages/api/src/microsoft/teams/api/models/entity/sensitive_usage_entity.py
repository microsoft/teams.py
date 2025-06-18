"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from ..custom_base_model import CustomBaseModel
from .message_entity import MessageEntity


class SensitiveUsagePattern(CustomBaseModel):
    """Pattern information for sensitive usage"""

    at_type: Literal["DefinedTerm"] = "DefinedTerm"

    in_defined_term_set: str
    name: str
    term_code: str


class SensitiveUsage(CustomBaseModel):
    """Sensitive usage information"""

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

    usage_info: Optional[SensitiveUsage] = None
    "As part of the usage field"
