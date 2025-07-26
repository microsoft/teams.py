"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Optional, Type, TypeVar

from pydantic import create_model
from pydantic_core import PydanticUndefinedType

from ...models import ActivityBase, CustomBaseModel

T = TypeVar("T", bound=CustomBaseModel)


def input_model(model: Type[T]) -> Type[T]:
    """
    Creates an input model from an activity model, making all ActivityBase fields optional
    except for the 'type' field, while preserving activity-specific field requirements.

    This is used to create input types for activities where:
    - ActivityBase fields become optional (SDK fills them)
    - Activity-specific fields keep their required/optional status
    - 'type' field remains required with its literal value

    Args:
        model: The activity model class to create an input type for

    Returns:
        A new input model class with ActivityBase fields made optional
    """
    base_fields = set(ActivityBase.model_fields.keys())
    curr_fields = model.model_fields.items()
    fields: dict[str, Any] = {}

    for field_name, field_info in curr_fields:
        # Only make ActivityBase fields optional (except 'type')
        if field_name in base_fields and field_name != "type":
            annotation = Optional[field_info.annotation]  # type: ignore
            default = None if isinstance(field_info.default, PydanticUndefinedType) else field_info.default
            fields[field_name] = (annotation, default)
        else:
            fields[field_name] = (field_info.annotation, field_info.default)

    return create_model(
        f"{model.__name__}Input",
        __base__=model,
        __module__=model.__module__,
        **{k: v for k, v in fields.items()},
    )
