"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

from typing import Awaitable, Protocol

from microsoft_teams.common.http.client_token import StringLike

from ..models.agent_user import AgentUser


class AuthProvider(Protocol):
    def token(
        self, *, scope: str | None = None, agent_user: AgentUser | None = None
    ) -> str | StringLike | None | Awaitable[str | StringLike | None]: ...
