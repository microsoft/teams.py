# Sample: MCP Server

A comprehensive test demonstrating MCP (Machine Conversation Protocol) server functionality using the Microsoft Teams Python SDK.

## Prerequisites

- Python 3.12 or later
- UV package manager
- An Microsoft 365 development account. If you don't have one, you can get one for free by signing up for the [Microsoft 365 Developer Program](https://developer.microsoft.com/microsoft-365/dev-program).

## Setup

1. Install dependencies:

```bash
uv sync
```

2. Set up your `.env` file (if needed for Teams connectivity)

## Run

```bash
# Activate virtual environment
source .venv/bin/activate  # On macOS/Linux
# .venv\Scripts\Activate   # On Windows

# Run the MCP server
python tests/mcp-server/src/main.py
```

## Features Demonstrated

### Core MCP Server Functionality
- **MCP Server Plugin** - Converting a Teams App into an MCP server using `McpServerPlugin`
- **Custom Server Name** - Configuring server with custom name (`test-mcp`)
- **DevTools Integration** - MCP request inspection through DevToolsPlugin
- **Multiple Tool Registration** - Exposing various tools to MCP clients

### Available Tools

| Tool | Description | Parameters | Example Usage |
|------|-------------|------------|---------------|
| `echo` | Echo back input text | `input: str` | Echo functionality from docs |
| `get_weather` | Get weather for a location | `location: str` | Always returns "sunny" |
| `calculate` | Basic arithmetic operations | `operation: str, a: float, b: float` | add, subtract, multiply, divide |
| `alert` | Send proactive message to Teams user | `user_id: str, message: str` | Human-in-the-loop notifications |

### Proactive Messaging (Message Piping)

The server demonstrates the key documentation feature of "piping messages to the user":

1. **Conversation Storage** - Stores user conversation IDs when they message the bot
2. **User Validation** - The alert tool validates if a user exists in storage
3. **Proactive Messaging** - Simulates sending notifications back to Teams users

#### How it works:
1. User sends any message to the bot ’ conversation ID gets stored
2. External MCP client calls the `alert` tool with `user_id` and `message`
3. Server looks up the stored conversation ID and sends proactive message

### Architecture

The MCP server is available at `/mcp` endpoint (default) and exposes:
- **Tools** - Callable functions with typed parameters
- **Resources** - (Not implemented in this test)
- **Prompts** - (Not implemented in this test)

## Testing the MCP Server

### 1. Start the Server
```bash
python tests/mcp-server/src/main.py
```

### 2. Send a Message via Teams
Send any message to store your conversation ID:
```
Hello MCP server!
```

Response will show your stored conversation ID.

### 3. Test MCP Tools (via MCP Client)
The tools can be called by any MCP-compatible client:

**Echo Tool:**
```json
{
  "tool": "echo",
  "params": {
    "input": "Hello from MCP client"
  }
}
```

**Calculator Tool:**
```json
{
  "tool": "calculate", 
  "params": {
    "operation": "add",
    "a": 10,
    "b": 5
  }
}
```

**Alert Tool (Proactive Messaging):**
```json
{
  "tool": "alert",
  "params": {
    "user_id": "your-teams-user-id",
    "message": "Hello from MCP!"
  }
}
```

### 4. Monitor in DevTools
- Navigate to the DevTools interface
- View MCP requests and responses in real-time
- Similar to the Activities tab for regular Teams interactions

## Key Implementation Notes

- **Plugin Configuration**: Uses `McpServerPlugin(name="test-mcp")` as shown in documentation
- **Tool Registration**: Each tool is registered with `mcp_server_plugin.use_tool(Function(...))`
- **Type Safety**: All parameters use Pydantic models for validation
- **Conversation Tracking**: Stores `user_id ’ conversation_id` mapping for proactive messaging
- **Error Handling**: Proper validation and error responses for invalid tool calls

This implementation covers all the core concepts from the MCP server documentation and provides a solid foundation for testing and development.