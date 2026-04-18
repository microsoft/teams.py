"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, cast

from microsoft_teams.api import MessageActivity
from microsoft_teams.apps import ActivityContext

FILE_DOWNLOAD_CONTENT_TYPE = "application/vnd.microsoft.teams.file.download.info"


def extract_file_attachments(ctx: ActivityContext[MessageActivity]) -> list[dict[str, Any]]:
    """Pull (name, download_url) for each Teams file.download.info attachment on the activity."""
    out: list[dict[str, Any]] = []
    for a in ctx.activity.attachments or []:
        if a.content_type != FILE_DOWNLOAD_CONTENT_TYPE:
            continue
        content = cast(dict[str, Any], a.content) if isinstance(a.content, dict) else {}  # pyright: ignore[reportUnknownMemberType]
        url = content.get("downloadUrl")
        if isinstance(url, str) and url:
            out.append({"name": a.name, "download_url": url})
    return out


def inject_file_list(query: str, files_metadata: list[dict[str, Any]]) -> str:
    """Prepend the file list to the user's query so the LLM can forward it to search_files."""
    file_list = "\n".join(f"- name: {f['name']}, download_url: {f['download_url']}" for f in files_metadata)
    prefix = f"Files available (pass this list to search_files when you call it):\n{file_list}\n\n"
    return prefix + (query or "Summarize the files and generate relevant data insights.")
