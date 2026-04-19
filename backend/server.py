from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from graph import get_graph
from ingest import ingest_ara_event, ingest_omi_memory, semantic_search

app = FastAPI(title="Memory Palace API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/webhook/omi")
async def omi_webhook(payload: dict):
    node = ingest_omi_memory(payload)
    return {"success": True, "node_id": node.id}


@app.post("/webhook/ara")
async def ara_webhook(event: dict):
    node = ingest_ara_event(
        event.get("event_type", "tool_call"),
        event.get("input", ""),
        event.get("output", ""),
        event.get("metadata", {}),
    )
    return {"success": True, "node_id": node.id}


@app.get("/graph")
async def graph_endpoint():
    return get_graph().to_dict()


@app.get("/query")
async def query(q: str, k: int = 10):
    results = semantic_search(q, k=k)
    return {
        "query": q,
        "results": [
            {
                "id": node.id,
                "content": node.content,
                "node_type": node.node_type,
                "timestamp": node.timestamp.isoformat(),
                "source": node.source,
                "score": round(score, 4),
            }
            for node, score in results
        ],
    }


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
