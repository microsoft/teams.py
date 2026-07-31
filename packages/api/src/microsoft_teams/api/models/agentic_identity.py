"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AgenticIdentity:
    """Identifies the Agent 365 identity scope used for SDK operations.

    AgenticIdentity is the SDK operation/request scope: the agentic program or
    identity used to authenticate proactive/API calls. Today incoming activities
    are user-backed and include ``agentic_user_id``; over time this same scope can
    encompass concrete service concepts such as an Agent 365 app blueprint,
    app-backed identity, or user-backed identity without exposing separate public
    SDK models for each service shape.
    """

    agentic_app_id: str
    agentic_user_id: str | None = None
    tenant_id: str | None = None
    agentic_app_blueprint_id: str | None = None


__all__ = ["AgenticIdentity"]
