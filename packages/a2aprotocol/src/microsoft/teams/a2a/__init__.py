"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.


Backward compatibility shim for microsoft.teams.a2a.

DEPRECATED: This import path is deprecated and will be removed in version 2.0.0 GA.
Please update your imports to use 'microsoft_teams.a2a' instead.
"""

import sys
import warnings

warnings.warn(
    "The 'microsoft.teams.a2a' namespace is deprecated and will be removed in "
    "version 2.0.0 GA. Please update your imports to 'microsoft_teams.a2a'.",
    DeprecationWarning,
    stacklevel=2,
)

from microsoft_teams.a2a import *  # noqa: E402, F401, F403
from microsoft_teams.a2a import __all__  # noqa: E402, F401

_new_module = sys.modules["microsoft_teams.a2a"]
sys.modules[__name__] = _new_module
