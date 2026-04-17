# A2A Sample — Teams Data Assistant

A Teams bot that orchestrates two **A2A** (Agent-to-Agent protocol) sub-agents to read shared files
and produce Adaptive Card visualizations from data.

## Architecture

```
┌─────────────────── Teams bot process (:3978) ───────────────────┐
│  Teams  ─►  Orchestrator Agent  ─►  search_files   (in-process) │
│                                                                 │
│                                 ─►  visualize_data ─────HTTP────┼──►  Data Analyst
│                                                                 │      A2A process (:3979)
└─────────────────────────────────────────────────────────────────┘
```

- `main.py` — Teams bot + orchestrator Agent (OpenAI) with `search_files` and `visualize_data` tools.
- `file_search/` — A2A server mounted **in-process** on the Teams bot's FastAPI adapter.
- `data_analyst/` — A2A server that runs as a **separate process**, called over HTTP.
- `a2a_utils.py` — extracts card dicts from A2A responses.

The split shows two valid deployment shapes for A2A: co-located (file_search) and distributed
(data_analyst). The Teams bot doesn't care — both look the same through `A2AAgent`.

## Run

Set Azure OpenAI credentials in `.env`:

```
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_MODEL=...
AZURE_OPENAI_API_VERSION=...
```

The data-analyst runs as a **separate process** (port `3979`) so the Teams bot makes a real HTTP A2A
call to it. Start them in two terminals — both run from `src/` so Python can find the packages:

```bash
# Terminal 1 — data-analyst A2A server
cd src
uv run --env-file ../.env python -m data_analyst
```

```bash
# Terminal 2 — Teams bot (hosts file-search A2A server in-process at :3978, calls data-analyst at :3979)
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

## Known limitations (sample-grade)

- **Unbounded memory.** The `_sessions` dict and each `AgentSession`'s history grow without limit.
  A production bot would add LRU eviction on the session map and a bounded/compacting history provider.
- **File size.** `file_search` inlines the full file contents into the LLM prompt, so anything
  beyond roughly 100 KB will exceed the context window. A production version would chunk the file
  and index it (vector store, keyword search, etc.) before answering.
