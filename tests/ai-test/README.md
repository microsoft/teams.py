# Sample: AI

A sample demonstrating various AI capabilities in the Python Teams SDK.

## Prerequisites

- Python 3.12 or later
- UV package manager
- An Microsoft 365 development account. If you don't have one, you can get one for free by signing up for the [Microsoft 365 Developer Program](https://developer.microsoft.com/microsoft-365/dev-program).

## Setup

1. Install dependencies:

```bash
uv sync
```

2. Set up your `.env` file with your Azure OpenAI API key (or OpenAI API Key):

```bash
AZURE_OPENAI_API_KEY=<your_azure_openai_api_key>
AZURE_OPENAI_ENDPOINT=<your_azure_openai_endpoint>
AZURE_OPENAI_MODEL=<your_azure_openai_model_deployment_name>
AZURE_OPENAI_API_VERSION=<your_azure_openai_api_version>

# Alternatively, set the OpenAI API key:
OPENAI_API_KEY=<sk-your_openai_api_key>
```

## Run

```bash
# Activate virtual environment
source .venv/bin/activate  # On macOS/Linux
# .venv\Scripts\Activate   # On Windows

# Run the AI test
python tests/ai-test/src/main.py
```

## Usage

From Teams, DevTools, or your test client, use any of the following commands to trigger specific scenarios:

| Scenario               | Usage                                   | Description                                               |
| ---------------------- | --------------------------------------- | --------------------------------------------------------- |
| Simple LLM check       | `hi`                                    | Basic ChatPrompt with pirate personality                  |
| Function calling       | `pokemon <pokemon_name>`                | Single function calling - searches Pokemon via PokeAPI    |
| Multi-Function calling | `weather`                               | Multiple function calling - gets location then weather    |
| Streaming              | `stream <your query>`                   | Shows streaming responses in verbose language             |
| Citations              | `citations`                             | Demonstrates citation functionality with position markers |
| Model switching        | `model completions` / `model responses` | Switch between Chat Completions and Responses API models  |
| Plugin stats           | `plugin`                                | Shows AI plugin function call statistics                  |
| Memory management      | `memory clear`                          | Clears conversation memory                                |
| Feedback collection    | `feedback demo`                         | Demonstrates message feedback with like/dislike buttons   |
| Feedback statistics    | `feedback stats <message_id>`           | Shows feedback summary for a specific message             |
| Stateful interactions  | `<any other message>`                   | Shows persistent conversation memory across interactions  |

## Features Demonstrated

### Core AI Functionality

- **ChatPrompt and Agent** - Basic LLM interaction patterns
- **String instructions** - Simple instruction passing (vs SystemMessage objects)
- **Model switching** - Runtime switching between different AI models

### Function Calling

- **Single functions** - Pokemon search with real API integration
- **Multiple functions** - Location detection followed by weather lookup
- **Error handling** - Proper exception handling for API failures

### Advanced Features

- **Streaming responses** - Real-time response streaming with group/1:1 handling
- **Memory management** - Per-conversation memory with manual clearing
- **Custom plugins** - AI plugin system with lifecycle hooks
- **Citations** - Position-based citations with proper formatting
- **Feedback collection** - Message feedback with like/dislike reactions and text feedback

### Best Practices

- **AI-generated indicators** - All AI responses marked appropriately
- **Modular handlers** - Clean separation of concerns across files
- **Pattern matching** - Uses `app.on_message_pattern` for command routing
- **Type safety** - Full pyright compliance with proper typing

## Architecture

The sample follows a modular architecture:

- `main.py` - Main application with pattern-based message handlers
- `handlers/` - Separate modules for different AI functionality:
  - `function_calling.py` - Pokemon and weather function implementations
  - `memory_management.py` - Stateful conversation handling
  - `citations.py` - Citation demo functionality
  - `plugins.py` - Custom AI plugin implementation
  - `feedback_management.py` - Message feedback collection and storage

This structure mirrors the TypeScript AI test implementation for consistency across language implementations.
