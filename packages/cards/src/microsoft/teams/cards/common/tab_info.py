"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from microsoft.teams.api.models.custom_base_model import CustomBaseModel


class TabInfo(CustomBaseModel):
    content_url: str
    "The URL to open in an iFrame."

    website_url: Optional[str] = None
    "Optional. Website URL to the content, allowing users to open this content in the browser (if they prefer)."

    name: str
    "Name for the content. This will be displayed as the title of the window hosting the iFrame."

    entity_id: str
    " Unique entity id for this content (e.g., random UUID)."
