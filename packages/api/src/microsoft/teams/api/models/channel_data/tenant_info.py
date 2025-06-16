from pydantic import BaseModel, Field


class TenantInfo(BaseModel):
    """
    Describes a tenant
    """

    id: str = Field(..., description="Unique identifier representing a tenant")
