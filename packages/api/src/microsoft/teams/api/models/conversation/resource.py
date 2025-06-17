"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from pydantic import AliasGenerator, BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ConversationResource(BaseModel):
    """A response containing a resource."""

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    id: str
    """
    Id of the resource.
    """

    activity_id: str
    """
    Id of the Activity (if sent).
    """

    service_url: str
    """
    Service endpoint where operations concerning the conversation may be performed.
    """
