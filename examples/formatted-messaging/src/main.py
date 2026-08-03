"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import logging

from microsoft_teams.api import MessageActivity
from microsoft_teams.api.activities.message import MessageActivityInput
from microsoft_teams.api.activities.typing import TypingActivityInput
from microsoft_teams.apps import ActivityContext, App

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = App()


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    """Demonstrate text format options: markdown, extendedmarkdown, xml, and plain."""
    await ctx.reply(TypingActivityInput())
    text = ctx.activity.text.lower()

    if "extended" in text:
        rich_content = "\n".join(
            [
                "\n",
                "# Extended Markdown Demo",
                "",
                "## Table",
                "| Feature | Status |",
                "|---------|--------|",
                "| Tables  | Supported |",
                "| Math    | Supported |",
                "",
                "## Math",
                "$$E = mc^2$$",
            ]
        )
        reply = MessageActivityInput(text=rich_content).with_text_format("extendedmarkdown")
        await ctx.reply(reply)
    elif "markdown" in text:
        md_content = "\n".join(
            [
                "\n",
                "# Markdown Demo",
                "",
                "**Bold**, *italic*, and ~~strikethrough~~",
                "",
                "- Item one",
                "- Item two",
                "- Item three",
                "",
                "> This is a blockquote",
                "",
                "`inline code` and [a link](https://www.microsoft.com)",
            ]
        )
        reply = MessageActivityInput(text=md_content).with_text_format("markdown")
        await ctx.reply(reply)
    elif "xml" in text:
        xml_content = (
            "<b>Bold</b>, <i>italic</i>, and <strike>strikethrough</strike><br/>"
            "<ul><li>Item one</li><li>Item two</li><li>Item three</li></ul>"
        )
        reply = MessageActivityInput(text=xml_content).with_text_format("xml")
        await ctx.reply(reply)
    elif "plain" in text:
        reply = MessageActivityInput(text="This is plain text with no formatting applied.").with_text_format("plain")
        await ctx.reply(reply)
    else:
        await ctx.send("Send **markdown**, **extended**, **xml**, or **plain** to see different text formats.")


if __name__ == "__main__":
    asyncio.run(app.start())
