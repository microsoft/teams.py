"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from pydantic import ConfigDict

from ..custom_base_model import CustomBaseModel


class ConversationResource(CustomBaseModel):
    """
    A response containing a resource
    """

    model_config = ConfigDict(
        **CustomBaseModel.model_config,
        extra="allow",
    )

    id: str
    "Id of the resource"

    activity_id: str
    "ID of the Activity (if sent)"

    service_url: str
    "Service endpoint where operations concerning the conversation may be performed"
