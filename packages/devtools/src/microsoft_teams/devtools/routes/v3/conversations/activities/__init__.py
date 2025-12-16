"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from .create import create
from .router import get_router as activities_router

__all__ = ["create", "activities_router"]
