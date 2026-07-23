"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

from typing import Awaitable, Protocol

from microsoft_teams.common.http.client_token import StringLike

from ..models.agentic_user import AgenticUser


class AuthProvider(Protocol):
    def token(
        self, *, scope: str | None = None, agentic_user: AgenticUser | None = None
    ) -> str | StringLike | None | Awaitable[str | StringLike | None]: ...
