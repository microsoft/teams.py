"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from pydantic import AliasGenerator, BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CustomBaseModel(BaseModel):
    @staticmethod
    def validation_alias_generator(field: str) -> str:
        "Handles deserialization aliasing"

        # Handle parameters that start with "@"
        if field.startswith("at_"):
            return f"@{field[3:]}"

        # Handles from field which is a duplicate reserved internal name
        if field == "from_":
            return "from"

        # All other fields are converted to camelCase
        return to_camel(field)

    @staticmethod
    def serialization_alias_generator(field: str) -> str:
        "Handles serialization aliasing and casing"

        # Handle parameters that start with "@"
        if field.startswith("at_"):
            return f"@{field[3:]}"

        # Handles from field which is a duplicate reserved internal name
        if field == "from_":
            return "from"

        # All other fields are converted to camelCase
        return to_camel(field)

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
        validate_by_alias=True,
        arbitrary_types_allowed=True,
        extra="allow",
        alias_generator=AliasGenerator(
            validation_alias=validation_alias_generator, serialization_alias=serialization_alias_generator
        ),
    )
