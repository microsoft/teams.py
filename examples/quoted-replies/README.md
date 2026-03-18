# Example: Quoted Replies

A bot that demonstrates quoted reply features in Microsoft Teams — referencing previous messages when sending responses.

## Commands

| Command | Behavior |
|---------|----------|
| `test reply` | `reply()` — auto-quotes the inbound message |
| `test quote` | `quote_reply()` — sends a message, then quotes it by ID |
| `test add` | `add_quoted_reply()` — sends a message, then quotes it with builder + response |
| `test multi` | Sends two messages, then quotes both with interleaved responses |
| `test manual` | `add_quoted_reply()` + `add_text()` — manual control |
| `help` | Shows available commands |
| *(quote a message)* | Bot reads and displays the quoted reply metadata |

## Run

```bash
cd examples/quoted-replies
uv run python src/main.py
```

## Environment Variables

Create a `.env` file:

```env
CLIENT_ID=<your-azure-bot-app-id>
CLIENT_SECRET=<your-azure-bot-app-secret>
```
