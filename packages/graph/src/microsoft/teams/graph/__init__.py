"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Backward compatibility shim for microsoft.teams.graph.


DEPRECATED: This import path is deprecated and will be removed in version 2.0.0 GA.
Please update your imports to use 'microsoft_teams.graph' instead.
"""

import sys
import warnings

warnings.warn(
    "The 'microsoft.teams.graph' namespace is deprecated and will be removed in "
    "version 2.0.0 GA. Please update your imports to 'microsoft_teams.graph'.",
    DeprecationWarning,
    stacklevel=2,
)

from microsoft_teams.graph import *  # noqa: E402, F401, F403  # noqa: F401, F403
from microsoft_teams.graph import __all__  # noqa: E402, F401

_new_module = sys.modules["microsoft_teams.graph"]
sys.modules[__name__] = _new_module
