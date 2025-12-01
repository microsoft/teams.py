"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.


Backward compatibility shim for microsoft.teams.openai.

DEPRECATED: This import path is deprecated and will be removed in version 2.0.0 GA.
Please update your imports to use 'microsoft_teams.openai' instead.
"""

import sys
import warnings

warnings.warn(
    "The 'microsoft.teams.openai' namespace is deprecated and will be removed in "
    "version 2.0.0 GA. Please update your imports to 'microsoft_teams.openai'.",
    DeprecationWarning,
    stacklevel=2,
)

from microsoft_teams.openai import *  # noqa: E402, F401, F403
from microsoft_teams.openai import __all__  # noqa: E402, F401

_new_module = sys.modules["microsoft_teams.openai"]
sys.modules[__name__] = _new_module
