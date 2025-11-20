# Agent Framework vs ChatPrompt Comparison

This document compares the implementation differences between the agent-framework integration and the ChatPrompt approach in the Microsoft Teams Python SDK.

## Overview

Both approaches provide AI capabilities for Microsoft Teams bots, but with different programming models and abstractions:

- **agent-framework** (`main.py`): Uses the standalone agent-framework library with a simpler, more intuitive API
- **ChatPrompt** (`chat-prompt.py`): Uses the built-in microsoft.teams.ai ChatPrompt with more explicit configuration

## Key Differences

### 1. Setup & Imports

#### Agent Framework
```python
from agent_framework import ChatAgent, ChatMessageStore, MCPStreamableHTTPTool
from agent_framework.azure import AzureOpenAIChatClient
```

#### ChatPrompt
```python
from microsoft.teams.ai import ChatPrompt, Function, ListMemory
from microsoft.teams.openai import OpenAICompletionsAIModel
from microsoft.teams.mcpplugin import McpClientPlugin

# Requires model initialization
model = OpenAICompletionsAIModel()
```

**Key Difference**: Agent framework auto-initializes the client, while ChatPrompt requires explicit model creation.

---

### 2. Basic Message Handling

#### Agent Framework
```python
agent = ChatAgent(
    chat_client=AzureOpenAIChatClient(),
    instructions="You are a friendly but hilarious pirate robot.",
)
result = await agent.run(text)
await ctx.reply(result.text)
```

#### ChatPrompt
```python
prompt = ChatPrompt(model)
chat_result = await prompt.send(
    input=text,
    instructions="You are a friendly but hilarious pirate robot.",
)
if chat_result.response.content:
    message = MessageActivityInput(text=chat_result.response.content).add_ai_generated()
    await ctx.send(message)
```

**Key Differences**:
- Agent framework: `agent.run()` returns result with `.text` property
- ChatPrompt: `prompt.send()` returns result with `.response.content` property
- ChatPrompt requires manual construction of `MessageActivityInput` with AI-generated marker

---

### 3. Function/Tool Calling

#### Agent Framework
```python
def get_weather(
    location: Annotated[str, Field(description="The location to get the weather for.")],
) -> str:
    """Get the weather for a given location."""
    return f"The weather in {location} is sunny"

agent = ChatAgent(
    chat_client=AzureOpenAIChatClient(),
    instructions="...",
    tools=[get_weather, get_menu_specials],  # Pass functions directly
)
```

#### ChatPrompt
```python
class GetWeatherParams(BaseModel):
    location: Annotated[str, Field(description="The location to get the weather for.")]

def get_weather(params: GetWeatherParams) -> str:
    """Get the weather for a given location."""
    return f"The weather in {params.location} is sunny"

prompt = ChatPrompt(model)
prompt.with_function(
    Function(
        name="get_weather",
        description="Get the weather for a given location.",
        parameter_schema=GetWeatherParams,
        handler=get_weather,
    )
)
```

**Key Differences**:
- Agent framework: Functions use type annotations directly; parameters are individual function arguments
- ChatPrompt: Requires Pydantic model for parameters; function receives single params object
- Agent framework: Pass functions to `tools` list directly
- ChatPrompt: Wrap functions in `Function` objects with explicit configuration using `.with_function()`

---

### 4. Streaming

#### Agent Framework
```python
async for update in agent.run_stream(text):
    ctx.stream.emit(update.text)
```

#### ChatPrompt
```python
chat_result = await prompt.send(
    input=text,
    instructions="...",
    on_chunk=lambda chunk: ctx.stream.emit(chunk),
)

# Must emit final AI marker
if chat_result.response.content:
    ctx.stream.emit(MessageActivityInput().add_ai_generated())
```

**Key Differences**:
- Agent framework: Uses async iteration pattern with `run_stream()`
- ChatPrompt: Uses callback pattern with `on_chunk` parameter
- ChatPrompt requires manual emission of final AI-generated marker

---

### 5. Structured Output

#### Agent Framework
```python
class SentimentResult(BaseModel):
    sentiment: Literal["positive", "negative"]

result = await agent.run(text, response_format=SentimentResult)

if result.value:
    await ctx.reply(str(result.value))
```

#### ChatPrompt
```python
class SentimentResult(BaseModel):
    sentiment: Literal["positive", "negative"]

# NOTE: ChatPrompt does not support structured output natively
chat_result = await prompt.send(
    input=text,
    instructions="""
        Respond with ONLY a JSON object in this format: {"sentiment": "positive"}
        Do not include any other text.
    """,
)

# Manual parsing required
if chat_result.response.content:
    await ctx.reply(chat_result.response.content)
```

**Key Differences**:
- Agent framework: Native support via `response_format` parameter, returns typed `.value`
- ChatPrompt: **No native support** - requires workaround using instructions and manual JSON parsing

---

### 6. Conversation Memory

#### Agent Framework
```python
memory = ChatMessageStore()

agent = ChatAgent(
    chat_client=AzureOpenAIChatClient(),
    instructions="...",
    chat_message_store_factory=lambda: memory,
)
```

#### ChatPrompt
```python
memory_store: dict[str, ListMemory] = {}

def get_or_create_memory(conversation_id: str) -> ListMemory:
    if conversation_id not in memory_store:
        memory_store[conversation_id] = ListMemory()
    return memory_store[conversation_id]

memory = get_or_create_memory(ctx.activity.conversation.id)
prompt = ChatPrompt(model, memory=memory)
```

**Key Differences**:
- Agent framework: Uses `ChatMessageStore` with factory pattern
- ChatPrompt: Uses `ListMemory` passed directly to constructor; requires manual conversation tracking
- ChatPrompt requires developer to manage conversation-specific memory instances

---

### 7. MCP (Model Context Protocol) Integration

#### Agent Framework
```python
learn_mcp = MCPStreamableHTTPTool("microsoft-learn", "https://learn.microsoft.com/api/mcp")
agent = ChatAgent(
    chat_client=AzureOpenAIChatClient(),
    instructions="...",
    tools=[learn_mcp],  # MCP tools in same list as regular tools
)
```

#### ChatPrompt
```python
mcp_plugin = McpClientPlugin()
mcp_plugin.use_mcp_server("https://learn.microsoft.com/api/mcp")

prompt = ChatPrompt(model, memory=memory, plugins=[mcp_plugin])
```

**Key Differences**:
- Agent framework: MCP tools are treated as regular tools, added to `tools` list
- ChatPrompt: MCP requires plugin system, added to `plugins` list separately from functions

---

## Summary Table

| Feature | Agent Framework | ChatPrompt |
|---------|----------------|------------|
| **Setup** | Auto-initialized client | Manual model creation |
| **Tool Definition** | Type-annotated functions | Pydantic models + Function wrapper |
| **Streaming** | Async iteration | Callback pattern |
| **Structured Output** | Native via `response_format` | ❌ Not supported (workaround needed) |
| **Memory** | `ChatMessageStore` + factory | `ListMemory` + manual tracking |
| **MCP Integration** | Tools list | Plugins system |
| **Response Access** | `result.text` | `chat_result.response.content` |
| **Verbosity** | Less verbose | More explicit configuration |

## Recommendations

**Use Agent Framework when**:
- You want simpler, more intuitive APIs
- You need structured output support
- You prefer async iteration for streaming
- You want unified tool/MCP handling

**Use ChatPrompt when**:
- You need fine-grained control over the AI pipeline
- You're already using the microsoft.teams.ai ecosystem
- You want to use the plugin system
- You prefer explicit configuration over conventions

## Migration Tips

If migrating from ChatPrompt to Agent Framework:

1. **Functions**: Remove Pydantic parameter models, use type annotations directly
2. **Memory**: Replace `ListMemory` with `ChatMessageStore` and use factory pattern
3. **Streaming**: Replace `on_chunk` callbacks with `async for` iteration
4. **MCP**: Move MCP from plugins to tools list
5. **Response handling**: Change `.response.content` to `.text`
6. **Structured output**: Use `response_format` parameter instead of instruction-based workaround
