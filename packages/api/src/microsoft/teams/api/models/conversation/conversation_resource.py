from pydantic import AliasGenerator, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class ConversationResource(BaseModel):
    """
    A response containing a resource
    """

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    id: str = Field(..., description="Id of the resource")
    activity_id: str = Field(..., description="ID of the Activity (if sent)")
    service_url: str = Field(
        ..., description="Service endpoint where operations concerning the conversation may be performed"
    )
