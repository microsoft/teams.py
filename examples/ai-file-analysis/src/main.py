"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

AI File Analysis Example Bot

Two kinds of code live in this sample, labeled throughout:

- `FILE RECEIVE` is the Teams SDK file API itself. This is the part worth copying into your own app.
- `SAMPLE GUARDRAIL` is this sample deciding what it is willing to forward to a model. Those limits are arbitrary
  product choices, not SDK requirements, and your app should pick its own.
"""

import asyncio
import logging
from typing import List

from ai import AnalyzableFile, classify_file, is_ai_configured, prepare_analysis, run_analysis
from file_card import unsupported_file_card
from microsoft_teams.api import MessageActivity, TypingActivityInput
from microsoft_teams.apps import ActivityContext, App

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai-file-analysis")

app = App()

# SAMPLE GUARDRAIL: the file API needs no model, so the sample stays usable without Azure OpenAI settings. Without
# them it answers every file with the metadata card instead of analyzing it, which keeps download, content type,
# scope, and source demonstrable with no model subscription.
_ai_configured = is_ai_configured()
if not _ai_configured:
    logger.warning(
        "Azure OpenAI is not configured, so files will be reported but not analyzed. Set AZURE_OPENAI_ENDPOINT, "
        "AZURE_OPENAI_API_KEY, and AZURE_OPENAI_MODEL_DEPLOYMENT_NAME in .env to enable analysis."
    )

NO_MODEL_NOTE = (
    "I downloaded this file, but no model is configured for this sample, so I did not analyze it. "
    "Set the Azure OpenAI values in .env to enable analysis."
)


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]) -> None:
    """Analyze any files attached to the message, and describe the ones this sample cannot read."""
    await ctx.send(TypingActivityInput())

    # FILE RECEIVE: the files attached to this activity.
    attached = await ctx.files.list()
    if not attached:
        await ctx.send(
            "Attach one or more files. I analyze text files and images, and describe anything else I cannot read."
            if _ai_configured
            else "Attach one or more files. No model is configured, so I will report what I received "
            "without analyzing it."
        )
        return

    analyzable: List[AnalyzableFile] = []

    for file in attached:
        try:
            # FILE RECEIVE: download once. Every read below uses this in-memory copy rather than refetching through the
            # short-lived Teams download URL.
            downloaded = await file.download()
        except Exception as err:
            logger.warning("Could not download %s: %s", file.name, err)
            await ctx.send(f"I could not download {file.name}.")
            continue

        if not _ai_configured:
            await ctx.send(unsupported_file_card(file, downloaded, NO_MODEL_NOTE))
            continue

        # SAMPLE GUARDRAIL: the SDK hands over every attached file regardless of type. This sample is what narrows
        # that to the formats it will send on.
        kind = classify_file(downloaded, file.extension)

        if kind == "unsupported":
            await ctx.send(unsupported_file_card(file, downloaded))
            continue

        analyzable.append(AnalyzableFile(file=downloaded, kind=kind))

    if not analyzable:
        return

    # SAMPLE GUARDRAIL: applies this sample's size and count caps and reports anything it dropped or truncated.
    analysis = prepare_analysis(ctx.activity.strip_mentions_text().text or "", analyzable)

    for warning in analysis.warnings:
        await ctx.send(warning)

    if analysis.file_count == 0:
        return

    await run_analysis(analysis, ctx.stream, logger)


if __name__ == "__main__":
    asyncio.run(app.start())
