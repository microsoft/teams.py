"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional, assert_never

from microsoft_teams.api import ConversationType

FileUrlExpiredReason = Literal["first_fetch", "reread"]

FileRetrievalFailureReason = Literal["no_graph_credential", "access_denied"]
"""
Why a file's bytes could not be retrieved. See `FileRetrievalError`.

- `no_graph_credential`: no credential was available for the Graph call. Detectable before any HTTP request.
- `access_denied`: the identity used was refused by the storage service. Covers an unconsented scope, a file the
  identity was never granted, and a drive item that does not exist, which are indistinguishable on the wire: Graph
  answers all three with `403`, because telling an unauthorized caller whether a resource exists would disclose it.
"""

FileActor = Literal["app", "agentic_user"]
"""
The identity a file fetch was attempted as. Reported on `FileRetrievalError` so a failure names who was refused.
"""


class FileError(Exception):
    """
    Base class for the diagnosable failures on the inbound-file path: an expired URL, an unsupported scope, and a
    refused Graph read.

    Lets a caller catch those with one `except` clause, so a new one can be added without callers changing. A
    transport or service failure the SDK cannot attribute, such as a Graph 5xx, is not one of these and surfaces as
    a plain `RuntimeError`.
    """


class FileUrlExpiredError(FileError):
    """
    Raised when an inbound file's short-lived download URL has expired and can no longer fetch bytes.

    A personal file's pre-authorized `tempauth` download URL is valid only briefly.
    A fetch after it lapses gets a `401`/`403` from the platform. A handler that downloads once (and does not keep the
    handle) should not hit this.
    `reason` distinguishes the two cases:
    - `first_fetch`: the first fetch came after the URL lapsed, so no bytes were retrieved. There is no recovery: the
      URL carried its own credential, and the SDK does not fall back to Graph with an app identity. The file has to be
      sent again.
    - `reread`: edge case. An earlier download succeeded, then a later re-fetch through the same handle lapsed. Avoid it
      by calling `download()` once and reusing the returned `DownloadedFile` rather than re-reading the handle.
    """

    reason: FileUrlExpiredReason
    """
    Lets callers branch without string-matching the message.
    `first_fetch`: no bytes were ever fetched.
    `reread`: the uncommon case, a previously successful handle re-fetched too late.
    """

    def __init__(self, reason: FileUrlExpiredReason, message: Optional[str] = None) -> None:
        if message is None:
            message = (
                "file download URL expired before any bytes were fetched. The URL is short-lived and cannot be "
                "renewed, so the file has to be sent again. Download on arrival rather than holding the handle."
                if reason == "first_fetch"
                else "file download URL expired before a repeat read; reuse a single DownloadedFile from one "
                "download() call instead of re-reading the handle"
            )
        super().__init__(message)
        self.reason = reason


class FileScopeNotSupportedError(FileError):
    """
    Raised when file bytes are requested for a conversation scope whose download path is not implemented.

    Only `personal` (1:1) uploaded files download directly.
    `groupChat` files are surfaced by `list()`, but fetching their bytes needs Graph;
    `download()`/`stream()` throws until that path lands.
    """

    scope: ConversationType
    """The conversation scope that is not yet fetchable."""

    def __init__(self, scope: ConversationType, message: Optional[str] = None) -> None:
        if message is None:
            message = f"downloading files from '{scope}' conversations is not supported via SDK at this time"
        super().__init__(message)
        self.scope = scope


class FileRetrievalError(FileError):
    """
    Raised when a file's bytes could not be retrieved through Microsoft Graph.

    Distinct from `FileUrlExpiredError`, which means a pre-authorized URL lapsed and no usable Graph route existed.
    This error means a Graph fetch was attempted and did not produce bytes.
    """

    reason: FileRetrievalFailureReason
    """Lets callers branch without string-matching the message."""

    actor: Optional[FileActor]
    """The identity the fetch was attempted as, when one was selected. `None` when the failure preceded selection."""

    details: Optional[str]
    """
    What the storage service itself said, verbatim and truncated, when it said anything.

    `reason` deliberately collapses causes that are indistinguishable to the SDK: an unconsented scope and a file that
    was never shared both arrive as 403. That collapse is right for branching and wrong for diagnosis, so the original
    text is kept here rather than discarded.
    """

    def __init__(
        self,
        reason: FileRetrievalFailureReason,
        actor: Optional[FileActor] = None,
        details: Optional[str] = None,
    ) -> None:
        message = _default_retrieval_message(reason, actor)
        if details:
            message = f"{message} (service said: {details})"
        super().__init__(message)
        self.reason = reason
        self.actor = actor
        self.details = details


def _describe_actor(actor: FileActor) -> str:
    """
    Name the identity in prose. Exhaustive on purpose: a new `FileActor` must fail type checking here rather than
    silently inherit the app's wording, which would send that identity's failures to the wrong remedy.
    """
    if actor == "agentic_user":
        return "the agentic user"
    if actor == "app":
        return "the app"
    assert_never(actor)


def _no_credential_guidance(actor: FileActor) -> str:
    """Where to go to fix a missing credential, which differs per identity. Exhaustive for the same reason."""
    if actor == "agentic_user":
        # Linked rather than described because the agent permission model is still moving, and stale instructions in
        # an error message are worse than none.
        return (
            "the agentic user has no usable Graph permissions. An agent identity gets Graph scopes from its "
            "blueprint's inheritable permissions or from a direct grant, and an administrator must consent to them. "
            "See https://learn.microsoft.com/entra/agent-id/concept-inheritable-permissions"
        )
    if actor == "app":
        # Not a route the SDK takes on its own: Graph file reads happen as the agentic user. An app reaching here
        # means a file arrived in a shape that should not occur, so the remedy is not a permission grant.
        return (
            "the app has no usable Graph credential for this file. Graph file retrieval is supported for Agentic "
            "Users, which read as their own identity; an app identity and/or user-delegated permissions may be "
            "used but are not supported via the SDK at this time"
        )
    assert_never(actor)


def _default_retrieval_message(reason: FileRetrievalFailureReason, actor: Optional[FileActor]) -> str:
    as_who = _describe_actor(actor or "app")

    if reason == "no_graph_credential":
        return f"cannot fetch file bytes through Graph: {_no_credential_guidance(actor or 'app')}"
    if reason == "access_denied":
        return (
            f"cannot fetch file bytes through Graph: access was denied for {as_who}. The required scope may not be "
            "consented, the file may never have been shared with that identity, or the drive item may not exist"
        )
    assert_never(reason)
