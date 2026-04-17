"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
import time
from typing import Annotated

import httpx
from agent_framework import Agent, tool
from agent_framework_openai import OpenAIChatClient

logger = logging.getLogger(__name__)

INSTRUCTIONS = (
    "You are a file search assistant. "
    "The user will provide a list of available files (name + download URL) and a query. "
    "Download only the files that are likely relevant to the query, then answer based on their contents.\n\n"
    "When returning tabular data (CSV rows, records, etc.), reproduce EVERY row verbatim — "
    "do not summarize, sample, or use '...' to elide rows. Downstream tools will chart or tabulate "
    "the data and need complete rows."
)


@tool
async def download_file(
    name: Annotated[str, "The filename as it appears in the metadata"],
    download_url: Annotated[str, "The pre-authenticated download URL for the file"],
) -> str:
    """Download a file and return its text content."""
    logger.info("download_file: START name=%r url_len=%d url_prefix=%r", name, len(download_url), download_url[:80])
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as http:
            response = await http.get(download_url)
            elapsed = time.monotonic() - start
            logger.info(
                "download_file: HTTP %s name=%r status=%d elapsed=%.2fs content_type=%r content_length=%s redirects=%d",
                "OK" if response.is_success else "ERR",
                name,
                response.status_code,
                elapsed,
                response.headers.get("content-type"),
                response.headers.get("content-length"),
                len(response.history),
            )
            response.raise_for_status()
            content = response.content.decode("utf-8", errors="replace")
            logger.info("download_file: DONE name=%r size=%d bytes", name, len(content))
            return content
    except httpx.HTTPStatusError as e:
        logger.exception("download_file: HTTPStatusError name=%r status=%d", name, e.response.status_code)
        raise
    except httpx.RequestError as e:
        logger.exception("download_file: RequestError name=%r type=%s msg=%r", name, type(e).__name__, str(e))
        raise
    except Exception:
        logger.exception("download_file: UNEXPECTED name=%r", name)
        raise


agent = Agent(OpenAIChatClient(), instructions=INSTRUCTIONS, tools=[download_file])
