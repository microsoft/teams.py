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
| `quote reply` | `add_quote()` explicitly quotes the inbound message |
| `quote message` | `add_quote()` quotes a previously sent message by ID |
| `quote batch` | Combines multiple quotes with mixed responses |
| *(quote a message)* | Displays the quoted-message metadata |

### Threading

| Command | Behavior |
|---------|----------|
| `default send` | `ctx.send()` uses the default reactive placement |
| `thread proactive` | `app.reply()` selects an explicit proactive thread root |
| `thread proactive quote` | `app.reply()` selects a thread root; `add_quote()` adds quote metadata |
| `thread proactive targeted` | `app.reply()` sends a targeted activity to an explicit thread root |
| `thread proactive targeted quote` | Combines targeted thread placement with explicit quote metadata |

Targeted outbound activities use the targeted reply endpoint when a thread root is
selected, so recipient visibility, thread placement, and quote metadata remain
independent.

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
