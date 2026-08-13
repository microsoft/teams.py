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

from ai import AnalyzableFile, classify_file, prepare_analysis, run_analysis
from file_card import unsupported_file_card
from microsoft_teams.api import MessageActivity, TypingActivityInput
from microsoft_teams.apps import ActivityContext, App

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai-file-analysis")

app = App()


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]) -> None:
    """Analyze any files attached to the message, and describe the ones this sample cannot read."""
    await ctx.send(TypingActivityInput())

    # FILE RECEIVE: the files attached to this activity.
    attached = await ctx.files.list()
    if not attached:
        await ctx.send(
            "Attach one or more files. I analyze text files and images, and describe anything else I cannot read."
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
