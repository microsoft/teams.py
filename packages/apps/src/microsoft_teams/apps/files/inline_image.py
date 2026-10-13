"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import re
from dataclasses import dataclass
from typing import Literal, Optional, cast
from urllib.parse import urlsplit

InlineImageFormat = Literal["png", "jpeg", "gif", "webp"]
"""
The image formats the SDK gives an extension and a specific MIME type.

PNG, JPEG, and WebP are named and typed with confidence.
GIF is not: Teams saves a pasted GIF as a static PNG, so it is listed as `.gif` and `image/gif` but downloads as a PNG.
Other formats, such as BMP and AVIF, are not given an extension or a specific MIME type.
"""

_INLINE_IMAGE_FORMATS: dict[str, tuple[str, str]] = {
    "png": ("png", "image/png"),
    "jpeg": ("jpg", "image/jpeg"),
    "gif": ("gif", "image/gif"),
    "webp": ("webp", "image/webp"),
}

_OCTET_STREAM = "application/octet-stream"

_INLINE_IMAGE_PATH = re.compile(r"/v3/attachments/([A-Za-z0-9_.-]+)/views/original$", re.IGNORECASE)
"""
Matches the path of an inline image hosted by the Bot API, capturing its attachment id.

Pattern: the URL's path ends in `/v3/attachments/<id>/views/original`, so the same text in a query string or
fragment does not match.
The id becomes part of the file name, so it is limited to letters, digits, `_`, `.`, and `-`, which keeps path
separators out of it.
"""

_IMG_TAG = re.compile(r"<img\b(?:[^<>\"']|\"[^\"]*\"|'[^']*')*>", re.IGNORECASE | re.ASCII)

_ATTRIBUTE = re.compile(r"(?<![A-Za-z0-9_-])([A-Za-z0-9_-]+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)')")

_IMAGE_CONTENT_TYPE = re.compile(r"^image/([A-Za-z0-9_.+-]+)", re.IGNORECASE)

AMS_IMAGE_ITEMTYPE = "http://schema.skype.com/AMSImage"


@dataclass
class InlineImageNaming:
    """The filename, extension, and MIME type the SDK lists an inline image under."""

    name: str
    """Display name, with an extension when the format is one the SDK names."""

    extension: Optional[str]
    """Extension without the dot, or `None` when the format is not one the SDK names."""

    content_type: str
    """MIME type, or `application/octet-stream` when the format is not one the SDK types."""


def inline_image_id(content_url: str) -> Optional[str]:
    """
    The attachment id of an inline image, taken from its `content_url`, or `None` when the URL is not an inline
    image location.
    """
    try:
        path = urlsplit(content_url).path
    except ValueError:
        return None

    match = _INLINE_IMAGE_PATH.search(path)
    return match.group(1) if match else None


def parse_inline_image_hints(html: str) -> dict[str, str]:
    """
    Map each inline image id found in a message's HTML to its format hint.

    The hint is the `itemscope` attribute of an `<img>` whose `itemtype` marks it as an inline image, keyed by its
    `itemid`.
    """
    hints: dict[str, str] = {}

    # Each <img ...> start tag
    for tag in _IMG_TAG.findall(html):
        attributes: dict[str, str] = {}

        # Each name="value", capturing the name and whichever quoted value matched.
        # A name starts only where the previous character is not part of a name, so a long run of name characters is
        # scanned once rather than once per position.
        for match in _ATTRIBUTE.finditer(tag):
            double_quoted, single_quoted = match.group(2), match.group(3)
            attributes[match.group(1).lower()] = double_quoted if double_quoted is not None else single_quoted

        id = attributes.get("itemid")
        scope = attributes.get("itemscope")

        if attributes.get("itemtype") == AMS_IMAGE_ITEMTYPE and id and scope:
            hints[id] = scope

    return hints


def format_from_hint(hint: Optional[str]) -> Optional[InlineImageFormat]:
    """The format named by an `itemscope` hint, or `None` when it is not one of `InlineImageFormat`."""
    normalized = hint.strip().lower() if hint else None

    if normalized == "jpg":
        return "jpeg"

    if normalized in _INLINE_IMAGE_FORMATS:
        return cast(InlineImageFormat, normalized)

    return None


def format_from_content_type(content_type: Optional[str]) -> Optional[InlineImageFormat]:
    """The format named by an `image/*` content type, or `None` when it is not one of `InlineImageFormat`."""
    # "image/" then the subtype (letters, digits, ".", "+" or "-"), capturing the subtype.
    match = _IMAGE_CONTENT_TYPE.match(content_type.strip() if content_type else "")
    return format_from_hint(match.group(1) if match else None)


def sniff_image_format(data: bytes) -> Optional[InlineImageFormat]:
    """
    The format the bytes actually are, read from their leading magic bytes, or `None` when they are none of
    `InlineImageFormat`.

    The Teams service can return bytes in a different format from the hint (a GIF downloads as a static PNG), so the
    bytes are the stronger signal.
    """

    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"

    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"

    if data.startswith((b"GIF87a", b"GIF89a")):
        return "gif"

    # "RIFF" at byte 0 and "WEBP" at byte 8; bytes 4-7 are the file size.
    if data.startswith(b"RIFF") and data.startswith(b"WEBP", 8):
        return "webp"

    return None


def inline_image_naming(base_name: str, format: Optional[InlineImageFormat] = None) -> InlineImageNaming:
    """
    The filename, extension, and MIME type for an inline image of the given format.

    An unknown format gets no extension and `application/octet-stream` rather than a guess.
    """
    if not format:
        return InlineImageNaming(name=base_name, extension=None, content_type=_OCTET_STREAM)

    extension, content_type = _INLINE_IMAGE_FORMATS[format]
    return InlineImageNaming(name=f"{base_name}.{extension}", extension=extension, content_type=content_type)
