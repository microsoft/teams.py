"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from abc import ABC, abstractmethod
from logging import Logger
from typing import Awaitable, Callable, Dict, Optional

from microsoft.teams.api import JsonWebToken, TokenProtocol


class GraphTokenProvider(ABC):
    """Abstract base class for Graph token providers."""

    @abstractmethod
    async def get_token(self, tenant_id: Optional[str] = None) -> Optional[TokenProtocol]:
        """Get a Graph token for the specified tenant."""
        pass

    @abstractmethod
    async def refresh_token(self, tenant_id: Optional[str] = None) -> Optional[TokenProtocol]:
        """Refresh a Graph token for the specified tenant."""
        pass


class DefaultGraphTokenProvider(GraphTokenProvider):
    """Default Graph token provider that uses static tokens."""

    def __init__(self, default_token: Optional[TokenProtocol] = None, allowed_tenant_id: Optional[str] = None):
        self._default_token = default_token
        self._allowed_tenant_id = allowed_tenant_id

    async def get_token(self, tenant_id: Optional[str] = None) -> Optional[TokenProtocol]:
        """Get the default token. Validates tenant_id if configured."""
        if self._allowed_tenant_id is not None and tenant_id != self._allowed_tenant_id:
            raise ValueError(f"Static token only valid for tenant '{self._allowed_tenant_id}', requested '{tenant_id}'")
        return self._default_token

    async def refresh_token(self, tenant_id: Optional[str] = None) -> Optional[TokenProtocol]:
        """Return the default token (no refresh capability). Validates tenant_id if configured."""
        if self._allowed_tenant_id is not None and tenant_id != self._allowed_tenant_id:
            raise ValueError(f"Static token only valid for tenant '{self._allowed_tenant_id}', requested '{tenant_id}'")
        return self._default_token


class CallbackGraphTokenProvider(GraphTokenProvider):
    """Graph token provider that uses a callback function for token refresh."""

    def __init__(
        self, refresh_callback: Callable[[Optional[str]], Awaitable[Optional[str]]], logger: Optional[Logger] = None
    ):
        self._refresh_callback = refresh_callback
        self._logger = logger
        self._cached_tokens: Dict[Optional[str], TokenProtocol] = {}

    async def get_token(self, tenant_id: Optional[str] = None) -> Optional[TokenProtocol]:
        """Get cached token or refresh if needed."""
        cached_token = self._cached_tokens.get(tenant_id)
        if cached_token and not cached_token.is_expired():
            return cached_token

        return await self.refresh_token(tenant_id)

    async def refresh_token(self, tenant_id: Optional[str] = None) -> Optional[TokenProtocol]:
        """Refresh token using the callback."""
        try:
            token_string = await self._refresh_callback(tenant_id)
            if token_string:
                token = JsonWebToken(token_string)
                self._cached_tokens[tenant_id] = token
                return token
            return None
        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to refresh graph token for tenant {tenant_id}: {e}")
            # Return cached token as fallback
            return self._cached_tokens.get(tenant_id)


class GraphTokenManager:
    """Manages Graph API tokens with support for different providers."""

    def __init__(self, provider: Optional[GraphTokenProvider] = None, logger: Optional[Logger] = None):
        self._provider = provider or DefaultGraphTokenProvider()
        self._logger = logger

    def set_provider(self, provider: GraphTokenProvider) -> None:
        """Set the token provider."""
        self._provider = provider

    async def get_token(self, tenant_id: Optional[str] = None) -> Optional[TokenProtocol]:
        """Get a Graph token for the specified tenant."""
        try:
            return await self._provider.get_token(tenant_id)
        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to get graph token: {e}")
            return None

    async def refresh_token(self, tenant_id: Optional[str] = None) -> Optional[TokenProtocol]:
        """Refresh a Graph token for the specified tenant."""
        try:
            return await self._provider.refresh_token(tenant_id)
        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to refresh graph token: {e}")
            return None

    @classmethod
    def create_with_callback(
        cls, refresh_callback: Callable[[Optional[str]], Awaitable[Optional[str]]], logger: Optional[Logger] = None
    ) -> "GraphTokenManager":
        """Create a GraphTokenManager with a callback-based provider."""
        provider = CallbackGraphTokenProvider(refresh_callback, logger)
        return cls(provider, logger)

    @classmethod
    def create_with_static_token(
        cls,
        token: Optional[TokenProtocol] = None,
        logger: Optional[Logger] = None,
        allowed_tenant_id: Optional[str] = None,
    ) -> "GraphTokenManager":
        """Create a GraphTokenManager with a static token provider.

        Args:
            token: The static token to use
            logger: Optional logger
            allowed_tenant_id: If provided, restricts token usage to this tenant only
        """
        provider = DefaultGraphTokenProvider(token, allowed_tenant_id)
        return cls(provider, logger)
