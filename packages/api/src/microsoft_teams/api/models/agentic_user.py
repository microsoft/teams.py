"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AgenticUser:
    """Identifies an Agent ID user-shaped identity and its backing agent app."""

    agentic_app_instance_id: str
    agentic_user_id: str
    tenant_id: str | None = None
    agentic_blueprint_id: str | None = None


__all__ = ["AgenticUser"]
