"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any

from .custom_base_model import CustomBaseModel


class InnerHttpError(CustomBaseModel):
    """Object representing inner http error."""

    status_code: int
    """HttpStatusCode from failed request."""

    body: Any
    """Body from failed request."""


class HttpError(CustomBaseModel):
    """Object representing error information."""

    code: str
    """Error code."""

    message: str
    """Error message."""

    inner_http_error: InnerHttpError
    """Error from inner http call."""


class ErrorResponse(CustomBaseModel):
    """An HTTP API response."""

    error: HttpError
    """Error message."""
