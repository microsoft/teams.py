"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
from os import getenv
from typing import Any, cast

from dotenv import find_dotenv, load_dotenv
from microsoft_teams.api import MessageActivityInput
from microsoft_teams.apps.plugins.streamer import StreamerProtocol
from openai import AsyncAzureOpenAI

from .file_context import AnalysisRequest

load_dotenv(find_dotenv(usecwd=True))

SYSTEM_PROMPT = """\
You analyze files supplied by the user.

Base your answer on the user's message and the attached content. State clearly when the available files do not support
a conclusion. Do not claim to have inspected files that were not included. Keep the response concise and practical."""


def _required(name: str) -> str:
    value = getenv(name)
    if not value:
        raise ValueError(f"{name} is required (set it in .env).")
    return value


_deployment = _required("AZURE_OPENAI_MODEL_DEPLOYMENT_NAME")
_client = AsyncAzureOpenAI(
    azure_endpoint=_required("AZURE_OPENAI_ENDPOINT"),
    api_key=_required("AZURE_OPENAI_API_KEY"),
    api_version=getenv("AZURE_OPENAI_API_VERSION") or "2024-10-21",
)


async def run_analysis(request: AnalysisRequest, stream: StreamerProtocol, log: logging.Logger) -> None:
    """
    Sends one stateless request for the current message and streams the reply.

    SAMPLE GUARDRAIL: nothing is carried between turns. A stateful agent would keep history here, but that would let a
    later message silently reuse file content the user did not attach to it, and would resend every image on every
    following turn.
    """
    try:
        stream.update("Analyzing files...")

        completion = await _client.chat.completions.create(
            model=_deployment,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": cast(Any, request.content)},
            ],
            stream=True,
        )

        async for chunk in completion:
            if not chunk.choices:
                continue
            text = chunk.choices[0].delta.content
            if text:
                stream.emit(text)

        stream.emit(MessageActivityInput().add_ai_generated())
    except Exception as err:
        message = str(err)
        log.error("File analysis failed: %s", message)
        stream.clear_text()
        rate_limited = getattr(err, "status_code", None) == 429 or message.startswith("429 ")
        stream.emit(
            MessageActivityInput(
                text=(
                    "The AI service is temporarily rate-limited. Please wait a moment and try again."
                    if rate_limited
                    else "I could not analyze those files. Please try again."
                )
            ).add_ai_generated()
        )
