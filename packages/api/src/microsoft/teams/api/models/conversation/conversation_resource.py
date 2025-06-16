from pydantic import BaseModel, Field


class ConversationResource(BaseModel):
    """
    A response containing a resource
    """

    id: str = Field(..., description="Id of the resource")
    activity_id: str = Field(..., description="ID of the Activity (if sent)", alias="activityId")
    service_url: str = Field(
        ...,
        description="Service endpoint where operations concerning the conversation may be performed",
        alias="serviceUrl",
    )
