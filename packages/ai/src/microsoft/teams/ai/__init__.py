"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.


Backward compatibility shim for microsoft.teams.ai.

DEPRECATED: This import path is deprecated and will be removed in version 2.0.0 GA.
Please update your imports to use 'microsoft_teams.ai' instead.
"""

import sys
import warnings

# Issue deprecation warning
warnings.warn(
    "The 'microsoft.teams.ai' namespace is deprecated and will be removed in "
    "version 2.0.0 GA. Please update your imports to 'microsoft_teams.ai'.",
    DeprecationWarning,
    stacklevel=2,
)

# Import everything from the new namespace
from microsoft_teams.ai import *  # noqa: E402, F401, F403
from microsoft_teams.ai import __all__  # noqa: E402, F401

# sys.modules trick to make submodule imports work
# This ensures: from microsoft.teams.ai.submodule import X works
_new_module = sys.modules["microsoft_teams.ai"]
sys.modules[__name__] = _new_module
