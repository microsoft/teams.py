"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from .custom_base_model import CustomBaseModel


class CacheInfo(CustomBaseModel):
    """A cache info object which notifies Teams how long an object should be cached for."""

    cache_type: Optional[str] = None
    """The type of cache for this object."""

    cache_duration: Optional[int] = None
    """The time in seconds for which the cached object should remain in the cache."""
