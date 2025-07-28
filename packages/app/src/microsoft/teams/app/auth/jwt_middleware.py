"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Awaitable, Callable, Optional

import jwt
from fastapi import FastAPI, HTTPException, Request, Response
from microsoft.teams.api import TokenProtocol
from microsoft.teams.common.logging import ConsoleLogger
from starlette.middleware.base import BaseHTTPMiddleware

from .service_token_validator import ServiceTokenValidator


class FakeToken(TokenProtocol):
    """Fake token for development/testing when no app_id is provided."""

    def __init__(self, service_url: str = ""):
        self._service_url = service_url

    @property
    def app_id(self) -> str:
        return ""

    @property
    def app_display_name(self) -> Optional[str]:
        return None

    @property
    def tenant_id(self) -> Optional[str]:
        return None

    @property
    def service_url(self) -> str:
        return self._service_url

    @property
    def from_(self) -> str:
        return "azure"

    @property
    def from_id(self) -> str:
        return ""

    @property
    def expiration(self) -> Optional[int]:
        return None

    def is_expired(self, buffer_ms: int = 5 * 60 * 1000) -> bool:
        return False

    def __str__(self) -> str:
        return "FakeToken"


class JwtValidationMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for JWT token validation."""

    def __init__(self, app: FastAPI, app_id: Optional[str] = None, logger: Optional[Any] = None):
        super().__init__(app)
        self.logger = logger or ConsoleLogger().create_logger("jwt-validation-middleware")

        # Create service token validator if app_id is provided
        if app_id:
            self.token_validator = ServiceTokenValidator(app_id, self.logger)
        else:
            self.logger.debug("No app_id provided, skipping service token validation")
            self.token_validator = None

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Process request through JWT validation middleware."""

        # Only validate /api/messages route
        if request.url.path != "/api/messages":
            return await call_next(request)

        # Extract Bearer token
        authorization = request.headers.get("authorization")
        if not authorization or not authorization.startswith("Bearer "):
            self.logger.warning("Unauthorized request - missing or invalid authorization header")
            raise HTTPException(status_code=401, detail="unauthorized")

        raw_token = authorization.removeprefix("Bearer ")

        if not self.token_validator:
            self.logger.debug("No service token validator configured, skipping validation")
            # Add fake token to request state for development
            request.state.validated_token = FakeToken()
            return await call_next(request)

        try:
            # Parse request body to get service URL for validation
            body = await request.json()
            service_url = body.get("serviceUrl")

            # Validate token
            validated_token = await self.token_validator.validate_token(raw_token, service_url)

            self.logger.debug(f"Validated service token for activity {body.get('id', 'unknown')}")

            # Store validated token in request state
            request.state.validated_token = validated_token

            return await call_next(request)

        except jwt.InvalidTokenError as e:
            self.logger.warning(f"JWT token validation failed: {e}")
            raise HTTPException(status_code=401, detail="unauthorized") from e
        except Exception as e:
            self.logger.error(f"Unexpected error during token validation: {e}")
            raise HTTPException(status_code=500, detail="internal server error") from e


def create_jwt_validation_middleware(
    app_id: str,
    logger: Any,
    paths: list[str],
):
    """
    Create JWT validation middleware instance.

    Args:
        app_id: Bot's Microsoft App ID for audience validation
        logger: Logger instance
        paths: List of paths to validate

    Returns:
        Middleware function that can be added to FastAPI app
    """
    # Create service token validator
    token_validator = ServiceTokenValidator(app_id, logger)

    async def middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """JWT validation middleware function."""
        # Only validate specified paths
        if request.url.path not in paths:
            return await call_next(request)

        # Extract Bearer token
        authorization = request.headers.get("authorization")
        if not authorization or not authorization.startswith("Bearer "):
            logger.warning("Unauthorized request - missing or invalid authorization header")
            raise HTTPException(status_code=401, detail="unauthorized")

        raw_token = authorization.removeprefix("Bearer ")

        try:
            # Parse request body to get service URL for validation
            body = await request.json()
            service_url = body.get("serviceUrl")

            # Validate token
            validated_token = await token_validator.validate_token(raw_token, service_url)

            logger.debug(f"Validated service token for activity {body.get('id', 'unknown')}")

            # Store validated token in request state
            request.state.validated_token = validated_token

            return await call_next(request)

        except jwt.InvalidTokenError as e:
            logger.warning(f"JWT token validation failed: {e}")
            raise HTTPException(status_code=401, detail="unauthorized") from e
        except Exception as e:
            logger.error(f"Unexpected error during token validation: {e}")
            raise HTTPException(status_code=500, detail="internal server error") from e

    return middleware
