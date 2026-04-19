import uuid
from datetime import datetime
from typing import Optional

import numpy as np

from graph import MemoryEdge, MemoryNode, memory_graph

_model = None
_previous_node_id: Optional[str] = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed(text: str) -> list[float]:
    return _get_model().encode(text).tolist()


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    va = np.array(a)
    vb = np.array(b)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def find_neighbors(
    embedding: list[float], k: int = 5
) -> list[tuple[MemoryNode, float]]:
    results = []
    for node in memory_graph.get_all_nodes():
        if not node.embedding:
            continue
        score = _cosine_similarity(embedding, node.embedding)
        if score >= 0.7:
            results.append((node, score))
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:k]


def create_edges(
    new_node: MemoryNode,
    neighbors: list[tuple[MemoryNode, float]],
    previous_node_id: Optional[str],
):
    for neighbor, score in neighbors:
        if neighbor.id == new_node.id:
            continue
        memory_graph.add_edge(
            MemoryEdge(
                source_id=new_node.id,
                target_id=neighbor.id,
                edge_type="semantic",
                weight=score,
            )
        )

    if previous_node_id and memory_graph.get_node(previous_node_id):
        memory_graph.add_edge(
            MemoryEdge(
                source_id=previous_node_id,
                target_id=new_node.id,
                edge_type="temporal",
                weight=1.0,
            )
        )


def ingest_omi_memory(payload: dict) -> MemoryNode:
    global _previous_node_id

    content = (
        payload.get("text")
        or payload.get("transcript")
        or (payload.get("structured") or {}).get("overview")
        or ""
    )

    embedding = embed(content)
    neighbors = find_neighbors(embedding)

    node = MemoryNode(
        id=str(uuid.uuid4()),
        content=content,
        embedding=embedding,
        node_type="omi_memory",
        timestamp=datetime.utcnow(),
        source="omi",
        metadata=payload,
    )

    memory_graph.add_node(node)
    create_edges(node, neighbors, _previous_node_id)
    _previous_node_id = node.id
    return node


def ingest_ara_event(
    event_type: str, input_data: str, output_data: str
) -> MemoryNode:
    global _previous_node_id

    content = f"{event_type}: {input_data} -> {output_data}"
    embedding = embed(content)
    neighbors = find_neighbors(embedding)

    node = MemoryNode(
        id=str(uuid.uuid4()),
        content=content,
        embedding=embedding,
        node_type="ara_tool_call",
        timestamp=datetime.utcnow(),
        source="ara",
        metadata={"event_type": event_type, "input": input_data, "output": output_data},
    )

    memory_graph.add_node(node)
    create_edges(node, neighbors, _previous_node_id)
    _previous_node_id = node.id
    return node
