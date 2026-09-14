"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# pyright: basic

import base64
import json
import logging
from typing import List, Optional

import httpx
import pytest
from microsoft_teams.apps.files.download import (
    FileFetchTarget,
    GraphCredential,
    open_file_stream,
)
from microsoft_teams.apps.files.errors import FileAccessError, FileActor, FileCredentialError, FileUrlExpiredError
from microsoft_teams.apps.files.graph_share import encode_sharing_url

CONTENT_URL = "https://contoso.sharepoint.com/personal/a/Documents/report.pdf"
DOWNLOAD_URL = "https://contoso.sharepoint.com/personal/a/_layouts/15/download.aspx?UniqueId=1"


def _jwt(claims: dict) -> str:
    """Build a decodable JWT carrying the given claims. Only the payload segment is ever read."""

    def seg(obj: dict) -> str:
        raw = base64.urlsafe_b64encode(json.dumps(obj).encode()).decode()
        return raw.rstrip("=")

    return f"{seg({'alg': 'RS256'})}.{seg(claims)}.sig"


APP_JWT = _jwt({"roles": ["Files.Read.All"]})
AGENTIC_JWT = _jwt({"scp": "profile openid Files.Read.All"})


class _Recorder:
    """Records every request the dispatcher makes, so a route's request count is observable rather than inferred."""

    def __init__(self, statuses: List[int], error_body: Optional[str] = None) -> None:
        self._statuses = statuses
        self._error_body = error_body
        self._i = 0
        self.calls: List[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        status = self._statuses[min(self._i, len(self._statuses) - 1)]
        self._i += 1
        if status == 200:
            return httpx.Response(200, content=b"bytes", headers={"content-type": "application/pdf"})
        if self._error_body is not None:
            return httpx.Response(status, content=self._error_body.encode())
        return httpx.Response(status, json={"error": {"code": "err"}})

    @property
    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(self.handler))

    def client_with(self, **kwargs: object) -> httpx.AsyncClient:
        """A client carrying extra configuration, so a test can prove the SDK strips what the client would add."""
        return httpx.AsyncClient(transport=httpx.MockTransport(self.handler), **kwargs)  # type: ignore[arg-type]

    def auth_of(self, index: int) -> Optional[str]:
        return self.calls[index].headers.get("Authorization")


def _resolve_to(token: Optional[str]):
    async def resolve() -> Optional[str]:
        return token

    return resolve


def _credential(actor: FileActor = "app", token: Optional[str] = APP_JWT) -> GraphCredential:
    async def resolve() -> Optional[str]:
        return token

    return GraphCredential(actor=actor, token=resolve)


def _target(**over) -> FileFetchTarget:
    return FileFetchTarget(scope=over.pop("scope", "personal"), **over)


class TestGraphSharePath:
    @pytest.mark.asyncio
    async def test_resolves_bytes_through_shares_when_no_download_url_is_present(self):
        rec = _Recorder([200])

        async with open_file_stream(
            _target(content_url=CONTENT_URL), client=rec.client, credential=_credential("agentic_user", AGENTIC_JWT)
        ) as opened:
            assert opened.content_type == "application/pdf"

        assert len(rec.calls) == 1
        assert f"/shares/{encode_sharing_url(CONTENT_URL)}/driveItem/content" in str(rec.calls[0].url)

    @pytest.mark.asyncio
    async def test_never_sends_authorization_on_the_preauth_path(self):
        # This URL carries its own credential and points at third-party storage, so a bot token must not ride along.
        rec = _Recorder([200])

        async with open_file_stream(
            _target(download_url=DOWNLOAD_URL, content_url=CONTENT_URL), client=rec.client, credential=_credential()
        ):
            pass

        assert str(rec.calls[0].url) == DOWNLOAD_URL
        assert rec.auth_of(0) is None

    @pytest.mark.asyncio
    async def test_uses_the_agentic_credential_when_one_is_supplied(self):
        rec = _Recorder([200])

        async with open_file_stream(
            _target(content_url=CONTENT_URL), client=rec.client, credential=_credential("agentic_user", AGENTIC_JWT)
        ):
            pass

        assert rec.auth_of(0) == f"Bearer {AGENTIC_JWT}"

    @pytest.mark.asyncio
    async def test_reports_no_graph_credential_before_any_request(self):
        rec = _Recorder([200])

        with pytest.raises(FileCredentialError) as err:
            async with open_file_stream(_target(content_url=CONTENT_URL), client=rec.client):
                pass

        assert err.value.actor is None
        # And the message must not name one either. Defaulting to "the app" here would hand the reader the app
        # remedy, which is wrong guidance for a failure where no identity was ever selected.
        assert "no identity had been selected" in str(err.value)
        assert "the app has no usable Graph credential" not in str(err.value)
        assert len(rec.calls) == 0

    @pytest.mark.asyncio
    async def test_carries_the_acquisition_failure_as_details_when_the_credential_raises(self):
        # An acquisition that raised and an identity with no permissions both arrive here as "no token", but the
        # fixes differ: one is a transient or configuration fault, the other is a consent problem. The canned
        # guidance names consent, so without the cause a transient Entra failure reads as a permissions problem.
        rec = _Recorder([200])

        async def raises() -> Optional[str]:
            raise RuntimeError("AADSTS7000215: Invalid client secret provided.")

        throwing = GraphCredential(actor="agentic_user", token=raises)

        with pytest.raises(FileCredentialError) as err:
            async with open_file_stream(_target(content_url=CONTENT_URL), client=rec.client, credential=throwing):
                pass

        assert err.value.actor == "agentic_user"
        assert err.value.cause == "AADSTS7000215: Invalid client secret provided."
        assert len(rec.calls) == 0

    @pytest.mark.asyncio
    async def test_reports_no_graph_credential_for_a_token_with_no_roles_or_scopes(self):
        # Verified against real Graph: such a token returns 401 generalException, indistinguishable on the wire from
        # a genuine denial but with a completely different fix.
        rec = _Recorder([200])
        roleless = _jwt({"aud": "https://graph.microsoft.com", "roles": []})

        with pytest.raises(FileCredentialError) as err:
            async with open_file_stream(
                _target(content_url=CONTENT_URL), client=rec.client, credential=_credential(token=roleless)
            ):
                pass

        assert err.value.actor == "app"
        assert len(rec.calls) == 0

    @pytest.mark.asyncio
    async def test_reports_no_graph_credential_for_a_token_whose_scopes_are_all_non_file(self):
        # The case `.default` creates and an emptiness check misses. A blueprint consented to unrelated Graph
        # permissions returns a POPULATED scp with nothing file-capable in it, so "carries any permission at all"
        # passes and the developer gets a late 403 that is indistinguishable from "not shared with you".
        rec = _Recorder([200])
        unrelated = _jwt({"scp": "profile openid email Mail.Send Chat.ReadWrite User.Read.All"})

        with pytest.raises(FileCredentialError) as err:
            async with open_file_stream(
                _target(content_url=CONTENT_URL),
                client=rec.client,
                credential=_credential("agentic_user", unrelated),
            ):
                pass

        assert err.value.actor == "agentic_user"
        assert len(rec.calls) == 0

    @pytest.mark.asyncio
    async def test_proceeds_when_a_delegated_token_carries_a_file_capable_scope(self):
        # The shape the live blueprint issues: `.default` returns eleven scopes, of which only
        # Files.ReadWrite.All and Sites.Read.All are file-capable.
        rec = _Recorder([200])
        capable = _jwt({"scp": "profile openid email Mail.Send Files.ReadWrite.All Sites.Read.All"})

        async with open_file_stream(
            _target(content_url=CONTENT_URL), client=rec.client, credential=_credential("agentic_user", capable)
        ):
            pass

        assert len(rec.calls) == 1

    @pytest.mark.asyncio
    async def test_leaves_an_app_with_unrelated_graph_consent_on_its_existing_expiry_error(self):
        # The regression this guards: every app now carries an app credential, so merely resolving a token is not
        # evidence the app opted into file access. A bot that consented to, say, User.Read.All for its own reasons
        # must not be pulled onto the Graph path and handed a different error type than it has always seen.
        rec = _Recorder([401])
        unrelated = _credential(token=_jwt({"roles": ["User.Read.All"]}))

        with pytest.raises(FileUrlExpiredError):
            async with open_file_stream(
                _target(download_url=DOWNLOAD_URL, content_url=CONTENT_URL), client=rec.client, credential=unrelated
            ):
                pass

        # One call, not two: nothing is attempted after the URL lapses.
        assert len(rec.calls) == 1

    @pytest.mark.asyncio
    async def test_keeps_what_the_service_actually_said_on_a_denial(self):
        # A `403` covers an unconsented scope, a never-shared file and a missing drive item alike,
        # because the SDK cannot tell them apart. The service can, and says so in prose, so dropping
        # that text would destroy the only signal that distinguishes them.
        rec = _Recorder(
            [403],
            error_body='{"error":{"code":"accessDenied","message":"The caller does not have permission"}}',
        )

        with pytest.raises(FileAccessError) as err:
            async with open_file_stream(
                _target(content_url=CONTENT_URL), client=rec.client, credential=_credential("agentic_user", AGENTIC_JWT)
            ):
                pass

        assert err.value.status == 403
        assert err.value.details == "accessDenied: The caller does not have permission"
        assert "service said: accessDenied: The caller does not have permission" in str(err.value)

    @pytest.mark.asyncio
    async def test_falls_back_to_raw_text_when_the_service_does_not_reply_with_a_graph_envelope(self):
        # A 401 can come from the edge as HTML rather than Graph JSON, so the parser must not assume an envelope.
        rec = _Recorder([401], error_body="<html><body>Access Denied</body></html>")

        with pytest.raises(FileAccessError) as err:
            async with open_file_stream(
                _target(content_url=CONTENT_URL), client=rec.client, credential=_credential("agentic_user", AGENTIC_JWT)
            ):
                pass

        assert err.value.details == "<html><body>Access Denied</body></html>"

    @pytest.mark.asyncio
    async def test_points_each_actor_at_the_remedy_that_actually_applies_to_it(self):
        # An agent identity gets Graph scopes from its blueprint, so that arm links the agent permission model. The
        # app arm deliberately has no doc link: no permission grant would change the outcome, so pointing at a
        # permissions doc would advise a fix that does not work.
        rec = _Recorder([200, 200])

        with pytest.raises(FileCredentialError) as agentic_err:
            async with open_file_stream(
                _target(content_url=CONTENT_URL),
                client=rec.client,
                credential=_credential("agentic_user", None),
            ):
                pass

        with pytest.raises(FileCredentialError) as app_err:
            async with open_file_stream(
                _target(content_url=CONTENT_URL), client=rec.client, credential=_credential("app", None)
            ):
                pass

        assert "learn.microsoft.com/entra/agent-id" in str(agentic_err.value)
        assert "not supported via the SDK" in str(app_err.value)

    @pytest.mark.asyncio
    async def test_fails_open_on_a_token_that_is_not_a_decodable_jwt(self):
        # An unexpected token shape must not block a fetch that might have worked.
        rec = _Recorder([200])

        async with open_file_stream(
            _target(content_url=CONTENT_URL), client=rec.client, credential=_credential(token="not-a-jwt")
        ):
            pass

        assert len(rec.calls) == 1

    @pytest.mark.asyncio
    async def test_maps_403_to_an_access_failure_naming_the_actor(self):
        rec = _Recorder([403])

        with pytest.raises(FileAccessError) as err:
            async with open_file_stream(
                _target(content_url=CONTENT_URL), client=rec.client, credential=_credential("agentic_user", AGENTIC_JWT)
            ):
                pass

        assert err.value.status == 403
        assert err.value.actor == "agentic_user"

    @pytest.mark.asyncio
    async def test_names_the_identity_and_carries_the_service_message_on_an_unmapped_status(self):
        # A status outside 401/403 is not a typed reason, so the only diagnosis a caller gets is what the service
        # said and who was refused. An identity with no provisioned drive is the case that makes this matter,
        # because Graph answers the drive lookup rather than the sharing token and the message is the only tell.
        rec = _Recorder(
            [404],
            error_body='{"error": {"code": "ResourceNotFound", "message": "Unable to retrieve user\'s mysite URL."}}',
        )

        with pytest.raises(RuntimeError) as err:
            async with open_file_stream(
                _target(content_url=CONTENT_URL), client=rec.client, credential=_credential("agentic_user", AGENTIC_JWT)
            ):
                pass

        assert "agentic_user" in str(err.value)
        assert "404" in str(err.value)
        assert "mysite" in str(err.value)


class TestExpiredUrl:
    @pytest.mark.asyncio
    async def test_an_expired_url_is_terminal(self):
        rec = _Recorder([401])

        with pytest.raises(FileUrlExpiredError):
            async with open_file_stream(
                _target(download_url=DOWNLOAD_URL), client=rec.client, credential=_credential()
            ):
                pass

    @pytest.mark.asyncio
    async def test_raises_file_url_expired_when_the_app_never_adopted_graph(self):
        # The realistic shape of an existing bot: it has credentials and a content_url. What it lacks is a consented
        # Graph permission. Reporting access-denied would name a consent
        # this app never asked for and stop matching any existing `except FileUrlExpiredError`.
        rec = _Recorder([401])

        with pytest.raises(FileUrlExpiredError):
            async with open_file_stream(
                _target(download_url=DOWNLOAD_URL, content_url=CONTENT_URL),
                client=rec.client,
                credential=_credential(token=None),
            ):
                pass

        assert len(rec.calls) == 1

    @pytest.mark.asyncio
    async def test_raises_file_url_expired_when_acquiring_the_token_fails_outright(self):
        # An Entra or network failure during acquisition must not overwrite the more specific error the caller
        # already holds.
        rec = _Recorder([401])

        async def broken() -> Optional[str]:
            raise RuntimeError("AADSTS50034: tenant unreachable")

        with pytest.raises(FileUrlExpiredError):
            async with open_file_stream(
                _target(download_url=DOWNLOAD_URL, content_url=CONTENT_URL),
                client=rec.client,
                credential=GraphCredential(actor="app", token=broken),
            ):
                pass


class _RedirectRecorder:
    """Serves a 302 to `location` on the first call and bytes on the second, recording both hops."""

    def __init__(self, location: str) -> None:
        self._location = location
        self.calls: List[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        if len(self.calls) == 1:
            return httpx.Response(302, headers={"location": self._location})
        return httpx.Response(200, content=b"bytes", headers={"content-type": "application/pdf"})

    def client(self, **kwargs: object) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(self.handler), **kwargs)  # type: ignore[arg-type]

    def auth_of(self, index: int) -> Optional[str]:
        return self.calls[index].headers.get("Authorization")


class _AlwaysRedirectRecorder:
    """Serves a 302 to a fresh https location on every call, recording each hop."""

    def __init__(self) -> None:
        self.calls: List[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        return httpx.Response(302, headers={"location": f"https://storage.example/hop/{len(self.calls)}"})

    def client(self, **kwargs: object) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(self.handler), **kwargs)  # type: ignore[arg-type]


class TestRedirects:
    """
    Graph answers `/shares/.../content` with a 302 to ODSP storage and httpx follows it inside one call, so the
    bearer's survival across that hop is decided by httpx rather than by anything the SDK writes. These pin it.
    """

    @pytest.mark.asyncio
    async def test_does_not_forward_the_bearer_to_the_storage_host(self):
        rec = _RedirectRecorder("https://contoso.sharepoint.com/blob/1")

        async with open_file_stream(
            _target(content_url=CONTENT_URL), client=rec.client(), credential=_credential("agentic_user", AGENTIC_JWT)
        ):
            pass

        assert len(rec.calls) == 2
        assert rec.auth_of(0) == f"Bearer {AGENTIC_JWT}"
        assert rec.auth_of(1) is None

    @pytest.mark.asyncio
    async def test_the_preauth_path_follows_a_redirect(self):
        # httpx defaults follow_redirects to False, so the pre-authorized path has to opt in explicitly. TypeScript
        # (fetch, which defaults to "follow") and .NET (HttpClientHandler.AllowAutoRedirect, which defaults to true)
        # both follow without being asked, and this path used to be the one place across the three SDKs that did not.
        # Losing the flag does not hand the caller a redirect body: a 302 is not 2xx, so it would fall through to the
        # `not response.is_success` arm and surface as "failed to download file: 302 Found", which reads like a
        # server fault rather than a missing client option.
        #
        # Nothing is withheld across the hop on purpose here, unlike the cross-origin bearer case above: this request
        # carries no Authorization header at all, because the pre-authorized URL embeds its own credential.
        rec = _RedirectRecorder("https://contoso.sharepoint.com/blob/1")

        async with open_file_stream(
            _target(download_url=DOWNLOAD_URL), client=rec.client(), credential=_credential()
        ) as opened:
            body = b"".join([chunk async for chunk in opened.chunks])

        assert body == b"bytes"

        # Two hops, not one: the redirect was followed rather than surfacing as an error.
        assert len(rec.calls) == 2

    @pytest.mark.asyncio
    async def test_still_sends_the_bearer_when_the_redirect_stays_on_the_same_origin(self):
        # Without this the assertion above would also pass if the header were dropped unconditionally, which would
        # prove nothing about cross-origin behaviour.
        rec = _RedirectRecorder("https://graph.microsoft.com/v1.0/drives/d/items/i/content")

        async with open_file_stream(
            _target(content_url=CONTENT_URL), client=rec.client(), credential=_credential("agentic_user", AGENTIC_JWT)
        ):
            pass

        assert len(rec.calls) == 2
        assert rec.auth_of(1) == f"Bearer {AGENTIC_JWT}"


class TestSharedClientCredentials:
    @pytest.mark.asyncio
    async def test_strips_a_client_default_authorization_on_the_preauth_path(self):
        # The shared bot client carries default headers, so suppressing only the per-request token would still send
        # the bot's credential to third-party storage. Asserting against a client that has none proves nothing.
        rec = _Recorder([200])

        async with open_file_stream(
            _target(download_url=DOWNLOAD_URL, content_url=CONTENT_URL),
            client=rec.client_with(headers={"Authorization": "Bearer shared-client-secret"}),
            credential=_credential(),
        ):
            pass

        assert rec.auth_of(0) is None


class TestSovereignHost:
    @pytest.mark.asyncio
    async def test_requests_the_configured_graph_host_rather_than_the_public_one(self):
        # The builder is unit-tested elsewhere; this pins that the configured root actually reaches the wire.
        rec = _Recorder([200])
        credential = GraphCredential(
            actor="app", token=_resolve_to(APP_JWT), base_url_root="https://graph.microsoft.us"
        )

        async with open_file_stream(_target(content_url=CONTENT_URL), client=rec.client, credential=credential):
            pass

        assert str(rec.calls[0].url).startswith("https://graph.microsoft.us/")
        assert "graph.microsoft.com" not in str(rec.calls[0].url)


class TestAgenticTurnCarryingAPreauthUrl:
    """
    Guards an identity switch that cannot happen yet.

    The agentic credential is reached only through the "no download_url" arm, and that arm fires for every agent solely
    because the platform does not send agents a download_url. If that changes, the bytes still arrive and nothing
    raises, but they are fetched unauthenticated, so the only trace of the identity switch is in someone's audit log.
    These tests are the only thing keeping the warning alive, since no real activity can reach the branch.
    """

    @pytest.mark.asyncio
    async def test_warns_that_the_bytes_are_not_attributed_to_the_agentic_user(self, caplog):
        rec = _Recorder([200])

        with caplog.at_level(logging.WARNING, logger="microsoft_teams.apps.files.download"):
            async with open_file_stream(
                _target(download_url=DOWNLOAD_URL, content_url=CONTENT_URL),
                client=rec.client,
                credential=_credential("agentic_user", AGENTIC_JWT),
            ):
                pass

        warnings = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warnings) == 1
        assert "not attributed to the agentic user" in warnings[0]

    @pytest.mark.asyncio
    async def test_stays_silent_for_the_app_credential(self, caplog):
        rec = _Recorder([200])

        with caplog.at_level(logging.WARNING, logger="microsoft_teams.apps.files.download"):
            async with open_file_stream(
                _target(download_url=DOWNLOAD_URL, content_url=CONTENT_URL),
                client=rec.client,
                credential=_credential(),
            ):
                pass

        assert [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING] == []


class TestErrorBodyBounding:
    @pytest.mark.asyncio
    async def test_reads_at_most_the_limit_rather_than_buffering_the_whole_error_body(self):
        # The bound has to apply to what is READ, not only to the message that comes out. A service can answer a
        # failed download with an arbitrarily large body, and this runs on a stream the SDK never sized.
        served = 0

        async def body():
            nonlocal served
            for _ in range(64):
                served += 4096
                yield b"x" * 4096

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(403, content=body())

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

        with pytest.raises(FileAccessError) as err:
            async with open_file_stream(
                _target(content_url=CONTENT_URL), client=client, credential=_credential(token=AGENTIC_JWT)
            ):
                pass

        assert err.value.status == 403
        assert served <= 4096 * 2, f"read {served} bytes for a bounded diagnostic"
        assert err.value.details is not None
        assert len(err.value.details) <= 2048 + 3


class TestStatusIsNotCollapsed:
    """A 401 and a 403 have different remedies, so the status is carried rather than folded into one reason."""

    @pytest.mark.asyncio
    async def test_keeps_401_distinguishable_from_403(self):
        rec = _Recorder([401])

        with pytest.raises(FileAccessError) as err:
            async with open_file_stream(
                _target(content_url=CONTENT_URL), client=rec.client, credential=_credential("agentic_user", AGENTIC_JWT)
            ):
                pass

        assert err.value.status == 401
        assert "rejected" in str(err.value)
        assert "never have been shared" not in str(err.value)


class TestRedirectSafety:
    """
    Storage answers with a 302 to the host actually holding the bytes, so redirects must be followed. They must not
    be followed down to plaintext, which would put the file on the wire in the clear.
    """

    @pytest.mark.asyncio
    async def test_refuses_a_redirect_that_downgrades_to_plaintext_http(self):
        rec = _RedirectRecorder("http://storage.example/bytes")

        with pytest.raises(RuntimeError, match="must use https"):
            async with open_file_stream(_target(download_url=DOWNLOAD_URL), client=rec.client()):
                pass

        # The downgraded hop must never be requested, not merely discarded after the fact.
        assert len(rec.calls) == 1

    @pytest.mark.asyncio
    async def test_follows_a_redirect_that_stays_on_https(self):
        # The ordinary storage 302. The guard cannot simply refuse every redirect.
        rec = _RedirectRecorder("https://storage.example/bytes")

        async with open_file_stream(_target(download_url=DOWNLOAD_URL), client=rec.client()) as opened:
            chunks = [chunk async for chunk in opened.chunks]

        assert b"".join(chunks) == b"bytes"
        assert len(rec.calls) == 2

    @pytest.mark.asyncio
    async def test_stops_at_the_clients_redirect_ceiling(self):
        rec = _AlwaysRedirectRecorder()
        client = rec.client()

        with pytest.raises(RuntimeError, match="too many redirects"):
            async with open_file_stream(_target(download_url=DOWNLOAD_URL), client=client):
                pass

        # httpx's default, which is the ceiling a caller gets when they configure nothing.
        assert client.max_redirects == 20
        assert len(rec.calls) == 1 + client.max_redirects

    @pytest.mark.asyncio
    async def test_honours_a_ceiling_the_caller_configured(self):
        # Without this the assertion above would also pass against a hardcoded 20.
        rec = _AlwaysRedirectRecorder()
        client = rec.client(max_redirects=2)

        with pytest.raises(RuntimeError, match="too many redirects"):
            async with open_file_stream(_target(download_url=DOWNLOAD_URL), client=client):
                pass

        assert len(rec.calls) == 3
