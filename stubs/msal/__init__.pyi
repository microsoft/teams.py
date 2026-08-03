"""Type stubs for msal"""

from typing import Any, Callable, Optional, TypeAlias

ClientCredential: TypeAlias = str | dict[str, str | Callable[[], str] | Callable[[dict[str, Any]], str]] | None

class ConfidentialClientApplication:
    """MSAL Confidential Client Application"""

    def __init__(
        self,
        client_id: str,
        *,
        client_credential: ClientCredential = None,
        authority: str | None = None,
        **kwargs: Any,
    ) -> None: ...
    def acquire_token_for_client(
        self,
        scopes: list[str] | str,
        claims_challenge: str | None = None,
        *,
        fmi_path: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]: ...
    def acquire_token_by_user_federated_identity_credential(
        self,
        scopes: list[str],
        assertion: str | Callable[[], str],
        *,
        username: Optional[str] = None,
        user_object_id: Optional[str] = None,
        claims_challenge: Optional[None] = None,
        **kwargs: Any,
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
        managed_identity: SystemAssignedManagedIdentity | UserAssignedManagedIdentity,
        *,
        http_client: Any,
        token_cache: Any | None = None,
        http_cache: Any | None = None,
        client_capabilities: list[str] | None = None,
    ) -> None: ...
    def acquire_token_for_client(self, *, resource: str, claims_challenge: str | None = None) -> dict[str, Any]: ...
