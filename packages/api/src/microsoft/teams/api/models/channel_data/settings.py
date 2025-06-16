from typing import Any

from pydantic import BaseModel, Field

from .channel_info import ChannelInfo


class ChannelDataSettings(BaseModel):
    """
    Settings within teams channel data specific to messages received in Microsoft Teams.
    """

    selected_channel: ChannelInfo = Field(
        ..., alias="selectedChannel", description="Information about the selected Teams channel."
    )

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
