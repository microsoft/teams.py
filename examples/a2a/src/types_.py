"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


def _alias(name: str) -> str:
    """Camel-case a field name, stripping a trailing underscore first (e.g. ``from_`` → ``from``)."""
    return to_camel(name.rstrip("_"))


class HandoffMessage(BaseModel):
    """Payload carried in an A2A DataPart when one bot hands a user off to the other.

    The receiver uses aadObjectId + tenantId + serviceUrl to open a 1:1 with the
    user and message them proactively.
    """

    model_config = ConfigDict(alias_generator=_alias, populate_by_name=True)

    kind: Literal["handoff"] = "handoff"
    from_: str
    user_name: str
    aad_object_id: str
    tenant_id: str
    service_url: str
    summary: str


class TurnIdentity(BaseModel):
    """Identity captured from one inbound Teams activity, scoped to one agent turn."""

    aad_object_id: str
    user_name: str
    tenant_id: str
    service_url: str


class Config(BaseModel):
    """Per-bot static configuration read from environment variables at startup."""

    name: str
    description: str
    self_url: str
    peer_name: str
    peer_url: str
