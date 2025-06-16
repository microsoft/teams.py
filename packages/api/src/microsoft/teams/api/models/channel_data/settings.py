from typing import Any

from pydantic import AliasGenerator, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from .channel_info import ChannelInfo


class ChannelDataSettings(BaseModel):
    """
    Settings within teams channel data specific to messages received in Microsoft Teams.
    """

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    selected_channel: ChannelInfo = Field(..., description="Information about the selected Teams channel.")

    class Config:
        """Allow extra fields to be included and preserved."""

        extra = "allow"
        allow_population_by_field_name = True

    def __getitem__(self, key: str) -> Any:
        """Enable dictionary-style access to properties."""
        return self.__dict__[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """Enable dictionary-style setting of properties."""
        self.__dict__[key] = value
