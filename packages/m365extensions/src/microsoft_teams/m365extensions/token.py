"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

import time
from typing import Optional

from microsoft_agents.activity import Activity
from microsoft_teams.api.auth.caller import CallerIds, CallerType
from microsoft_teams.api.auth.token import TokenProtocol


class TeamsToken(TokenProtocol):
    """A minimal TokenProtocol synthesized from an Agents SDK Activity."""

    def __init__(
        self,
        *,
        app_id: str,
        tenant_id: Optional[str],
        service_url: str,
        app_display_name: Optional[str] = None,
    ) -> None:
        self._app_id = app_id
        self._tenant_id = tenant_id
        self._service_url = service_url.rstrip("/") if service_url else ""
        self._app_display_name = app_display_name
        # Synthetic expiration ~1h out so is_expired() reports False.
        self._expiration_ms = int(time.time() * 1000) + 60 * 60 * 1000

    @classmethod
    def from_activity(cls, activity: Activity) -> "TeamsToken":
        recipient = getattr(activity, "recipient", None)
        conversation = getattr(activity, "conversation", None)
        return cls(
            app_id=getattr(recipient, "id", "") or "",
            app_display_name=getattr(recipient, "name", None),
            tenant_id=getattr(conversation, "tenant_id", None),
            service_url=getattr(activity, "service_url", "") or "",
        )

    # ── TokenProtocol surface ──────────────────────────────────────────

    @property
    def app_id(self) -> str:
        return self._app_id

    @property
    def app_display_name(self) -> Optional[str]:
        return self._app_display_name

    @property
    def tenant_id(self) -> Optional[str]:
        return self._tenant_id

    @property
    def service_url(self) -> str:
        return self._service_url or "https://smba.trafficmanager.net/teams"

    @property
    def from_(self) -> CallerType:
        return "bot" if self._app_id else "azure"

    @property
    def from_id(self) -> str:
        if self.from_ == "bot":
            return f"{CallerIds.BOT}:{self._app_id}"
        return CallerIds.AZURE

    @property
    def expiration(self) -> Optional[int]:
        return self._expiration_ms

    def is_expired(self, buffer_ms: int = 5 * 60 * 1000) -> bool:
        return self._expiration_ms < (time.time() * 1000) + buffer_ms

    def __str__(self) -> str:
        # No real JWT is forwarded; a tagged sentinel is more honest than '' and
        # cannot be mistaken for a signable bearer.
        return f"teams-sdk-synthetic://app/{self._app_id}"
