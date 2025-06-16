from pydantic import BaseModel


class TokenExchangeInvokeRequest(BaseModel):
    """Placeholder for TokenExchangeInvokeRequest model"""

    pass


# Type alias for AdaptiveCardAuthentication
AdaptiveCardAuthentication = TokenExchangeInvokeRequest
"""
Defines the structure that arrives in the Activity.Value.Authentication
for Invoke activity with Name of 'adaptiveCard/action
"""
