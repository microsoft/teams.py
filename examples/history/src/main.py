"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import logging
import re
from typing import Any

from microsoft_teams.api import MessageActivity
from microsoft_teams.api.activities.typing import TypingActivityInput
from microsoft_teams.apps import ActivityContext, App

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = App()


def _parse_count(raw: str | None, default: int = 5) -> int:
    if raw is None:
        return default

    count = int(raw)
    if count < 1:
        raise ValueError("count must be greater than 0")

    return count


def _command_parts(text: str) -> list[str]:
    without_mentions = re.sub(r"<at>.*?</at>", "", text, flags=re.IGNORECASE).strip()
    return without_mentions.split()


def _read_attr(value: Any, *names: str) -> Any:
    current = value
    for name in names:
        current = getattr(current, name, None)
        if current is None:
            return None
    return current


def _message_sender(message: Any) -> str:
    sender = (
        _read_attr(message, "from_", "user", "display_name")
        or _read_attr(message, "from_", "application", "display_name")
        or "Unknown"
    )
    if sender == "Unknown":
        logger.info(
            "Unknown history sender payload: %s",
            message.model_dump(by_alias=True, exclude_none=True) if hasattr(message, "model_dump") else message,
        )
    return sender


def _message_text(message: Any) -> str:
    content = _read_attr(message, "body", "content") or "(no content)"
    text = re.sub(r"<[^>]+>", "", str(content)).strip()
    return re.sub(r"\s+", " ", text) or "(no content)"


def _format_history(title: str, messages: list[Any]) -> str:
    if not messages:
        return f"**{title}**\n\nNo messages returned."

    lines = [f"**{title}**", ""]
    for index, message in enumerate(messages, 1):
        sender = _message_sender(message)
        text = _message_text(message)
        created = getattr(message, "created_date_time", None)
        timestamp = f" ({created})" if created else ""
        lines.append(f"{index}. **{sender}**{timestamp}: {text[:240]}")

    return "\n\n".join(lines)


async def _send_history(ctx: ActivityContext[MessageActivity], title: str, messages: list[Any]) -> None:
    await ctx.reply(_format_history(title, messages))


def _history_error_guidance(error: Exception) -> str:
    error_text = str(error)
    if "ChannelMessage.Read.All" in error_text or "Missing role permissions" in error_text:
        return (
            "Channel history requires the Microsoft Graph **Application** permission "
            "`ChannelMessage.Read.All` with admin consent. After granting it, restart "
            "the bot so it gets a fresh app token containing the new role."
        )

    return "Check that Graph app permissions are granted and that the IDs match the command scope."


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]) -> None:
    await ctx.reply(TypingActivityInput())

    text = ctx.activity.text or ""
    parts = _command_parts(text)
    normalized_text = " ".join(parts).lower()

    if "history" not in normalized_text and "help" not in normalized_text:
        await ctx.reply('Say "help" for message history commands.')
        return

    if "help" in normalized_text:
        await ctx.reply(
            "**Message History Test Bot**\n\n"
            "**Commands:**\n\n"
            "- `history` - current context history with `ctx.get_history(5)`\n\n"
            "- `history ctx <n>` - current context history with a custom count\n\n"
            "- `history chat <chat-id> [n]` - app-level chat history\n\n"
            "- `history channel <team-aad-group-id> <channel-id> [n]` - app-level channel history\n\n"
            "- `history thread <team-aad-group-id> <channel-id> <thread-id> [n]` - app-level channel thread replies"
        )
        return

    try:
        history_index = next(index for index, part in enumerate(parts) if part.lower() == "history")
        args = parts[history_index + 1 :]
        scope = args[0].lower() if args else "ctx"

        if scope == "ctx":
            count = _parse_count(args[1] if len(args) > 1 else None)
            await _send_history(ctx, "Current context history", await ctx.get_history(count))
            return

        if scope == "chat" and len(args) >= 2:
            count = _parse_count(args[2] if len(args) > 2 else None)
            messages = await app.get_history(n=count, chat_id=args[1])
            await _send_history(ctx, f"Chat history for {args[1]}", messages)
            return

        if scope == "channel" and len(args) >= 3:
            count = _parse_count(args[3] if len(args) > 3 else None)
            messages = await app.get_history(n=count, team_aad_group_id=args[1], channel_id=args[2])
            await _send_history(ctx, f"Channel history for {args[2]}", messages)
            return

        if scope == "thread" and len(args) >= 4:
            count = _parse_count(args[4] if len(args) > 4 else None)
            messages = await app.get_history(
                n=count,
                team_aad_group_id=args[1],
                channel_id=args[2],
                thread_id=args[3],
            )
            await _send_history(ctx, f"Thread history for {args[3]}", messages)
            return

        await ctx.reply('Invalid command. Say "help" for message history commands.')

    except Exception as e:
        logger.exception("Failed to get message history")
        await ctx.reply(f"Failed to get message history: {e}\n\n{_history_error_guidance(e)}")


if __name__ == "__main__":
    asyncio.run(app.start())
