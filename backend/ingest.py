import math
import uuid
from datetime import datetime
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from graph import MemoryEdge, MemoryNode, get_graph

_model: Optional[SentenceTransformer] = None

SIMILARITY_THRESHOLD = 0.7
TEMPORAL_DECAY_LAMBDA = 0.01  # per hour


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed(text: str) -> list[float]:
    return get_model().encode(text).tolist()


def cosine_similarity(a: list[float], b: list[float]) -> float:
    a_arr, b_arr = np.array(a), np.array(b)
    denom = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
    if denom == 0:
        return 0.0
    return float(np.dot(a_arr, b_arr) / denom)


def temporal_weight(then: datetime, now: datetime) -> float:
    """Exponential decay: w(t) = e^(-λt) where t is hours elapsed."""
    delta_hours = (now - then).total_seconds() / 3600
    return math.exp(-TEMPORAL_DECAY_LAMBDA * delta_hours)


def find_neighbors(embedding: list[float], k: int = 5) -> list[tuple[MemoryNode, float]]:
    nodes = get_graph().get_all_nodes()
    scored = [
        (node, cosine_similarity(embedding, node.embedding))
        for node in nodes
    ]
    above_threshold = [(n, s) for n, s in scored if s >= SIMILARITY_THRESHOLD]
    above_threshold.sort(key=lambda x: -x[1])
    return above_threshold[:k]


def create_edges(new_node: MemoryNode, neighbors: list[tuple[MemoryNode, float]]):
    graph = get_graph()
    now = datetime.utcnow()

    for neighbor, sim in neighbors:
        graph.add_edge(MemoryEdge(
            source_id=new_node.id,
            target_id=neighbor.id,
            edge_type="semantic",
            weight=sim,
        ))

    # Temporal edge from the most recent prior node to the new one
    all_nodes = [n for n in graph.get_all_nodes() if n.id != new_node.id]
    if all_nodes:
        prev = max(all_nodes, key=lambda n: n.timestamp)
        graph.add_edge(MemoryEdge(
            source_id=prev.id,
            target_id=new_node.id,
            edge_type="temporal",
            weight=temporal_weight(prev.timestamp, now),
        ))


def ingest_omi_memory(payload: dict) -> MemoryNode:
    content = payload.get("content") or payload.get("text") or str(payload)
    embedding = embed(content)
    node = MemoryNode(
        id=str(uuid.uuid4()),
        content=content,
        embedding=embedding,
        node_type="omi_memory",
        timestamp=datetime.utcnow(),
        source="omi",
        metadata=payload,
    )
    graph = get_graph()
    graph.add_node(node)
    neighbors = [(n, s) for n, s in find_neighbors(embedding) if n.id != node.id]
    create_edges(node, neighbors)
    return node


def ingest_ara_event(event_type: str, input_data: str, output_data: str, metadata: dict = None) -> MemoryNode:
    content = f"{event_type}: {input_data} → {output_data}"
    embedding = embed(content)

    node_type_map = {"tool_call": "ara_tool_call", "message": "ara_message", "observation": "ara_observation"}
    node = MemoryNode(
        id=str(uuid.uuid4()),
        content=content,
        embedding=embedding,
        node_type=node_type_map.get(event_type, "ara_tool_call"),
        timestamp=datetime.utcnow(),
        source="ara",
        metadata={"event_type": event_type, "input": input_data, "output": output_data, **(metadata or {})},
    )
    graph = get_graph()
    graph.add_node(node)
    neighbors = [(n, s) for n, s in find_neighbors(embedding) if n.id != node.id]
    create_edges(node, neighbors)
    return node


def semantic_search(query: str, k: int = 10) -> list[tuple[MemoryNode, float]]:
    embedding = embed(query)
    nodes = get_graph().get_all_nodes()
    scored = [(node, cosine_similarity(embedding, node.embedding)) for node in nodes]
    scored.sort(key=lambda x: -x[1])
    return scored[:k]
