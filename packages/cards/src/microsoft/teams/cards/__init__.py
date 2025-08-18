"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from . import common
from .adaptive_card import AdaptiveCard
from .common import *  # noqa: F403

# Combine all exports from submodules
__all__: list[str] = ["AdaptiveCard"]
__all__.extend(common.__all__)
# __all__.extend(actions.__all__)
