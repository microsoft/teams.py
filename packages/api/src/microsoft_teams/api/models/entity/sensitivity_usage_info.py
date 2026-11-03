"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..custom_base_model import CustomBaseModel


class SensitivityUsageInfo(CustomBaseModel):
    """
    Microsoft Purview sensitivity label information.
    Used both as the message-level label on the root message entity and as a citation's usage info.
    """

    at_type: str = "CreativeWork"
    "The schema.org type. Defaults to 'CreativeWork'."

    at_id: str
    """
    The Purview sensitivity label ID, a GUID such as `00000000-0000-0000-0000-000000000000`.
    Teams resolves the label's display name and description from this ID.
    """

    name: Optional[str] = None
    "Display name of the label. Used as a fallback when Teams cannot resolve `at_id`."

    description: Optional[str] = None
    "Description of the label."

    position: Optional[int] = None
    """
    Priority of the label, used to pick the most restrictive label.
    Applies to the message-level label and requires `at_id`.
    """
