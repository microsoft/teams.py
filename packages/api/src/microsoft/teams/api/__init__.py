"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.


Backward compatibility shim for microsoft.teams.api.

DEPRECATED: This import path is deprecated and will be removed in version 2.0.0 GA.
Please update your imports to use 'microsoft_teams.api' instead.
"""

import sys
import warnings

# Issue deprecation warning
warnings.warn(
    "The 'microsoft.teams.api' namespace is deprecated and will be removed in "
    "version 2.0.0 GA. Please update your imports to 'microsoft_teams.api'.",
    DeprecationWarning,
    stacklevel=2,
)

# Import everything from the new namespace
from microsoft_teams.api import *  # noqa: E402, F401, F403
from microsoft_teams.api import __all__  # noqa: E402, F401

# sys.modules trick to make submodule imports work
# This ensures: from microsoft.teams.api.submodule import X works
_new_module = sys.modules["microsoft_teams.api"]
sys.modules[__name__] = _new_module
