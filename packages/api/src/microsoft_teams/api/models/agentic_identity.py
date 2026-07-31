"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class AgenticIdentity:
    """Identifies the Agent 365 identity scope used for SDK operations.

    AgenticIdentity is the SDK operation/request scope for the Agent 365
    program. It encompasses an agentic app blueprint, which can instantiate
    agentic apps, and each app can optionally have associated agentic users.
    """

    agentic_app_blueprint_id: str
    agentic_app_id: str | None = None
    agentic_user_id: str | None = None
    tenant_id: str | None = None


__all__ = ["AgenticIdentity"]
