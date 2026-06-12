"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentUserIdentity:
    """Identifies an Agent ID user-shaped identity and its backing agent app."""

    id: str
    agent_identity_app_id: str
    tenant_id: str


__all__ = ["AgentUserIdentity"]
