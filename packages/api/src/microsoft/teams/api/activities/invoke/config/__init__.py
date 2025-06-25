"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from .config_fetch import ConfigFetchInvokeActivity
from .config_submit import ConfigSubmitInvokeActivity

ConfigInvokeActivity = ConfigFetchInvokeActivity | ConfigSubmitInvokeActivity

__all__ = ["ConfigFetchInvokeActivity", "ConfigSubmitInvokeActivity", "ConfigInvokeActivity"]
