from pydantic import AliasGenerator, BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CustomBaseModel(BaseModel):
    @staticmethod
    def validation_alias_generator(field: str) -> str:
        "Handles deserialization aliasing"
        if field.startswith("at_"):
            return f"@{field[3:]}"
        if field == "from_":  # duplicate internal names
            return "from"
        return to_camel(field)

    @staticmethod
    def serialization_alias_generator(field: str) -> str:
        "Handles serialization aliasing and casing"
        if field.startswith("at_"):
            return f"@{field[3:]}"
        if field == "from_":  # duplicate internal names
            return "from"
        return to_camel(field)

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
        validate_by_alias=True,
        alias_generator=AliasGenerator(
            validation_alias=validation_alias_generator, serialization_alias=serialization_alias_generator
        ),
    )
