"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Microsoft Graph integration for Teams AI Python SDK.

This package provides seamless integration between the Teams AI SDK and Microsoft Graph,
enabling zero-configuration access to Graph APIs with automatic authentication.
"""

from .auth_provider import TeamsContextAuthProvider
from .context_extension import GraphIntegrationError, enable_graph_integration

__all__ = [
    "GraphIntegrationError",
    "TeamsContextAuthProvider",
    "enable_graph_integration",
]

__version__ = "0.1.0"
