# A2A Sample — Teams Knowledge-Base Assistant

A Teams bot that answers questions from Northwind Co.'s internal docs (HR, expense, remote work,
security, engineering handbook, revenue/metrics/headcount tables). The KB agent is exposed over
the **A2A (Agent-to-Agent) protocol** as a separate process, so external, non-Teams systems can
consume it.

## Components

- **Host agent** (Teams bot process) — routes messages; owns the `ask_kb` tool.
- **`ask_kb`** — uses `A2AAgent` from `agent_framework_a2a` to call the KB agent at
  `http://localhost:3979/kb-agent/`. Extracts Adaptive Card dicts from the response's DataParts.
- **KB agent** (separate process, `kb_agent/`) — a stateless A2A server backed by Azure AI Search.
  Tools:
  - `search_kb` — full-text search against the Azure AI Search index.
  - `render_answer` — text answer + cited sources (Adaptive Card).
  - `render_chart` — chart or table + cited sources (Adaptive Card). Used when the question is
    quantitative and the retrieved snippets carry a data table.
  Card dicts are returned as an A2A `DataPart`; the host agent extracts them and Teams renders
  them natively.

## Architecture

```
┌──────── Teams bot process (:3978) ────────┐
│  Teams ─► Host Agent ─────► ask_kb ───────┼──HTTP/A2A──► KB Agent (:3979)
└───────────────────────────────────────────┘                    │
                                                                 ▼
                                                      Azure AI Search index
                                                      (populated by ingest.py)
```

- `main.py` — Teams entry point; per-conversation `AgentSession` + `asyncio.Lock`.
- `host_agent.py` — host agent with the `ask_kb` tool; wraps `A2AAgent`.
- `kb_agent/` — A2A server. `index.py` wraps an Azure AI Search client; `agent.py` runs the agent
  with `search_kb` / `render_answer` / `render_chart` tools (stateless per request); `ingest.py`
  is a one-shot script that chunks `knowledge_base/*.md` and uploads the chunks to Azure Search.

## Prerequisites

- An [Azure AI Foundry](https://ai.azure.com) project with a deployed model. The bot's Service Principal needs the **Azure AI User** role on the Foundry project.
- A Teams bot registration (App ID + password)
- An Azure AI Search resource. Two things to configure on it:
   - **Enable RBAC on the resource itself.** Portal → the Search resource → **Keys** blade →
     **API access control** → switch from "API Key" to "Role-based access control" (or "Both").
     Save. Without this, role assignments below have no effect — the resource rejects token auth.
   - Grant the bot's Service Principal these role assignments:
     - **Search Service Contributor** — needed by `ingest.py` to create the index.
     - **Search Index Data Contributor** — needed by `ingest.py` to upload documents, and by the
       running agent to read them at query time (a reader role is sufficient if you only run the
       agent after ingesting once).

### .env

```
FOUNDRY_PROJECT_ENDPOINT=https://<your-project>.services.ai.azure.com
FOUNDRY_MODEL=<your-model>

AZURE_SEARCH_ENDPOINT=https://<your-search-resource>.search.windows.net
AZURE_SEARCH_INDEX_NAME=northwind-kb

TENANT_ID=...
CLIENT_ID=...
CLIENT_SECRET=...

# Optional — defaults to http://localhost:3979/kb-agent/
# KB_AGENT_URL=http://kb-agent.internal/kb-agent/
```


## Run

### 1. One-time: ingest the corpus into Azure AI Search

```bash
cd src
uv run --env-file ../.env python -m kb_agent.ingest
```

This creates the index (if missing), chunks every `kb_agent/knowledge_base/*.md` file by `##`
section, and uploads each chunk as a document. Re-run this whenever the corpus changes.

### 2. Start the KB agent and the Teams bot

```bash
# Terminal 1 — KB agent A2A server (port 3979)
cd src
uv run --env-file ../.env python -m kb_agent
```

```bash
# Terminal 2 — Teams bot (port 3978); calls the KB agent at :3979 over A2A
uv run src/main.py
```

## Example interactions

**Policy question (answer card):**

> How much PTO do I accrue in my first year?

The agent retrieves from `pto_policy.md` and renders an Adaptive Card with the answer and the PTO
policy source.

**Quantitative question (chart card):**

> Chart our engineering headcount over the last two years.

The agent retrieves from `headcount.md`, parses the headcount-over-time table, and renders a
line-chart Adaptive Card citing the headcount doc.

**Follow-up in same conversation:**

> What's total company headcount at end of Q4?

The KB agent is stateless, so this query is answered independently — but it still resolves cleanly
because the host agent's Teams-side session carries the surrounding conversation context that
shaped the user's phrasing.

## Calling the A2A server from outside

The KB agent exposes a standard A2A endpoint, so any A2A-compatible client can invoke it.
While the KB agent process is running, an external caller can do:

```python
import asyncio
from agent_framework_a2a import A2AAgent

async def main():
    client = A2AAgent(url="http://localhost:3979/kb-agent/")
    response = await client.run("What's the expense limit for international meals?")
    print(response.text)

asyncio.run(main())
```

## Known limitations (sample-grade)

- **Keyword search only.** `ingest.py` uploads text fields; `search_kb` uses Azure Search's default
  BM25 retrieval. For better recall on paraphrased queries, add a vector field (e.g. 1536-dim for
  `text-embedding-3-small`), generate embeddings at ingest time, and issue hybrid queries with
  `vector_queries=...`. Optionally enable Azure's semantic ranker for re-ranking.
- **Manual re-ingest on corpus change.** `ingest.py` is a one-shot; there's no change detection or
  incremental update. A production version would watch the source and sync.
- **Unbounded host-agent memory.** The host agent's `_sessions` dict in `main.py` grows without
  limit. A production bot would add LRU eviction and a bounded/compacting history provider. The
  KB agent itself is stateless so it has no such concern.
