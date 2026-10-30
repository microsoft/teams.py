# Example: Interacting with Messages

Demonstrates quoting, threading, and reactions in one bot while keeping each concept
in a separate source module.

- `src/quoting.py` - quoted-message metadata and quote composition
- `src/threading_handlers.py` - reactive and proactive threaded replies, and top-level messages
- `src/reactions.py` - reactions on inbound messages and a proactive reaction flow
- `src/main.py` - app setup, explicit handler composition, and help

## Commands

### Quoting

| Command | Behavior |
|---------|----------|
| `quote reply` | `ctx.reply()` auto-quotes the inbound message |
| `quote message` | `ctx.quote()` quotes a previously sent message by ID |
| `quote add` | `add_quote()` composes a quote with a response |
| `quote batch` | Combines multiple quotes with mixed responses |
| `quote manual` | Combines `add_quote()` and `add_text()` manually |
| *(quote a message)* | Displays the quoted-message metadata |

### Threading

| Command | Behavior |
|---------|----------|
| `thread reply` | `ctx.reply()` sends a reactive, quoted reply. In a channel it is sent in the same thread. In a 1:1 chat it matches the level of your message (in the thread if your message is in one, otherwise top-level) |
| `thread send` | `ctx.send()` sends reactively without quoting. In a channel it is sent in the same thread. In a 1:1 chat it matches the level of your message (in the thread if your message is in one, otherwise top-level) |
| `thread proactive` | `app.reply()` replies in the reply chain (thread) of your message, using `channel_data.chat.id` (or `channel_data.channel.id`) and `channel_data.reply_chain.id`. Without `reply_chain.id` the sample answers that there is not enough thread metadata |
| `thread top-level` | `app.send()` to `channel_data.chat.id` (or `channel_data.channel.id`) sends a new top-level message |

### Reactions

| Command | Behavior |
|---------|----------|
| `reaction add <type>` | Adds a reaction to the inbound message |
| `reaction remove <type>` | Adds a reaction, then removes it after two seconds |
| `reaction proactive` | Sends a bot message and reacts to it using app-level APIs |
| *(react to a bot message)* | Reports added reactions and logs removed reactions |

## Run

```bash
uv run python src/main.py
```
