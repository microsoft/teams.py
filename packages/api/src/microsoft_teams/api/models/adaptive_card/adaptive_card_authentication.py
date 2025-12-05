"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from ..token_exchange import TokenExchangeInvokeRequest

# Type alias for AdaptiveCardAuthentication
AdaptiveCardAuthentication = TokenExchangeInvokeRequest
"""
Defines the structure that arrives in the Activity.Value.Authentication
for Invoke activity with Name of 'adaptiveCard/action
"""
