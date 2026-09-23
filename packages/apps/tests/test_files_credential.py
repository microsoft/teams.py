"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# pyright: basic

from typing import Optional
from unittest.mock import AsyncMock

import pytest
from microsoft_teams.api import AgenticIdentity
from microsoft_teams.apps.files_credential import select_files_credential


class FakeToken:
    """Minimal stand-in for a token; only `str()` is consumed by the credential."""

    def __init__(self, value: str) -> None:
        self._value = value

    def __str__(self) -> str:
        return self._value


AGENTIC = AgenticIdentity(
    agentic_app_blueprint_id="blueprint-1",
    agentic_app_id="agentic-app-1",
    agentic_user_id="agentic-user-1",
    tenant_id="tenant-1",
)


def _selector(
    *,
    agentic_identity: Optional[AgenticIdentity] = None,
    app_token: Optional[FakeToken] = None,
    agentic_token: Optional[FakeToken] = None,
    base_url_root: Optional[str] = None,
):
    get_app = AsyncMock(return_value=app_token)
    get_agentic = AsyncMock(return_value=agentic_token)
    credential = select_files_credential(
        agentic_identity=agentic_identity,
        graph_base_url_root=base_url_root,
        get_app_graph_token=get_app,
        get_agentic_graph_token=get_agentic,
    )
    return credential, get_app, get_agentic


class TestSelectFilesCredential:
    @pytest.mark.asyncio
    async def test_reads_as_the_app_when_there_is_no_agentic_identity(self):
        credential, _, _ = _selector(app_token=FakeToken("app-token"), agentic_token=FakeToken("agentic-token"))

        assert credential.actor == "app"
        assert await credential.token() == "app-token"

    @pytest.mark.asyncio
    async def test_reads_as_the_agentic_user_when_an_agentic_identity_is_present(self):
        # Every other file test supplies a credential directly, so they would all pass even if this branch were
        # inverted, and the failure would look like a consent problem rather than a wrong-identity one.
        credential, _, _ = _selector(
            agentic_identity=AGENTIC,
            app_token=FakeToken("app-token"),
            agentic_token=FakeToken("agentic-token"),
        )

        assert credential.actor == "agentic_user"
        assert await credential.token() == "agentic-token"

    @pytest.mark.asyncio
    async def test_never_falls_back_to_the_app_token_for_an_agentic_identity(self):
        # An app token sees a different set than what was shared with the agent, so a silent fallback would 403 on
        # exactly the agent's own files.
        credential, get_app, _ = _selector(agentic_identity=AGENTIC, app_token=FakeToken("app-token"))

        assert await credential.token() is None
        get_app.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_passes_the_agentic_identity_through_unchanged(self):
        credential, _, get_agentic = _selector(agentic_identity=AGENTIC, agentic_token=FakeToken("agentic-token"))

        await credential.token()

        get_agentic.assert_awaited_once_with(AGENTIC)

    @pytest.mark.asyncio
    async def test_carries_the_graph_host_root_for_both_actors(self):
        # Keeping the token and its destination on one object removes the failure mode where a new code path wires one
        # through and forgets the other.
        app_credential, _, _ = _selector(base_url_root="https://graph.microsoft.us")
        agentic_credential, _, _ = _selector(agentic_identity=AGENTIC, base_url_root="https://graph.microsoft.us")

        assert app_credential.base_url_root == "https://graph.microsoft.us"
        assert agentic_credential.base_url_root == "https://graph.microsoft.us"

    @pytest.mark.asyncio
    async def test_leaves_the_host_root_unset_when_the_cloud_supplies_none(self):
        credential, _, _ = _selector(app_token=FakeToken("app-token"))

        assert credential.base_url_root is None

    @pytest.mark.asyncio
    async def test_acquires_no_token_until_one_is_asked_for(self):
        # A turn that never touches files should never pay for a token.
        _, get_app, get_agentic = _selector(app_token=FakeToken("app-token"))
        _, get_app2, get_agentic2 = _selector(agentic_identity=AGENTIC, agentic_token=FakeToken("agentic-token"))

        get_app.assert_not_awaited()
        get_agentic.assert_not_awaited()
        get_app2.assert_not_awaited()
        get_agentic2.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_reports_no_token_rather_than_raising_when_the_app_has_no_credentials(self):
        # Surfaces downstream as a typed `no_graph_credential` failure before any HTTP call is made.
        credential, _, _ = _selector()

        assert await credential.token() is None
