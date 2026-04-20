# Example: Threading

A bot that demonstrates reactive and proactive threading in Microsoft Teams channels.

## Commands

| Command | Behavior |
|---------|----------|
| `test reply` | `ctx.reply()` — reactive threaded reply with visual quote |
| `test send` | `ctx.send()` — reactive send to same thread, no quote |
| `test proactive` | `app.reply()` — proactive threaded reply |
| `test manual` | `to_threaded_conversation_id()` + `app.send()` — advanced manual control |
| `help` | Shows available commands |

## Notes

- `test reply` and `test send` work in all scopes (1:1, group chat, channels)
- `test proactive` constructs a threaded conversation ID and sends to that thread
- `test manual` does the same using `to_threaded_conversation_id()` + `app.send()` directly
- `test proactive` and `test manual` may return a service error in conversation types that do not currently support threading (e.g. meetings)

## Run

```bash
uv run python src/main.py
```

## Environment Variables

Create a `.env` file:

```
CLIENT_ID=<your-azure-bot-app-id>
CLIENT_SECRET=<your-azure-bot-app-secret>
```
