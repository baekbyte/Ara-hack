# Memory Palace (Ara-hack)

A **unified memory graph** that can ingest **real-life memories** (e.g. from [Omi](https://github.com/BasedHardware/omi) via webhook) and **agent activity** (Ara-style events), then visualize and search them in one place.

## What this repo does

- **Backend (FastAPI)** — Persists a directed graph of memory **nodes** and **edges** in **SQLite** (`memory_palace.db`), with an in-memory **NetworkX** view for structure and queries.
- **Embeddings** — Uses **sentence-transformers** (`all-MiniLM-L6-v2`) to embed text. New nodes are linked to similar existing nodes (**semantic** edges above a cosine threshold) and to the most recent prior node (**temporal** edges).
- **HTTP API** — Webhooks to append data, JSON endpoints to read the graph and run semantic search.
- **Frontend (React + Vite)** — **3D “constellation”** view (`react-force-graph-3d`), polls the graph every 2s, supports search highlighting and a node detail panel.
- **Ara stub (`app.py`)** — Example functions that call the API over HTTP (`query_memory_palace`, `web_search` stub, `recall_context`). The real **Ara SDK** integration is commented as a TODO for swap-in at deploy time.

## API (backend)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/webhook/omi` | Ingest an Omi-style memory payload; creates an `omi_memory` node. |
| `POST` | `/webhook/ara` | Ingest an agent event (`event_type`, `input`, `output`, `metadata`); creates Ara-labeled nodes. |
| `GET` | `/graph` | Full graph as JSON (`nodes`, `edges`). |
| `GET` | `/query?q=...&k=10` | Semantic search over stored node embeddings. |

There is also a **catch-all debug route** that logs incoming requests (useful while wiring webhooks).

## Project layout

```
backend/
  server.py    # FastAPI app + routes
  graph.py     # MemoryNode / MemoryEdge, SQLite + NetworkX
  ingest.py    # embed, neighbors, ingest_omi_memory, ingest_ara_event, semantic_search
  app.py       # httpx client + tool-shaped functions for Ara (stub)
  requirements.txt
frontend/
  src/         # React UI (constellation, search, legend, node panel)
PLAN.md        # Hackathon design notes (architecture & demo script)
```

## Quick start

**Backend** (from `backend/`; Python 3.9+ recommended):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
python server.py
```

Server listens on **http://localhost:8000**. Embeddings need a working **PyTorch** install; `requirements.txt` pins `torch>=2.4` so `sentence-transformers` loads correctly.

**Frontend**:

```bash
cd frontend
npm install
npm run dev
```

Point the UI at the API URL in `frontend/src/App.jsx` (`API = 'http://localhost:8000'`) if your backend host differs.

## Omi integration

Point Omi (or any client) at `POST http://<your-host>:8000/webhook/omi` with a JSON body; the ingest layer accepts `content` or `text` (or falls back to stringifying the payload). For tunneling during local dev, tools like **ngrok** work well.

## License / credits

Hackathon / team project; Omi is a separate open-source product by Based Hardware.
