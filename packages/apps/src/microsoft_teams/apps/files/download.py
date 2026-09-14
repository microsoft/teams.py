"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import base64
import binascii
import json
import logging
from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Optional, cast

import httpx
from microsoft_teams.api import ConversationType

from .errors import FileAccessError, FileActor, FileCredentialError, FileScopeNotSupportedError, FileUrlExpiredError
from .graph_share import build_drive_item_content_url

logger = logging.getLogger(__name__)

# How much of an error body to keep. Enough for a Graph error envelope, small enough to never matter.
_ERROR_BODY_LIMIT = 2048


@dataclass
class FileFetchTarget:
    """The minimal file description the download dispatcher needs to open a byte stream."""

    scope: ConversationType
    """Conversation scope; the dispatcher is keyed on this."""

    download_url: Optional[str] = None
    """Short-lived, pre-authorized download URL (personal scope)."""

    content_url: Optional[str] = None
    """
    Browsable URL to the item in OneDrive/SharePoint. Used as the Graph sharing locator when no `download_url` is
    present.
    """

    content_type: Optional[str] = None
    """MIME type reported by the incoming file, used as a fallback when the response omits one."""


@dataclass
class GraphCredential:
    """
    Supplies a bearer token for Graph, and names the identity it belongs to.

    Resolved at fetch time rather than stored on the file handle, so a handle stays inert and a token is never
    acquired before it is needed. Returning `None` for the token means no credential is available, which surfaces as
    a `FileCredentialError` before any request is made.

    `base_url_root` is carried here so a new code path cannot wire the token through and forget its destination.
    """

    actor: FileActor
    """Which identity this credential belongs to."""

    token: Callable[[], Awaitable[Optional[str]]]
    """Resolves the bearer token, or `None` when no credential is available."""

    base_url_root: Optional[str] = None
    """Graph host root, e.g. `https://graph.microsoft.com`. The API version is appended at the point of use."""


@dataclass
class OpenedFileStream:
    """A freshly opened, single-consumption byte stream plus the metadata resolved while opening it."""

    chunks: AsyncIterator[bytes]
    """The raw response body stream. Uncapped; the caller bounds it."""

    source_url: str
    """The URL the bytes were actually fetched from."""

    content_type: str
    """MIME type resolved from the response, falling back to the incoming file's."""


@asynccontextmanager
async def open_file_stream(
    target: FileFetchTarget,
    *,
    prior_fetch_succeeded: bool = False,
    client: Optional[httpx.AsyncClient] = None,
    credential: Optional[GraphCredential] = None,
) -> AsyncGenerator[OpenedFileStream]:
    """
    Open a byte stream for an inbound file, keyed on its conversation scope so every scope's receive path extends this
    one place rather than branching in callers.

    Only `personal` is implemented; `groupChat`/`channel` (and any future scope) raise `FileScopeNotSupportedError`
    until their Graph receive path lands.
    """
    if target.scope != "personal":
        raise FileScopeNotSupportedError(target.scope)

    async with _open_personal_file_stream(
        target, prior_fetch_succeeded=prior_fetch_succeeded, client=client, credential=credential
    ) as opened:
        yield opened


async def _send_following_https_redirects(http: httpx.AsyncClient, request: httpx.Request) -> httpx.Response:
    """
    Send a streaming request, following redirects only while they stay on HTTPS.

    Storage answers with a 302 to the host actually holding the bytes, so redirects have to be followed. They must
    not be followed *down* to plaintext: an `https` to `http` hop would put the file on the wire in the clear.
    `follow_redirects=True` would take that hop silently, so the walk is done here instead, one hop at a time.

    Each next request is built by httpx rather than by hand, which keeps its own header rules, including dropping
    `Authorization` when the redirect leaves the origin.

    httpx applies `max_redirects` only when it follows redirects itself, so the ceiling is read off the client
    here. A caller who sets their own limit keeps it.
    """
    response = await http.send(request, stream=True, follow_redirects=False)

    for _ in range(http.max_redirects):
        if not response.is_redirect or response.next_request is None:
            return response

        next_request = response.next_request
        if next_request.url.scheme != "https":
            await response.aclose()
            raise RuntimeError(
                "cannot download file: a redirect destination must use https, got "
                f"'{next_request.url.scheme}://{next_request.url.host}'. "
                "The file's bytes would cross that hop in the clear."
            )

        await response.aclose()
        response = await http.send(next_request, stream=True, follow_redirects=False)

    await response.aclose()
    raise RuntimeError("cannot download file: too many redirects")


@asynccontextmanager
async def _open_personal_file_stream(
    target: FileFetchTarget,
    *,
    prior_fetch_succeeded: bool,
    client: Optional[httpx.AsyncClient],
    credential: Optional[GraphCredential],
) -> AsyncGenerator[OpenedFileStream]:
    url = target.download_url

    # The Agentic User case: a browsable `content_url` arrives in place of a `download_url`, so Graph is the only
    # route to the bytes.
    if not url:
        if not target.content_url:
            raise RuntimeError("cannot download file: no download URL is available")

        async with _open_graph_file_stream(target, target.content_url, client=client, credential=credential) as opened:
            yield opened
        return

    # Unreachable today: the platform's agentic path never sets a download URL, which is the only reason the arm above
    # always fires for an agent. If that ever changes, the bytes still arrive and nothing fails, but they are fetched
    # unauthenticated and attributed to nobody, so the switch away from the agent's own identity would be invisible
    # except in an audit log. Warn rather than reroute: rerouting would ignore a working URL, which is the escalation
    # the automatic-credential rule exists to prevent.
    if credential is not None and credential.actor == "agentic_user":
        logger.warning(
            "an agentic turn received a file carrying a pre-authorized download URL, which the platform did not "
            "previously send to agents. The SDK is using that URL, so these bytes are not attributed to the agentic "
            "user."
        )

    if not url.lower().startswith("https://"):
        raise RuntimeError("cannot download file: download URL must use https")

    owns_client = client is None
    http = client or httpx.AsyncClient()

    try:
        # Plain GET with no bearer token: the download URL embeds its own `tempauth` credential, and attaching a
        # credential can get the request rejected. The shared client is configured with the bot's default headers,
        # so strip `Authorization` off this request rather than assuming the client carries none; otherwise it
        # would be sent to a third-party storage host.
        request = http.build_request("GET", url)
        request.headers.pop("Authorization", None)

        # Redirects are followed, because without it a storage 302 never resolves: it is not 2xx, so it would fall
        # through to the `not response.is_success` arm below and surface as "failed to download file: 302 Found".
        # They are followed one hop at a time so a downgrade to plaintext can be refused.
        response = await _send_following_https_redirects(http, request)

        try:
            if response.status_code in (401, 403):
                # Terminal. The URL carried its own credential and that credential has lapsed, and the SDK does not
                # perform a fallback via app identity or user-delegated permissions on the developer's behalf. The
                # file has to be sent again.
                raise FileUrlExpiredError("reread" if prior_fetch_succeeded else "first_fetch")

            if not response.is_success:
                raise RuntimeError(f"failed to download file: {response.status_code} {response.reason_phrase}".strip())

            content_type = response.headers.get("content-type") or target.content_type or "application/octet-stream"
            yield OpenedFileStream(chunks=response.aiter_bytes(), source_url=url, content_type=content_type)
        finally:
            await response.aclose()
    finally:
        if owns_client:
            await http.aclose()


@asynccontextmanager
async def _open_graph_file_stream(
    target: FileFetchTarget,
    sharing_url: str,
    *,
    client: Optional[httpx.AsyncClient],
    credential: Optional[GraphCredential],
) -> AsyncGenerator[OpenedFileStream]:
    """
    Fetch bytes by resolving the item through Graph's `/shares` endpoint.

    Unlike the pre-authorized path, which strips `Authorization` because the URL carries its own credential, this is
    an ordinary authenticated Graph call and fails without a bearer token.
    """
    actor = credential.actor if credential else None
    token, token_failure = await _try_resolve_token(credential)

    # Detectable before any HTTP call, so a missing consent names itself instead of arriving as an opaque Graph 401.
    if not token or _carries_no_graph_permissions(token):
        raise FileCredentialError(actor, token_failure)

    base_url_root = (credential.base_url_root if credential else None) or "https://graph.microsoft.com"
    url = build_drive_item_content_url(sharing_url, base_url_root)
    logger.debug(f"resolving bytes through Graph /shares as '{actor}'")

    owns_client = client is None
    http = client or httpx.AsyncClient()

    try:
        # Authentication belongs to the branch, never the downloader: the pre-authorized path strips `Authorization`
        # because that URL carries its own credential, this one requires it.
        request = http.build_request("GET", url, headers={"Authorization": f"Bearer {token}"})
        response = await _send_following_https_redirects(http, request)

        try:
            if response.status_code in (401, 403):
                # An unconsented scope, a file never shared with this identity, and a drive item that does not exist
                # are all 403, differing only in message text. The SDK cannot branch on that, but the developer can
                # read it, so it is carried rather than dropped.
                raise FileAccessError(response.status_code, actor, await _read_service_error(response))

            if not response.is_success:
                # Carry Graph's own text and name the identity, as the 401/403 arm does. An unexpected status here is
                # often diagnosable only from the service message, so dropping it leaves a bare status code.
                details = await _read_service_error(response)
                message = (
                    f"failed to download file through Graph as '{actor or 'app'}': "
                    f"{response.status_code} {response.reason_phrase}"
                ).strip()
                raise RuntimeError(f"{message} ({details})" if details else message)

            content_type = response.headers.get("content-type") or target.content_type or "application/octet-stream"
            yield OpenedFileStream(chunks=response.aiter_bytes(), source_url=url, content_type=content_type)
        finally:
            await response.aclose()
    finally:
        if owns_client:
            await http.aclose()


async def _read_service_error(response: httpx.Response) -> Optional[str]:
    """
    Pull the human-readable part out of a Graph error envelope, falling back to the raw text.

    Graph replies `{"error": {"code", "message"}}`, but a 401 can also come from the edge as HTML, so this must not
    assume JSON. Reads at most `_ERROR_BODY_LIMIT` bytes rather than buffering the whole body: this runs on a stream
    the SDK does not size, and the text only ever lands in an exception message. A body large enough to be cut off
    will not parse as JSON, which is fine, because the raw fallback is what a body that shape deserves anyway.
    """
    try:
        collected = bytearray()
        async for chunk in response.aiter_bytes():
            collected.extend(chunk)
            if len(collected) >= _ERROR_BODY_LIMIT:
                break
        raw = bytes(collected[:_ERROR_BODY_LIMIT]).decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001 - diagnostics must never mask the error being raised
        return None

    try:
        envelope: Any = json.loads(raw)
        error = cast(dict[str, Any], envelope).get("error") if isinstance(envelope, dict) else None
        if isinstance(error, dict):
            fields = cast(dict[str, Any], error)
            parts = [str(fields[k]) for k in ("code", "message") if fields.get(k)]
            if parts:
                return _truncate(": ".join(parts))
    except ValueError:
        pass  # Not JSON. The raw text is still better than nothing.

    return _truncate(raw)


def _truncate(text: str) -> Optional[str]:
    collapsed = " ".join(text.split())
    if not collapsed:
        return None
    return collapsed[:_ERROR_BODY_LIMIT] + "..." if len(collapsed) > _ERROR_BODY_LIMIT else collapsed


async def _try_resolve_token(credential: Optional[GraphCredential]) -> tuple[Optional[str], Optional[str]]:
    """
    Resolve a Graph token without raising, returning the token and, when acquisition threw, the reason it did.

    On the expiry path the caller already holds a more precise error, so an acquisition failure must leave it intact
    rather than surfacing as an unrelated exception. The reason is returned rather than only logged because an
    acquisition that threw is not the same as an identity with no permissions, and the guidance differs.
    """
    if credential is None:
        return None, None

    try:
        return await credential.token(), None
    except Exception as err:  # noqa: BLE001 - any acquisition failure degrades to "no token", by design
        failure = str(err)
        logger.debug(f"could not acquire a Graph token: {failure}")
        return None, failure


def _permissions_of(token: str) -> Optional[list[str]]:
    """
    The permissions a token carries, as a flat list, or `None` when the token is not a decodable JWT.

    An app-only token lists application permissions in `roles`; a delegated or agentic-user token lists scopes in
    `scp`, space-delimited and absent entirely when there are none. `None` and `[]` mean different things and both
    callers depend on the difference: undecodable is "cannot tell", empty is "decoded, and there is nothing there".
    Both fail open on `None` rather than blocking a fetch that might have worked.
    """
    try:
        payload = token.split(".")[1]
        decoded = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
        parsed = json.loads(decoded)

        # A JWT payload is an object by definition, but the wire is untrusted: a decodable token whose payload is a
        # list, string or null must read as "cannot tell" rather than raising out of a function documented to fail open.
        if not isinstance(parsed, dict):
            return None

        claims = cast(dict[str, Any], parsed)
        roles_claim = claims.get("roles")
        roles = [r for r in cast(list[Any], roles_claim) if isinstance(r, str)] if isinstance(roles_claim, list) else []
        scp = claims.get("scp")
        scopes = scp.split() if isinstance(scp, str) else []
        return roles + scopes
    except (IndexError, ValueError, binascii.Error, UnicodeDecodeError):
        return None


def _carries_no_graph_permissions(token: str) -> bool:
    """
    Detect a credential that cannot reach a drive item, before spending a request to find out.

    Real Graph answers such a token with a `401 generalException` or a `403`, indistinguishable on the wire from a
    genuine denial but fixed in the identity's consented permissions rather than in file sharing.

    The predicate is "carries no file-capable permission", not "carries none at all". Emptiness was sufficient while
    the app rung was the concern, because an app registration with no Graph permissions really does return
    `roles: []`. It is not sufficient for an Agentic User under `.default`, where a blueprint consented to unrelated
    scopes such as `Mail.Send` returns a populated `scp` that passes an emptiness check and then fails late as an
    ambiguous 403.

    Any `Files.*` or `Sites.*` permission is admitted, deliberately generously. `Sites.Selected` is a known false
    positive: it starts with `Sites.` but grants nothing until an admin allowlists specific sites. A false positive
    degrades to the previous behaviour of calling Graph and reporting what it says, which is the safe direction.

    Fails open on an undecodable token, which proceeds to the call rather than blocking a fetch that might have
    worked.
    """
    permissions = _permissions_of(token)
    if permissions is None:
        return False
    return not any(p.lower().startswith(("files.", "sites.")) for p in permissions)


async def collect_stream(chunks: AsyncIterator[bytes]) -> bytes:
    """Read a byte stream to completion into a single `bytes` object."""
    buffer = bytearray()

    async for chunk in chunks:
        buffer.extend(chunk)

    return bytes(buffer)
