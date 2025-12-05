"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.


Backward compatibility shim for microsoft.teams.devtools.

DEPRECATED: This import path is deprecated and will be removed in version 2.0.0 GA.
Please update your imports to use 'microsoft_teams.devtools' instead.
"""

import sys
import warnings

warnings.warn(
    "The 'microsoft.teams.devtools' namespace is deprecated and will be removed in "
    "version 2.0.0 GA. Please update your imports to 'microsoft_teams.devtools'.",
    DeprecationWarning,
    stacklevel=2,
)

from microsoft_teams.devtools import *  # noqa: E402, F401, F403
from microsoft_teams.devtools import __all__  # noqa: E402, F401

_new_module = sys.modules["microsoft_teams.devtools"]
sys.modules[__name__] = _new_module
