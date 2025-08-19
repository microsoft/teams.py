"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from .auth_provider import DirectTokenCredential
from .graph import get_graph_client

__all__ = [
    "DirectTokenCredential",
    "get_graph_client",
]
