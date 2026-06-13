"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AgenticIdentity:
    """Identifies an Agent ID user-shaped identity and its backing agent app."""

    agentic_app_id: str
    agentic_user_id: str
    tenant_id: str | None = None
    agentic_app_blueprint_id: str | None = None

    @property
    def channel_account_id(self) -> str:
        return self.agentic_user_id if self.agentic_user_id.startswith("8:") else f"8:orgid:{self.agentic_user_id}"


__all__ = ["AgenticIdentity"]
