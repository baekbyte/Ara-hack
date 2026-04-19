"""Retrieval and ranking logic for compact Ara context packs."""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from config import get_settings
from graph import memory_graph
from ingest import cosine_similarity, embed
from models import GraphEdgeResponse, GraphNodeResponse, MemoryEdge, MemoryNode, model_dump_compat


settings = get_settings()
_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_']+")
_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "of",
    "in",
    "on",
    "for",
    "with",
    "what",
    "was",
    "just",
    "working",
    "about",
    "into",
    "from",
    "your",
    "their",
}


def serialize_node(node: MemoryNode, *, pagerank: float = 0.0) -> GraphNodeResponse:
    """Convert a MemoryNode into the API/frontend response shape."""
    return GraphNodeResponse(
        id=node.id,
        content=node.content,
        node_type=node.node_type,
        source=node.source,
        timestamp=node.timestamp,
        metadata=node.metadata,
        pagerank=pagerank,
    )


def serialize_edge(edge: MemoryEdge) -> GraphEdgeResponse:
    """Convert a MemoryEdge into the API/frontend response shape."""
    return GraphEdgeResponse(
        id=edge.id,
        source=edge.source_id,
        target=edge.target_id,
        edge_type=edge.edge_type,
        weight=edge.weight,
        metadata=edge.metadata,
    )


def _tokenize(text: str) -> set[str]:
    return {
        token.lower()
        for token in _TOKEN_PATTERN.findall(text or "")
        if len(token) > 2 and token.lower() not in _STOPWORDS
    }


def _entity_overlap(query: str, node: MemoryNode) -> float:
    query_tokens = _tokenize(query)
    node_tokens = _tokenize(node.content)
    node_tokens.update(token.lower() for token in node.metadata.get("people", []))
    node_tokens.update(_tokenize(" ".join(node.metadata.get("action_items", []))))
    if not query_tokens or not node_tokens:
        return 0.0
    overlap = len(query_tokens & node_tokens)
    return overlap / max(len(query_tokens), 1)


def _recency_score(timestamp: datetime) -> float:
    now = datetime.now(timezone.utc)
    ts = timestamp.astimezone(timezone.utc) if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
    hours_old = max((now - ts).total_seconds() / 3600.0, 0.0)
    return math.exp(-hours_old / 24.0)


def _source_priority(node: MemoryNode) -> float:
    priorities = {
        "omi_memory": 1.0,
        "omi_conversation": 0.9,
        "omi_desktop_context": 0.9,
        "omi_transcript_chunk": 0.75,
        "task_candidate": 0.8,
        "ara_tool_call": 0.65,
        "ara_message": 0.7,
        "ara_observation": 0.6,
        "derived_fact": 0.55,
    }
    return priorities.get(node.node_type, 0.5)


def _rank_nodes(query: str, nodes: Iterable[MemoryNode], *, limit: int) -> list[dict[str, Any]]:
    query_embedding = embed(query)
    pagerank = memory_graph.compute_pagerank()
    ranked: list[dict[str, Any]] = []

    for node in nodes:
        semantic_similarity = cosine_similarity(query_embedding, node.embedding)
        recency = _recency_score(node.timestamp)
        overlap = _entity_overlap(query, node)
        centrality = pagerank.get(node.id, 0.0)
        source_priority = _source_priority(node)
        score = (
            0.50 * semantic_similarity
            + 0.20 * recency
            + 0.15 * overlap
            + 0.10 * centrality
            + 0.05 * source_priority
        )
        ranked.append(
            {
                "node": model_dump_compat(serialize_node(node, pagerank=centrality)),
                "score": round(score, 4),
                "semantic_similarity": round(semantic_similarity, 4),
                "recency_score": round(recency, 4),
                "entity_overlap": round(overlap, 4),
                "pagerank_score": round(centrality, 4),
            }
        )

    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:limit]


def _top_entities(nodes: Iterable[MemoryNode], *, limit: int = 8) -> list[str]:
    counter: Counter[str] = Counter()
    for node in nodes:
        counter.update(token for token in node.metadata.get("people", []) if token)
        counter.update(_tokenize(node.content))
    return [entity for entity, _ in counter.most_common(limit)]


def _summarize_context(query: str, ranked_results: list[dict[str, Any]]) -> str:
    if not ranked_results:
        return f"No strong personal context was found for '{query}'."

    snippets: list[str] = []
    for item in ranked_results[:3]:
        content = item["node"]["content"].strip()
        if not content:
            continue
        snippets.append(content[:120])
    if not snippets:
        return f"Context was found for '{query}', but it is sparse."
    return "Recent context suggests: " + " | ".join(snippets)


def build_context_pack(query: str, *, limit: int | None = None) -> dict[str, Any]:
    """Build a compact context pack suitable for an LLM tool result."""
    cap = limit or settings.semantic_top_k
    all_nodes = memory_graph.get_all_nodes()
    ranked = _rank_nodes(query, all_nodes, limit=max(cap, settings.recent_context_limit))

    ranked_nodes = [item["node"] for item in ranked]
    selected_ids = {item["node"]["id"] for item in ranked}

    recent_memories = [
        item["node"]
        for item in ranked
        if item["node"]["node_type"] == "omi_memory"
    ][:cap]
    recent_transcript_chunks = [
        item["node"]
        for item in ranked
        if item["node"]["node_type"] == "omi_transcript_chunk"
    ][:cap]
    related_ara_actions = [
        item["node"]
        for item in ranked
        if item["node"]["source"] == "ara"
    ][:cap]
    derived_tasks = [
        item["node"]
        for item in ranked
        if item["node"]["node_type"] == "task_candidate"
    ][:cap]
    recent_desktop_context = [
        item["node"]
        for item in ranked
        if item["node"]["node_type"] in {"omi_desktop_context", "omi_conversation"}
    ][:cap]

    related_nodes = [memory_graph.get_node(node_id) for node_id in selected_ids]
    entities = _top_entities([node for node in related_nodes if node is not None])

    return {
        "ok": True,
        "query": query,
        "summary": _summarize_context(query, ranked),
        "recent_memories": recent_memories,
        "similar_memories": recent_memories,
        "recent_desktop_context": recent_desktop_context,
        "recent_transcript_chunks": recent_transcript_chunks,
        "related_ara_actions": related_ara_actions,
        "derived_tasks": derived_tasks,
        "task_candidates": derived_tasks,
        "top_entities": entities,
        "results": ranked[:cap],
        "nodes": ranked_nodes[:cap],
    }


def build_recent_context_pack(*, hours: int, limit: int) -> dict[str, Any]:
    """Build a recency-heavy context pack for 'what's happening now' flows."""
    recent_nodes = memory_graph.get_recent_nodes(limit=limit * 3, hours=hours)
    ranked = _rank_nodes("recent context", recent_nodes, limit=limit)
    selected = [item["node"] for item in ranked]
    return {
        "ok": True,
        "summary": _summarize_context("recent context", ranked),
        "recent_memories": [node for node in selected if node["node_type"] == "omi_memory"][:limit],
        "recent_transcript_chunks": [node for node in selected if node["node_type"] == "omi_transcript_chunk"][:limit],
        "related_ara_actions": [node for node in selected if node["source"] == "ara"][:limit],
        "task_candidates": [node for node in selected if node["node_type"] == "task_candidate"][:limit],
        "nodes": selected,
    }
