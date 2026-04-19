# Memory Palace
*A unified memory layer that fuses your real life (via Omi) and your agent's actions (via Ara) into a single navigable knowledge graph.*

---

## Architecture Overview

```
Real World (conversations, screen)
        ↓
   Omi Desktop/Mobile App
        ↓ webhook on memory creation
   FastAPI Ingest Server
        ↓
   Memory Graph (NetworkX + SQLite)
        ↑
   Ara Agent (reads + writes to graph)
        ↓
   Frontend Visualization (palace/city/constellation)
```

---

## Backend

### 1. Memory Graph (`graph.py`)

```python
@dataclass
class MemoryNode:
    id: str
    content: str
    embedding: list[float]
    node_type: str  # "omi_memory" | "ara_tool_call" |
                    # "ara_message" | "ara_observation"
    timestamp: datetime
    source: str     # "omi" | "ara"
    metadata: dict  # raw payload, tool name, etc.

@dataclass
class MemoryEdge:
    source_id: str
    target_id: str
    edge_type: str  # "semantic" | "temporal" | "causal"
    weight: float
```

### 2. Ingest Layer (`ingest.py`)

- `ingest_omi_memory(payload)` — receives Omi webhook, embeds, finds neighbors, creates nodes and edges
- `ingest_ara_event(event)` — called after every Ara tool call, same pipeline
- `find_neighbors(embedding, k=5)` — cosine similarity search over existing nodes, returns top-k
- `create_edges(new_node, neighbors)` — semantic edges based on similarity score, temporal edge to previous node

### 3. FastAPI Server (`server.py`)

```
POST /webhook/omi      ← Omi fires this on memory creation
POST /webhook/ara      ← Ara fires this after tool calls
GET  /graph            ← frontend polls this for visualization
GET  /query?q=...      ← natural language search over palace
```

### 4. Ara Agent (`app.py`)

```python
@ara.tool
def query_memory_palace(question: str) -> dict:
    # semantic search over graph before acting

@ara.tool
def web_search(query: str) -> dict:
    result = real_search(query)
    ingest_ara_event("web_search", query, result)
    return result

@ara.tool
def recall_context(topic: str) -> dict:
    # retrieve relevant nodes from graph
    # returns both omi memories AND past ara actions

ara.Automation(
    "memory-palace-agent",
    system_instructions=(
        "Before answering anything, call query_memory_palace "
        "to check what you already know. Every action you take "
        "is logged to your memory palace automatically."
    ),
    tools=[query_memory_palace, web_search, recall_context],
)
```

---

## Math Layer

Edge weight formulation:

- **Semantic edge weight**: cosine similarity between embeddings, threshold at 0.7
- **Temporal decay**: edges to older nodes get lower weight over time using exponential decay `w(t) = e^(-λt)`
- **Causal edge**: tool call → result always weight 1.0, directional
- **Node importance**: PageRank over the graph to surface the most connected memories

---

## Frontend

**Tech:** React + D3.js or Three.js for 3D

**Visual options (pick one, build it well):**
- **City**: each knowledge domain is a neighborhood, buildings = individual memories, height = importance (PageRank score)
- **Constellation**: nodes are stars, edges are lines, brightness = recency
- **Palace**: rooms = domains, objects = memories, corridors = edges

**Key UI components:**
- Live graph that updates as new memories arrive (poll `/graph` every 2s)
- Node detail panel on click: shows raw content, source (Omi vs Ara), timestamp
- Color coding: blue = Omi memory, orange = Ara action, green = Ara observation
- Search bar that hits `/query` and highlights matching nodes

---

## Team Split

| Person | Owns |
|---|---|
| Seokhyun + ML friend | `graph.py`, `ingest.py`, embedding pipeline, Ara agent tool wrapping |
| Math friend | Edge weight formulas, temporal decay, PageRank scoring, similarity thresholds |
| Full stack friend | `server.py`, FastAPI endpoints, frontend visualization, Omi webhook setup |

---

## Tech Stack

| Component | Tool |
|---|---|
| Agent deployment | Ara SDK |
| Real-life memory capture | Omi desktop/mobile |
| Graph store | NetworkX + SQLite |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| API server | FastAPI |
| Frontend | React + D3.js or Three.js |
| Webhook tunneling (dev) | ngrok |

---

## Hour-by-Hour Plan

| Hour | Work |
|---|---|
| 1 | Graph data model, SQLite setup, basic embedding pipeline, Omi webhook receiving and parsing |
| 2 | Neighbor search, edge creation logic, Ara tool wrapping with memory logging |
| 3 | FastAPI server fully wired, Ara agent deployed and talking to graph, end-to-end test: Omi memory → graph → Ara retrieves it |
| 4 | Frontend starts, basic node rendering, polling live graph state |
| 5 | Frontend polish, color coding, node detail panel, search working |
| 6 | Full demo rehearsal, fix broken edges, prepare pitch |

---

## Demo Script (5 minutes)

1. Show empty palace
2. Have a 2-minute conversation while Omi runs in background
3. Omi fires webhook, memories appear in palace in real time
4. Ask Ara agent something related to the conversation
5. Show agent calling `query_memory_palace`, finding the Omi memory, answering with it
6. Agent does a web search, show that action also appearing in the palace as a new node connected to the Omi memory
7. Show the graph: two types of nodes, edges between them, palace growing

---

## One Sentence Pitch

*Every AI agent starts from zero — ours builds a memory from your actual life that compounds forever.*