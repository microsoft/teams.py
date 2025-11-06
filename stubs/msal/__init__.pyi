"""Type stubs for msal"""

from typing import Any

class ConfidentialClientApplication:
    """MSAL Confidential Client Application"""

    def __init__(
        self, client_id: str, *, client_credential: str | None = None, authority: str | None = None, **kwargs: Any
    ) -> None: ...
    def acquire_token_for_client(
        self, scopes: list[str] | str, claims_challenge: str | None = None, **kwargs: Any
    ) -> dict[str, Any]: ...
