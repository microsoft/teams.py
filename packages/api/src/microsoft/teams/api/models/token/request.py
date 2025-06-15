"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict

from pydantic import AliasGenerator, BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class TokenRequest(BaseModel):
    """A request to receive a user token."""

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    provider: str
    """
    The provider to request a user token from.
    """
    settings: Dict[str, Any]
    """
    A collection of settings for the specific provider for this request.
    """
