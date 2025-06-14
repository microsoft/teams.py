"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from pydantic import BaseModel


class ConversationResource(BaseModel):
    """A response containing a resource."""

    id: str
    activity_id: str
    service_url: str
