# A2A Sample — Teams Data Assistant

A Teams bot that reads shared files and produces Adaptive Card visualizations. The data-analyst is
exposed over the **A2A (Agent-to-Agent) protocol** as a separate process, showing how a Teams bot
can host capabilities that external, non-Teams systems can consume.

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

Set Azure OpenAI credentials in `.env`:

```
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_MODEL=...
AZURE_OPENAI_API_VERSION=...
```

The data-analyst runs as a **separate process** (port `3979`) so the Teams bot makes a real HTTP A2A
call to it. Start both from the `src/` directory so Python can resolve the packages:

```bash
# Terminal 1 — data-analyst A2A server (port 3979)
cd src
uv run --env-file ../.env python -m data_analyst
```

```bash
# Terminal 2 — Teams bot (port 3978); calls the data-analyst at :3979 over A2A
cd src
uv run --env-file ../.env python main.py
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

The data-analyst exposes a standard A2A endpoint, so any A2A-compatible client can invoke it — no
Teams required. This is the "Teams as A2A server" story: a Teams bot can host capabilities (here,
chart generation) that external systems consume.

While the data-analyst process is running (Terminal 1), an external caller can do:

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
