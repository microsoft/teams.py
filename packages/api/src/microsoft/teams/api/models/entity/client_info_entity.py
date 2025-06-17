from typing import Literal

from pydantic import ConfigDict

from ..custom_base_model import CustomBaseModel


class ClientInfoEntity(CustomBaseModel):
    """Client information entity"""

    model_config = ConfigDict(
        **CustomBaseModel.model_config,
        extra="allow",
    )

    type: Literal["clientInfo"] = "clientInfo"
    "Type identifier for client info"

    locale: str
    "Client locale (ex en-US)"

    country: str
    "Client country code (ex US)"

    platform: str
    "Client platform (ex Web)"

    timezone: str
    "Client timezone (ex America/New_York)"
