"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from ..custom_base_model import CustomBaseModel


class ConversationResource(CustomBaseModel):
    """
    A response containing a resource
    """

    id: str
    "Id of the resource"

    activity_id: str
    "ID of the Activity (if sent)"

    service_url: str
    "Service endpoint where operations concerning the conversation may be performed"
