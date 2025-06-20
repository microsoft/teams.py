"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..custom_base_model import CustomBaseModel


class TabEntityContext(CustomBaseModel):
    """Current TabRequest entity context, or 'tabEntityId'."""

    tab_entity_id: Optional[str] = None
    """The entity id of the tab."""
