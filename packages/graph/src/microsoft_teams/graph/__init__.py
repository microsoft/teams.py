"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging

from .auth_provider import AuthProvider
from .graph import get_graph_client

logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = [
    "AuthProvider",
    "get_graph_client",
]
