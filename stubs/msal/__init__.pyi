"""Type stubs for msal"""

from typing import Any, Optional

class ConfidentialClientApplication:
    """MSAL Confidential Client Application"""

    def __init__(
        self, client_id: str, *, client_credential: Optional[str] = None, authority: Optional[str] = None, **kwargs: Any
    ) -> None: ...
    def acquire_token_for_client(
        self, scopes: list[str] | str, claims_challenge: Optional[str] = None, **kwargs: Any
    ) -> dict[str, Any]: ...
