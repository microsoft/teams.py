"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Awaitable, Callable

import jwt
from fastapi import HTTPException, Request, Response

from .service_token_validator import ServiceTokenValidator


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
