# Example: Targeted Messages

A bot that demonstrates targeted (ephemeral) messages in Microsoft Teams.

Targeted messages are messages that only a specific recipient can see - other participants in the conversation won't see them.

## Commands

| Command | Behavior |
|---------|----------|
| `test send` | Sends a targeted message (only you see it) |
| `test reply` | Replies with a targeted message |
| `test update` | Sends a targeted message, then updates it after 3 seconds |
| `test delete` | Sends a targeted message, then deletes it after 5 seconds |
| `help` | Shows available commands |

## How It Works

When responding to an incoming message, use `with_targeted_recipient(True)` - the recipient is automatically inferred from the message sender.

## Testing in a Group Chat

To properly test targeted messages:

1. Add the bot to a **group chat** with 2+ people
2. Send `test send`
3. **Expected result**: 
   - You (the sender) should see the "🔒 Targeted message"
   - Other participants should **NOT** see it

## Run

```bash
cd examples/targeted-messages
uv run python src/main.py
```

## Environment Variables

Create a `.env` file:

```env
CLIENT_ID=<your-azure-bot-app-id>
CLIENT_SECRET=<your-azure-bot-app-secret>
```
