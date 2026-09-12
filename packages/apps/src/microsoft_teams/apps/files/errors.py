"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional, assert_never

from microsoft_teams.api import ConversationType

FileUrlExpiredReason = Literal["first_fetch", "reread"]

FileActor = Literal["app", "agentic_user"]
"""
The identity a file fetch was attempted as. Reported on `FileCredentialError` and `FileAccessError` so a failure
names who was refused.
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


class FileCredentialError(FileError):
    """
    Raised when no credential was available for the Graph call. Detectable before any HTTP request.

    Distinct from `FileUrlExpiredError`, which means a pre-authorized URL lapsed and no usable Graph route existed.
    This error means the Graph route was ruled out before the request, because no usable credential was available:
    either a token could not be acquired, or the one acquired carries no file-capable permission.
    """

    actor: Optional[FileActor]
    """The identity the fetch was attempted as, when one was selected. `None` when the failure preceded selection."""

    cause: Optional[str]
    """
    What went wrong while acquiring the token, when the attempt failed rather than simply returning nothing.

    An acquisition that raised and an identity with no permissions both arrive here as "no token", but the fixes
    differ: one is a transient or configuration fault, the other is a consent problem. Local to this process;
    contrast `FileAccessError.details`, which is the service's own words.
    """

    def __init__(self, actor: Optional[FileActor] = None, cause: Optional[str] = None) -> None:
        message = f"cannot fetch file bytes through Graph: {_no_credential_guidance(actor)}"
        if cause:
            message = f"{message} ({cause})"
        super().__init__(message)
        self.actor = actor
        self.cause = cause


class FileAccessError(FileError):
    """
    Raised when the identity used was refused by the storage service.

    Distinct from `FileUrlExpiredError`, which means a pre-authorized URL lapsed and no usable Graph route existed.
    This error means the Graph route was the one that failed, refused by the service after the request was made.
    """

    status: int
    """
    Lets callers branch without string-matching the message. `401` means the token itself was rejected; `403` means
    the identity lacks the grant, and the two have different remedies.
    """

    actor: Optional[FileActor]
    """The identity the fetch was attempted as, when one was selected. `None` when the failure preceded selection."""

    details: Optional[str]
    """
    What the storage service itself said, verbatim and truncated, when it said anything.

    A `403` covers an unconsented scope, a file the identity was never granted, and a drive item that does not exist,
    which are indistinguishable on the wire: Graph answers all three with `403`, because telling an unauthorized
    caller whether a resource exists would disclose it. That collapse is right for branching and wrong for diagnosis,
    so the original text is kept here rather than discarded.
    """

    def __init__(
        self,
        status: int,
        actor: Optional[FileActor] = None,
        details: Optional[str] = None,
    ) -> None:
        message = f"cannot fetch file bytes through Graph: {_access_guidance(status, actor)}"
        if details:
            message = f"{message} (service said: {details})"
        super().__init__(message)
        self.status = status
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


def _no_credential_guidance(actor: Optional[FileActor]) -> str:
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
        # Graph file reads happen as the agentic user. Granting the app file permissions would make this succeed,
        # which is why the message says it may be used rather than that it cannot.
        return (
            "the app has no usable Graph credential for this file. Graph file retrieval is supported for Agentic "
            "Users, which read as their own identity; an app identity and/or user-delegated permissions may be "
            "used but are not supported via the SDK at this time"
        )
    # No identity was selected, so neither remedy above applies and naming one would send the reader somewhere wrong.
    return "no Graph credential was available, and no identity had been selected when the attempt was made"


def _access_guidance(status: int, actor: Optional[FileActor]) -> str:
    """
    Say what a refusal means, which depends on the status: a rejected token and an insufficient grant have different
    remedies.
    """
    as_who = _describe_actor(actor) if actor else "the identity used"

    if status == 401:
        return (
            f"the token presented for {as_who} was rejected. It may have expired, or been issued for the wrong "
            "audience or tenant"
        )
    if status == 403:
        return (
            f"access was denied for {as_who}. The required scope may not be consented, the file may never have been "
            "shared with that identity, or the drive item may not exist"
        )
    return f"the request for {as_who} was refused with status {status}"
