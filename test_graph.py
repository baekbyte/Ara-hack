"""Quick smoke test for the Memory Palace ingestion + retrieval pipeline."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ["MEMORY_PALACE_DB"] = str(Path(tempfile.gettempdir()) / "test_memory_palace.db")

import db as db_module
import graph as graph_module
import ingest
import retrieval


def separator(title: str) -> None:
    print(f"\n{'=' * 52}")
    print(f"  {title}")
    print("=" * 52)


db_path = Path(os.environ["MEMORY_PALACE_DB"])
if db_path.exists():
    db_path.unlink()

db_module.sqlite_store = db_module.SQLiteStore(str(db_path))
graph_module.memory_graph = graph_module.MemoryGraph(store=db_module.sqlite_store)
ingest.memory_graph = graph_module.memory_graph
retrieval.memory_graph = graph_module.memory_graph


separator("Ingesting Omi memories")
omi_payloads = [
    {
        "id": "mem-1",
        "summary": "Discussed the Ara and Omi integration plan for the hackathon demo.",
        "action_items": ["Wire FastAPI endpoints", "Deploy Ara automation"],
        "people": ["Alice", "Bob"],
    },
    {
        "id": "mem-2",
        "transcript": "We were debugging the graph visualization and talking about recent transcript retrieval.",
        "people": ["Charlie"],
        "client": "desktop",
    },
]
for payload in omi_payloads:
    node = ingest.ingest_omi_memory(payload)
    print(f"[omi] {node.id[:20]:20s} {node.content[:65]}")


separator("Ingesting transcript chunks")
transcript_payloads = [
    {"session_id": "sess-1", "chunk_id": "1", "text": "Need the recent context endpoint for Ara.", "speaker": "user"},
    {"session_id": "sess-1", "chunk_id": "2", "text": "Also log important Ara actions back into the graph.", "speaker": "assistant"},
]
for payload in transcript_payloads:
    node = ingest.ingest_omi_transcript(payload)
    print(f"[transcript] {node.id[:20]:20s} {node.content[:65]}")


separator("Ingesting Ara action")
ara_node = ingest.ingest_ara_event(
    {
        "action_type": "ara_message",
        "content": "Outlined the Memory Palace integration plan and next implementation steps.",
        "metadata": {"tool_name": "planner"},
    }
)
print(f"[ara] {ara_node.id[:20]:20s} {ara_node.content[:65]}")


separator("Context pack")
context = retrieval.build_context_pack("What was I just working on?", limit=5)
print(context["summary"])
print(f"similar_memories={len(context['similar_memories'])}")
print(f"recent_transcript_chunks={len(context['recent_transcript_chunks'])}")
print(f"related_ara_actions={len(context['related_ara_actions'])}")


separator("Graph stats")
stats = graph_module.memory_graph.stats()
for key, value in stats.items():
    print(f"{key}: {value}")


separator("Cleanup")
if db_path.exists():
    db_path.unlink()
print("Removed test database")
print("Smoke test passed")
