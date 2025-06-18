"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from ..custom_base_model import CustomBaseModel


class TokenExchangeInvokeRequest(CustomBaseModel):
    """Placeholder for TokenExchangeInvokeRequest model"""

    pass


# Type alias for AdaptiveCardAuthentication
AdaptiveCardAuthentication = TokenExchangeInvokeRequest
"""
Defines the structure that arrives in the Activity.Value.Authentication
for Invoke activity with Name of 'adaptiveCard/action
"""
