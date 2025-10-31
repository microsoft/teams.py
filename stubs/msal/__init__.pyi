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

class SystemAssignedManagedIdentity:
    """MSAL System Assigned Managed Identity"""

    def __init__(self) -> None: ...

class UserAssignedManagedIdentity:
    """MSAL User Assigned Managed Identity"""

    def __init__(self, *, client_id: str) -> None: ...

class ManagedIdentityClient:
    """MSAL Managed Identity Client"""

    def __init__(
        self,
        managed_identity: SystemAssignedManagedIdentity | UserAssignedManagedIdentity | dict[str, Any],
        *,
        http_client: Any,
        token_cache: Optional[Any] = None,
        http_cache: Optional[Any] = None,
        client_capabilities: Optional[list[str]] = None,
    ) -> None: ...
    def acquire_token_for_client(self, *, resource: str, claims_challenge: Optional[str] = None) -> dict[str, Any]: ...
