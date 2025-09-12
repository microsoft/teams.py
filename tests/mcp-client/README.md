# Sample: MCP Client

A comprehensive test demonstrating MCP (Machine Conversation Protocol) client functionality using the Microsoft Teams Python SDK. This test shows how to integrate remote MCP servers into your Teams application, allowing AI agents to access external tools via the SSE protocol.

## Prerequisites

- Python 3.12 or later
- UV package manager
- An Microsoft 365 development account. If you don't have one, you can get one for free by signing up for the [Microsoft 365 Developer Program](https://developer.microsoft.com/microsoft-365/dev-program).

## Setup

1. Install dependencies:

```bash
uv sync
```

2. Set up your `.env` file with your API keys:

```bash
# Azure OpenAI (required)
AZURE_OPENAI_API_KEY=<your_azure_openai_api_key>
AZURE_OPENAI_ENDPOINT=<your_azure_openai_endpoint>
AZURE_OPENAI_MODEL=<your_azure_openai_model_deployment_name>
AZURE_OPENAI_API_VERSION=<your_azure_openai_api_version>

# Alternatively, set the OpenAI API key:
OPENAI_API_KEY=<sk-your_openai_api_key>

# GitHub PAT for MCP server (optional)
GITHUB_PAT=<your_github_personal_access_token>
```

## Run

```bash
# Activate virtual environment
source .venv/bin/activate  # On macOS/Linux
# .venv\Scripts\Activate   # On Windows

# Run the MCP client
python tests/mcp-client/src/main.py
```

## Features Demonstrated

### Core MCP Client Functionality
- **Remote MCP Server Integration** - Connect to external MCP servers via SSE protocol
- **Multiple Server Support** - Demonstrate connecting to multiple MCP servers simultaneously
- **ChatPrompt Integration** - Direct integration with ChatPrompt for tool access
- **Agent Integration** - Stateful conversation with MCP tools through Agent pattern
- **DevTools Integration** - Monitor MCP requests and responses in real-time

### Available Commands

| Command | Description | Example Usage |
|---------|-------------|---------------|
| `agent <query>` | Use stateful Agent with MCP tools | `agent What's the weather like?` |
| `prompt <query>` | Use stateless ChatPrompt with MCP tools | `prompt Find information about Python` |
| `mcp info` | Show connected MCP servers and usage | `mcp info` |
| `<any message>` | Fallback to Agent with MCP tools | `Hello, can you help me?` |

### Architecture Patterns

#### 1. ChatPrompt with MCP (Stateless)
```python
chat_prompt = ChatPrompt(
    completions_model,
    plugins=[mcp_plugin]
)

result = await chat_prompt.send(
    input=query,
    instructions="You are a helpful assistant with access to remote MCP tools."
)
```

#### 2. Agent with MCP (Stateful)
```python
responses_agent = Agent(
    responses_model, 
    memory=chat_memory, 
    plugins=[mcp_plugin]
)

result = await responses_agent.send(query)
```

#### 3. Multiple MCP Server Configuration
```python
mcp_plugin = McpClientPlugin()
mcp_plugin.use_mcp_server("https://learn.microsoft.com/api/mcp")
mcp_plugin.use_mcp_server("https://example.com/mcp/weather")
mcp_plugin.use_mcp_server("https://example.com/mcp/pokemon")
```

### Connected MCP Servers

- **Microsoft Learn API** - `https://learn.microsoft.com/api/mcp`
  - Provides access to Microsoft documentation and learning resources
  - Demonstrates basic MCP server integration without authentication

- **GitHub Copilot API** - `https://api.githubcopilot.com/mcp/` (Optional)
  - Requires GitHub Personal Access Token (`GITHUB_PAT` environment variable)
  - Demonstrates authenticated MCP server integration with headers
  - Provides access to GitHub repositories, issues, and code analysis tools

**Authentication Example:**
```python
from microsoft.teams.mcpplugin import McpClientPluginParams

# This example uses a PersonalAccessToken, but you may get
# the user's oauth token as well by getting them to sign in
# and then using app.sign_in to get their token.
GITHUB_PAT = getenv("GITHUB_PAT")

# GitHub MCP server with Bearer token authentication
if GITHUB_PAT:
    mcp_plugin.use_mcp_server(
        "https://api.githubcopilot.com/mcp/",
        McpClientPluginParams(headers={
            "Authorization": f"Bearer {GITHUB_PAT}"
        })
    )
```

## How MCP Client Works

1. **Server Discovery** - MCP Client connects to remote servers via SSE protocol
2. **Tool Loading** - Remote tools are loaded and made available to the LLM
3. **Function Integration** - Tools are treated like local functions by ChatPrompt/Agent
4. **Remote Execution** - When LLM calls a tool, request is sent to remote MCP server
5. **Result Processing** - Response from remote server is returned to LLM for use

## Testing the MCP Client

### 1. Start the Client
```bash
python tests/mcp-client/src/main.py
```

### 2. Test Different Patterns

**Stateful Agent Pattern:**
```
agent Tell me about Microsoft Teams development
```

**Stateless ChatPrompt Pattern:**
```  
prompt What are the latest features in .NET?
```

**General Chat (uses Agent by default):**
```
Hello, I need help with Azure functions
```

**Get MCP Information:**
```
mcp info
```

### 3. Monitor in DevTools
- Navigate to the DevTools interface
- View MCP requests and responses in real-time
- See which remote tools are being called by the LLM
- Monitor latency and response data from remote servers

## Key Implementation Details

- **SSE Protocol** - Uses Server-Sent Events for remote MCP server communication
- **Plugin Architecture** - MCP Client integrates as a plugin with ChatPrompt and Agent
- **Tool Discovery** - Remote tools are automatically discovered and made available
- **Error Handling** - Graceful handling of remote server connectivity issues
- **Memory Management** - Proper memory handling for stateful vs stateless patterns
- **Type Safety** - Full typing support with proper async/await patterns

## Remote MCP Server Requirements

For connecting to your own MCP servers, ensure they:

1. **Support SSE Protocol** - Server must implement Server-Sent Events communication
2. **Follow MCP Specification** - Implement proper MCP protocol for tool definition and execution
3. **HTTPS Endpoint** - Server should be accessible via HTTPS URL
4. **Authentication** - If required, proper header-based authentication support

## Use Cases Demonstrated

- **Human-in-the-loop** - Remote tools can ask for user confirmation
- **External APIs** - Access to third-party services via MCP protocol  
- **Distributed Architecture** - Tools can be hosted separately from main application
- **Tool Sharing** - Multiple applications can use the same MCP servers
- **Scalability** - Remote tools can be scaled independently

This implementation provides a complete foundation for integrating external MCP servers into Teams applications, enabling powerful distributed AI agent architectures.