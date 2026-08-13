"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import re
from base64 import b64encode
from dataclasses import dataclass
from typing import Any, List, Literal, Optional

from microsoft_teams.apps import DownloadedFile

# SAMPLE GUARDRAIL: every constant below is a product choice made by this sample, not a Teams SDK or Azure OpenAI
# limit. They exist to keep one Teams message from turning into an unbounded model request. Pick your own values.
#
# `download()` buffers the whole file before any of these are checked, so they bound what reaches the model, not
# network transfer or process memory.
MAX_FILES = 5
MAX_TEXT_BYTES_PER_FILE = 100 * 1024
MAX_TOTAL_TEXT_BYTES = 250 * 1024
MAX_IMAGE_BYTES = 1024 * 1024

# SAMPLE GUARDRAIL: the formats this sample is willing to forward. The file API itself delivers any attached file type.
IMAGE_CONTENT_TYPES = {
    "image/gif",
    "image/jpeg",
    "image/png",
    "image/webp",
}

TEXT_EXTENSIONS = {
    "c",
    "cpp",
    "cs",
    "css",
    "csv",
    "go",
    "h",
    "html",
    "java",
    "js",
    "json",
    "jsx",
    "md",
    "py",
    "rb",
    "rs",
    "sh",
    "sql",
    "toml",
    "ts",
    "tsx",
    "txt",
    "xml",
    "yaml",
    "yml",
}

_TEXTUAL_CONTENT_TYPE = re.compile(r"\b(json|xml|javascript|yaml|csv|markdown)\b")

FileKind = Literal["image", "text", "unsupported"]
"""Whether this sample can send a downloaded file to the model, and as what."""


@dataclass
class AnalyzableFile:
    """A downloaded file that `classify_file` accepted, paired with its kind."""

    file: DownloadedFile
    kind: Literal["image", "text"]


@dataclass
class AnalysisRequest:
    """A model request built from the user's message and their analyzable files."""

    content: List[Any]

    warnings: List[str]
    """User-facing explanations for files that were skipped or truncated."""

    file_count: int
    """Number of files whose content reached the model request."""


def classify_file(file: DownloadedFile, extension: Optional[str] = None) -> FileKind:
    """
    SAMPLE GUARDRAIL: decides whether a downloaded file can be sent to the model.

    The response MIME type is preferred, but the platform-supplied extension is a necessary fallback, and that part is
    a real file-receive detail rather than a sample preference: Teams commonly omits or misclassifies source files,
    reporting `.ts` as `video/vnd.dlna.mpeg-tts` for example.
    """
    content_type = _base_content_type(file.content_type)

    if content_type in IMAGE_CONTENT_TYPES:
        return "image"

    if _is_text_content_type(content_type) or _get_text_extension(extension, file.filename):
        return "text"

    return "unsupported"


def prepare_analysis(user_text: str, files: List[AnalyzableFile]) -> AnalysisRequest:
    """
    Converts already-downloaded files into OpenAI content parts.

    The conversion itself is the AI integration. The caps it enforces along the way are SAMPLE GUARDRAILs, and each one
    that drops or shortens a file returns a warning so the user is never left guessing what the model saw.
    """
    parts: List[Any] = [
        {
            "type": "text",
            "text": user_text.strip() or "Please analyze the attached file content.",
        }
    ]
    warnings: List[str] = []
    file_count = 0
    total_text_bytes = 0

    for entry in files[:MAX_FILES]:
        downloaded = entry.file

        if entry.kind == "image":
            if len(downloaded.bytes) > MAX_IMAGE_BYTES:
                warnings.append(f"{downloaded.filename} was not sent to the model because it is larger than 1 MB.")
                continue

            parts.append({"type": "text", "text": f"Attached image: {downloaded.filename}"})
            parts.append(
                {
                    "type": "image_url",
                    "image_url": {
                        # FILE RECEIVE: the downloaded bytes are sent inline instead of handing the model the
                        # pre-authorized `tempauth` download URL, which is a short-lived credential.
                        "url": _to_data_uri(downloaded.bytes, _base_content_type(downloaded.content_type)),
                        "detail": "auto",
                    },
                }
            )
            file_count += 1
            continue

        remaining_bytes = MAX_TOTAL_TEXT_BYTES - total_text_bytes
        if remaining_bytes <= 0:
            warnings.append(
                f"{downloaded.filename} was not sent to the model because the combined text-file limit was reached."
            )
            continue

        included_bytes = min(len(downloaded.bytes), MAX_TEXT_BYTES_PER_FILE, remaining_bytes)
        text = downloaded.bytes[:included_bytes].decode("utf-8", errors="replace")
        truncated = included_bytes < len(downloaded.bytes)
        total_text_bytes += included_bytes

        parts.append(
            {
                "type": "text",
                "text": "\n".join(
                    [
                        f"Attached file: {downloaded.filename}",
                        "",
                        "<file>",
                        text,
                        "\n[File content truncated by the sample.]" if truncated else "",
                        "</file>",
                    ]
                ),
            }
        )

        if truncated:
            warnings.append(f"{downloaded.filename} was truncated before being sent to the model.")
        file_count += 1

    if len(files) > MAX_FILES:
        warnings.append(
            f"{len(files) - MAX_FILES} additional file(s) were not sent to the model because this sample accepts "
            f"up to {MAX_FILES} files per message."
        )

    return AnalysisRequest(content=parts, warnings=warnings, file_count=file_count)


def _base_content_type(content_type: str) -> str:
    return content_type.split(";", 1)[0].strip().lower()


def _is_text_content_type(content_type: str) -> bool:
    return content_type.startswith("text/") or bool(_TEXTUAL_CONTENT_TYPE.search(content_type))


def _get_text_extension(extension: Optional[str], filename: str) -> Optional[str]:
    if extension:
        normalized = extension.lstrip(".").lower()
    elif "." in filename:
        normalized = filename.rsplit(".", 1)[-1].lower()
    else:
        normalized = ""
    return normalized if normalized in TEXT_EXTENSIONS else None


def _to_data_uri(data: bytes, content_type: str) -> str:
    return f"data:{content_type};base64,{b64encode(data).decode('ascii')}"
