import uvicorn
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ingest import ingest_omi_memory, ingest_ara_event, embed, find_neighbors
from graph import memory_graph

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AraEvent(BaseModel):
    event_type: str
    input: str
    output: str


@app.post("/webhook/omi")
async def webhook_omi(payload: dict):
    node = ingest_omi_memory(payload)
    return {"status": "ok", "node_id": node.id}


@app.post("/webhook/ara")
async def webhook_ara(event: AraEvent):
    node = ingest_ara_event(event.event_type, event.input, event.output)
    return {"status": "ok", "node_id": node.id}


@app.get("/graph")
async def get_graph():
    pagerank = memory_graph.compute_pagerank()
    nodes = [
        {
            "id": node.id,
            "content": node.content,
            "node_type": node.node_type,
            "source": node.source,
            "timestamp": node.timestamp,
            "metadata": node.metadata,
            "pagerank": pagerank.get(node.id, 0.0),
        }
        for node in memory_graph.get_all_nodes()
    ]
    edges = [
        {
            "source_id": edge.source_id,
            "target_id": edge.target_id,
            "edge_type": edge.edge_type,
            "weight": edge.weight,
        }
        for edge in memory_graph.get_all_edges()
    ]
    return {"nodes": nodes, "edges": edges}


@app.get("/query")
async def query(q: str = Query(...)):
    embedding = embed(q)
    neighbors = find_neighbors(embedding, k=10)
    results = [{"node": {
        "id": node.id,
        "content": node.content,
        "node_type": node.node_type,
        "source": node.source,
        "timestamp": node.timestamp,
        "metadata": node.metadata,
    }, "score": score} for node, score in neighbors]
    return {"results": results}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
