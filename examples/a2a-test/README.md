# A2A Sample — Teams Data Assistant

A Teams bot that reads shared files and produces Adaptive Card visualizations. The data-analyst is
exposed over the **A2A (Agent-to-Agent) protocol** as a separate process, showing how a Teams bot
can host capabilities that external, non-Teams systems can consume.

## What this demonstrates

- **A2A as-a-service** — data-analyst runs in a separate process and exposes a standard A2A endpoint that any A2A client can call.
- **Local sub-agent** — `file_search` is a dedicated agent-framework `Agent` for extracting context from files, consumed in-process via `.as_tool()`.
- **Safe concurrent conversational memory** — `AgentSession` preserves prior turns for follow-ups; per-conversation `asyncio.Lock` keeps overlapping messages from racing on session history.
- **Adaptive Cards for data viz** — the data-analyst agent programmatically builds bar/line/pie/table Adaptive Cards and returns them for Teams to render; multiple cards per turn.

## Architecture

```
┌─────────────────── Teams bot process (:3978) ───────────────────┐
│  Teams  ─►  Orchestrator Agent  ─►  search_files   (sub-agent)  │
│                                                                 │
│                                 ─►  visualize_data ─────HTTP────┼──►  Data Analyst
│                                                                 │      A2A process (:3979)
└─────────────────────────────────────────────────────────────────┘
```

- `main.py` — Teams bot + orchestrator Agent (OpenAI) with `search_files` and `visualize_data` tools.
- `file_search/` — plain agent-framework `Agent` with a `download_file` tool. Consumed in-process
  via `.as_tool()`. Not exposed externally — no A2A.
- `data_analyst/` — an A2A server that runs as a **separate process**, called over HTTP. Useful
  pattern when the sub-agent has external consumers or lives elsewhere.
- `a2a_utils.py` — extracts card dicts from A2A responses.

## Run

Set Azure OpenAI + bot credentials in `.env`:

```
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_MODEL=...
AZURE_OPENAI_API_VERSION=...

CLIENT_ID=...
CLIENT_SECRET=...
TENANT_ID=...
```

The data-analyst runs as a **separate process** (port `3979`) so the Teams bot makes a real HTTP A2A
call to it.

```bash
# Terminal 1 — data-analyst A2A server (port 3979)
cd src
uv run --env-file ../.env python -m data_analyst
```

```bash
# Terminal 2 — Teams bot (port 3978); calls the data-analyst at :3979 over A2A
uv run src/main.py
```

## Example interactions

**Chart from inline data:**

> Visualize revenue by region: North $45,000, South $32,000, East $61,000, West $28,000

Expected: bar chart Adaptive Card.

**Chart from a shared file** — upload `sales.csv` (monthly sales data included) and ask:

> Chart the monthly sales.

Expected: the orchestrator calls `search_files` to read the CSV, then `visualize_data` to render the
chart.

**Follow-up in same conversation:**

> Now show it as a pie chart and a summary table.

Expected: agent remembers the previous data via `AgentSession` history — no need to re-read the file.

## Calling the A2A server from outside

The data-analyst exposes a standard A2A endpoint, so any A2A-compatible client can invoke it.
While the data-analyst process is running, an external caller can do:

```python
import asyncio
from agent_framework_a2a import A2AAgent

async def main():
    client = A2AAgent(url="http://localhost:3979/data-analyst/")
    response = await client.run(
        "Bar chart of revenue by region. Data:\n"
        "North,45000\nSouth,32000\nEast,61000\nWest,28000"
    )
    print(response.text)  # JSON payload with {"cards": [...AdaptiveCard...]}

asyncio.run(main())
```

## Known limitations (sample-grade)

- **Unbounded memory.** The `_sessions` dict and each `AgentSession`'s history grow without limit.
  A production bot would add LRU eviction on the session map and a bounded/compacting history provider.
- **File size.** `file_search` inlines the full file contents into the LLM prompt, so anything
  beyond roughly 100 KB will exceed the context window. A production version would chunk the file
  and index it (vector store, keyword search, etc.) before answering.
