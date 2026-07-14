"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

import logging
from typing import Awaitable, Protocol

from microsoft_teams.common import InterceptorRequestContext, resolve_token
from microsoft_teams.common.http.client_token import StringLike

from ..models.agentic_identity import AgenticIdentity


class AuthProvider(Protocol):
    def token(
        self, *, scope: str | None = None, agentic_identity: AgenticIdentity | None = None
    ) -> str | StringLike | None | Awaitable[str | StringLike | None]: ...


logger = logging.getLogger(__name__)


class AuthProviderInterceptor:
    """Adds an auth-provider token when a request has no Authorization header."""

    def __init__(
        self,
        auth_provider: AuthProvider,
        *,
        default_agentic_identity: AgenticIdentity | None = None,
    ) -> None:
        self._auth_provider = auth_provider
        self._default_agentic_identity = default_agentic_identity

    async def request(self, ctx: InterceptorRequestContext) -> None:
        if "Authorization" in ctx.request.headers:
            return

        token = await resolve_token(lambda: self._auth_provider.token(agentic_identity=self._default_agentic_identity))
        if token is None:
            return

        token = token.strip()
        if not token:
            logger.warning("Auth provider returned an empty token; skipping Authorization header.")
            return

        ctx.request.headers["Authorization"] = f"Bearer {token}"
