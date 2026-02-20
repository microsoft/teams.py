# Example: Message Reactions

A bot that demonstrates adding and removing reactions to messages in Microsoft Teams.

This example shows how to use the `ReactionClient` to programmatically add and remove reactions (like, heart, laugh, etc.) on messages.

## Commands

| Command | Behavior |
|---------|----------|
| `react <type>` | Adds a reaction to your message (e.g., `react like`, `react heart`) |
| `unreact <type>` | Removes a reaction from your message |
| `help` | Shows available commands |

## Supported Reaction Types

- `like` - 👍 Like
- `heart` - ❤️ Heart
- `laugh` - 😂 Laugh
- `surprised` - 😮 Surprised
- `sad` - 😢 Sad
- `angry` - 😠 Angry
- `plusOne` - ➕ Plus one

## How It Works

The bot listens for incoming messages and:
1. When you send `react <type>`, it adds that reaction to your message
2. When you send `unreact <type>`, it removes that reaction from your message

The reactions are added/removed using the Bot Framework v3 API:
- **Add**: `PUT /v3/conversations/{conversationId}/activities/{activityId}/reactions/{reactionType}`
- **Remove**: `DELETE /v3/conversations/{conversationId}/activities/{activityId}/reactions/{reactionType}`

## Testing

1. Add the bot to a Teams chat or channel
2. Send a message: `react like`
3. **Expected result**: A 👍 reaction appears on your message
4. Send another message: `unreact like`
5. **Expected result**: The 👍 reaction is removed from that message

## Run

```bash
cd examples/reactions
uv run python src/main.py
```

## Environment Variables

Create a `.env` file:

```env
CLIENT_ID=<your-azure-bot-app-id>
CLIENT_SECRET=<your-azure-bot-app-secret>
```
