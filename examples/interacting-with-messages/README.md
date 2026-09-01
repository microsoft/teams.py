# Example: Interacting with Messages

Demonstrates quoting, threading, and reactions in one bot while keeping each concept
in a separate source module.

- `src/quoting.py` - quoted-message metadata and quote composition
- `src/threading_handlers.py` - reactive, proactive, and manually constructed threads
- `src/reactions.py` - reactions on inbound messages and a proactive reaction flow
- `src/main.py` - app setup, explicit handler composition, and help

## Commands

### Quoting

| Command | Behavior |
|---------|----------|
| `quote reply` | Deprecated `ctx.reply()` compatibility behavior auto-quotes the inbound message |
| `quote message` | `ctx.quote()` quotes a previously sent message by ID |
| `quote add` | `add_quote()` composes a quote with a response |
| `quote batch` | Combines multiple quotes with mixed responses |
| `quote manual` | Combines `add_quote()` and `add_text()` manually |
| *(quote a message)* | Displays the quoted-message metadata |

### Threading

| Command | Behavior |
|---------|----------|
| `thread reply` | Deprecated `ctx.reply()` compatibility behavior sends a reactive threaded reply |
| `thread send` | `ctx.send()` sends to the same thread without quoting |
| `thread proactive` | `app.reply()` sends a proactive threaded reply |
| `thread manual` | `app.reply()` selects an explicit thread root |

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
