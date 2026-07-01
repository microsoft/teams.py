# Example: Message History

A bot that demonstrates the `ctx.get_history(...)` and `app.get_history(...)` APIs backed by Microsoft Graph.

## Commands

| Command | Behavior |
|---------|----------|
| `history` | Reads the 5 most recent messages for the current chat or channel context using `ctx.get_history(5)` |
| `history ctx <n>` | Reads the last `<n>` messages from the current context |
| `history chat <chat-id> [n]` | Reads chat history using `app.get_history(n=n, chat_id=chat_id)` |
| `history channel <team-aad-group-id> <channel-id> [n]` | Reads channel history using `app.get_history(n=n, team_aad_group_id=team_aad_group_id, channel_id=channel_id)` |
| `history thread <team-aad-group-id> <channel-id> <thread-id> [n]` | Reads channel thread replies using `app.get_history(..., thread_id=thread_id)` |
| `help` | Shows available commands |

## Required Graph permissions

This example uses app-only Microsoft Graph calls. Grant and admin-consent the app permissions needed for the surfaces you test:

- Channel history: `ChannelMessage.Read.All`
- Chat history: `Chat.Read.All` or the more specific chat message permission your tenant requires

## Run

```bash
uv run python src/main.py
```

## Environment Variables

Create a `.env` file:

```text
CLIENT_ID=<your-azure-bot-app-id>
CLIENT_SECRET=<your-azure-bot-app-secret>
TENANT_ID=<your-tenant-id>
```
