# Example: Interacting with Messages

Demonstrates quoting, threading, and reactions in one bot while keeping each concept
in a separate source module.

- `src/quoting.py` - quoted-message metadata and quote composition
- `src/threading_handlers.py` - reactive and proactive threaded replies, and top-level messages
- `src/reactions.py` - reactions on inbound messages and a proactive reaction flow
- `src/main.py` - app setup, explicit handler composition, and help

## Reply modes

`ctx.reply()` places and quotes its response according to the reply mode. Set it for the whole app, or pass it on a single call (this sample keeps the default, `combined`):

```python
app = App(reply_mode="thread")

await ctx.reply("Hello!", reply_mode="quote")
```

| Mode | In a chat | Quote |
|------|-----------|-------|
| `combined` (default) | A reply to a top-level message starts a thread under it; a reply inside a thread stays in that thread | Yes |
| `thread` | Same as `combined` | No |
| `quote` | The reply stays at the level of the inbound message | Yes |

In a channel every reply goes in the thread of the inbound message, so the mode only decides the quote.

## Commands

### Quoting

| Command | Behavior |
|---------|----------|
| `quote reply` | `ctx.reply(text, reply_mode="quote")` auto-quotes the inbound message and stays at its level (a top-level message gets a top-level reply) |
| `quote message` | `ctx.quote()` quotes a previously sent message by ID |
| `quote add` | `add_quote()` composes a quote with a response |
| `quote batch` | Combines multiple quotes with mixed responses |
| `quote manual` | Combines `add_quote()` and `add_text()` manually |
| *(quote a message)* | Displays the quoted-message metadata |

### Threading

| Command | Behavior |
|---------|----------|
| `thread reply` | `ctx.reply()` with the default reply mode, `combined`. In a chat, a reply to a top-level message starts a thread under it, and a reply inside a thread stays in that thread. The inbound message is quoted. In a channel it is sent in the same thread |
| `thread reply unquoted` | `ctx.reply(text, reply_mode="thread")`. The same placement as `combined`, without the quote |
| `thread send` | `ctx.send()` sends reactively without quoting. In a channel it is sent in the same thread. In a chat it matches the level of your message (in the thread if your message is in one, otherwise top-level). In a chat, unlike `reply`, `send` never starts a new thread |
| `thread proactive` | `app.reply()` replies in the reply chain (thread) of your message without the inbound activity, as a bot does when it replies later. It never quotes. It uses `channel_data.chat.id` (or `channel_data.channel.id`) and `channel_data.reply_chain.id`. Without `reply_chain.id` the sample answers that there is not enough thread metadata |
| `thread top-level` | `app.send()` to `channel_data.chat.id` (or `channel_data.channel.id`) sends a new top-level message |

### Reactions

| Command | Behavior |
|---------|----------|
| `reaction add <type>` | Adds a reaction to the inbound message |
| `reaction remove <type>` | Adds a reaction, then removes it after two seconds |
| `reaction proactive` | Sends a bot message and reacts to it using app-level APIs |
| *(react to a bot message)* | Thanks you for an added reaction with `ctx.reply()` (in a chat, in a thread under the message you reacted to) and logs removed reactions |

## Notes

- Threading behavior depends on the conversation type. A threaded reply, from `ctx.reply()` or a proactive `app.reply()`, may return a service error where threading is unsupported.
- Every message first gets a typing indicator from `ctx.send(TypingActivityInput())`. A typing activity never starts a new thread, so for a top-level message the indicator shows in the main conversation while a `thread reply` answer appears in the new thread.

## Run

```bash
uv run python src/main.py
```
