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

    type: Optional[Literal["https://schema.org/Message"]] = None
    """
    .. deprecated::
        Not part of the usageInfo contract.
    """

    at_type: str = "CreativeWork"
    "The schema.org type. Defaults to 'CreativeWork'."

    at_id: Optional[str] = None
    "The Purview sensitivity label ID"

    name: Optional[str] = None
    "Title of the content"

    description: Optional[str] = None
    "Description of the content"

    position: Optional[int] = None
    "Priority of the label, used to pick the most restrictive label."

    pattern: Optional[SensitiveUsagePattern] = None
    "The pattern"


class SensitiveUsageEntity(MessageEntity):
    """
    Sensitive usage entity extending MessageEntity
    """

    usage_info: Optional[SensitiveUsage] = None
    "As part of the usage field"
