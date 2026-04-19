"""Ingestion pipelines for Omi and Ara events."""

from __future__ import annotations

import hashlib
import math
import re
import uuid
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from adapters.omi import OmiAdapter
from config import get_settings
from graph import memory_graph
from models import MemoryEdge, MemoryNode, OmiMemoryEvent, OmiTranscriptChunk, SessionChunk

try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover - optional dependency
    SentenceTransformer = None  # type: ignore[assignment]


settings = get_settings()
omi_adapter = OmiAdapter()
_embedding_model: SentenceTransformer | None = None
_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_']+")


def _get_model() -> SentenceTransformer | None:
    """Load the sentence-transformer lazily when available."""
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model
    if SentenceTransformer is None:
        return None
    try:
        _embedding_model = SentenceTransformer(settings.embedding_model_name)
    except Exception:
        _embedding_model = None
    return _embedding_model


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_PATTERN.findall(text)]


def _hashed_embedding(text: str, *, dim: int) -> list[float]:
    """Deterministic fallback embedding when ML dependencies are unavailable."""
    vector = [0.0] * dim
    for token in _tokenize(text):
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        index = int(digest[:8], 16) % dim
        sign = -1.0 if int(digest[8:10], 16) % 2 else 1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def embed(text: str) -> list[float] | None:
    """Create an embedding with a transformer when available, else a hashed fallback."""
    cleaned = (text or "").strip()
    if not cleaned:
        return None

    model = _get_model()
    if model is not None:
        try:
            return model.encode(cleaned).tolist()
        except Exception:
            pass
    return _hashed_embedding(cleaned, dim=settings.fallback_embedding_dim)


def cosine_similarity(left: list[float] | None, right: list[float] | None) -> float:
    """Compute cosine similarity for two vectors."""
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def find_neighbors(
    embedding: list[float] | None,
    *,
    k: int | None = None,
    threshold: float | None = None,
    node_types: Iterable[str] | None = None,
    exclude_ids: Iterable[str] | None = None,
) -> list[tuple[MemoryNode, float]]:
    """Return top semantic neighbors from the current graph."""
    if embedding is None:
        return []

    limit = k or settings.semantic_top_k
    minimum = threshold if threshold is not None else settings.semantic_threshold
    allowed_types = set(node_types or [])
    excluded = set(exclude_ids or [])
    candidates: list[tuple[MemoryNode, float]] = []

    for node in memory_graph.get_all_nodes():
        if node.id in excluded:
            continue
        if allowed_types and node.node_type not in allowed_types:
            continue
        score = cosine_similarity(embedding, node.embedding)
        if score >= minimum:
            candidates.append((node, score))

    candidates.sort(key=lambda item: item[1], reverse=True)
    return candidates[:limit]


def _iso_to_datetime(raw_timestamp: datetime | str | None) -> datetime:
    if isinstance(raw_timestamp, datetime):
        return raw_timestamp.astimezone(timezone.utc) if raw_timestamp.tzinfo else raw_timestamp.replace(tzinfo=timezone.utc)
    if isinstance(raw_timestamp, str) and raw_timestamp.strip():
        try:
            parsed = datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))
            return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _edge_id(prefix: str, source_id: str, target_id: str, edge_type: str) -> str:
    digest = hashlib.sha1(f"{prefix}:{source_id}:{target_id}:{edge_type}".encode("utf-8")).hexdigest()
    return f"{prefix}_{digest[:16]}"


def _node_id(prefix: str, external_id: str | None = None) -> str:
    return f"{prefix}_{external_id}" if external_id else f"{prefix}_{uuid.uuid4().hex}"


def _link_semantic_neighbors(node: MemoryNode, neighbors: list[tuple[MemoryNode, float]]) -> None:
    for neighbor, score in neighbors:
        if neighbor.id == node.id:
            continue
        memory_graph.add_edge(
            MemoryEdge(
                id=_edge_id("semantic", node.id, neighbor.id, "semantic"),
                source_id=node.id,
                target_id=neighbor.id,
                edge_type="semantic",
                weight=round(score, 4),
                metadata={"similarity": round(score, 4)},
            )
        )


def _link_temporal_neighbor(node: MemoryNode) -> None:
    previous = memory_graph.get_previous_node(before=node.timestamp, exclude_id=node.id)
    if previous is None:
        return
    memory_graph.add_edge(
        MemoryEdge(
            id=_edge_id("temporal", previous.id, node.id, "temporal"),
            source_id=previous.id,
            target_id=node.id,
            edge_type="temporal",
            weight=1.0,
            metadata={},
        )
    )


def _create_derived_node(
    *,
    prefix: str,
    content: str,
    node_type: str,
    source_node: MemoryNode,
    extra_metadata: dict[str, Any],
    edge_type: str,
) -> MemoryNode:
    node = MemoryNode(
        id=_node_id(prefix),
        content=content,
        embedding=embed(content),
        node_type=node_type,
        timestamp=source_node.timestamp,
        source="derived",
        metadata={"derived_from": source_node.id, **extra_metadata},
    )
    memory_graph.add_node(node)
    memory_graph.add_edge(
        MemoryEdge(
            id=_edge_id(edge_type, source_node.id, node.id, edge_type),
            source_id=source_node.id,
            target_id=node.id,
            edge_type=edge_type,
            weight=1.0,
            metadata={"derived_from": source_node.id},
        )
    )
    memory_graph.add_edge(
        MemoryEdge(
            id=_edge_id("derived_from", node.id, source_node.id, "derived_from"),
            source_id=node.id,
            target_id=source_node.id,
            edge_type="derived_from",
            weight=1.0,
            metadata={"derived_from": source_node.id},
        )
    )
    return node


def _ingest_normalized_omi_event(
    event: OmiMemoryEvent,
    *,
    node_type: str,
    id_prefix: str,
    event_kind: str,
) -> MemoryNode:
    content = event.summary or event.transcript_text or f"Untitled {event_kind}"
    node = MemoryNode(
        id=_node_id(id_prefix, event.omi_id),
        content=content,
        embedding=embed(content),
        node_type=node_type,
        timestamp=_iso_to_datetime(event.timestamp),
        source="omi",
        metadata={
            "omi_id": event.omi_id,
            "client": event.client,
            "people": event.people,
            "action_items": event.action_items,
            "summary": event.summary,
            "transcript_text": event.transcript_text,
            "event_kind": event_kind,
            "raw_payload": event.raw_payload,
        },
    )
    memory_graph.add_node(node)

    neighbors = find_neighbors(node.embedding, exclude_ids={node.id})
    _link_semantic_neighbors(node, neighbors)
    _link_temporal_neighbor(node)

    for person in event.people:
        _create_derived_node(
            prefix="person",
            content=person,
            node_type="derived_fact",
            source_node=node,
            extra_metadata={"kind": "person"},
            edge_type="mentions_person",
        )

    for action_item in event.action_items:
        _create_derived_node(
            prefix="task",
            content=action_item,
            node_type="task_candidate",
            source_node=node,
            extra_metadata={"kind": "action_item"},
            edge_type="contains_task",
        )

    return node


def ingest_omi_memory(payload: dict[str, Any]) -> MemoryNode:
    """Normalize and ingest an Omi memory payload."""
    event = omi_adapter.handle_memory_webhook(payload)
    return _ingest_normalized_omi_event(
        event,
        node_type="omi_memory",
        id_prefix="omi",
        event_kind="memory",
    )


def ingest_omi_conversation(payload: dict[str, Any]) -> MemoryNode:
    """Normalize and ingest a completed Omi conversation event."""
    event = omi_adapter.handle_memory_webhook(payload)
    return _ingest_normalized_omi_event(
        event,
        node_type="omi_conversation",
        id_prefix="conv",
        event_kind="conversation",
    )


def ingest_omi_day_summary(payload: dict[str, Any]) -> MemoryNode:
    """Normalize and ingest an Omi day-summary event."""
    event = omi_adapter.handle_day_summary_webhook(payload)
    return _ingest_normalized_omi_event(
        event,
        node_type="omi_desktop_context",
        id_prefix="day",
        event_kind="day_summary",
    )


def ingest_omi_transcript(payload: dict[str, Any]) -> MemoryNode:
    """Ingest a real-time Omi transcript chunk."""
    chunk: OmiTranscriptChunk = omi_adapter.handle_transcript_webhook(payload)
    chunk_timestamp = _iso_to_datetime(chunk.timestamp)
    stored = memory_graph.upsert_session_chunk(
        SessionChunk(
            session_id=chunk.session_id,
            chunk_id=chunk.chunk_id,
            content=chunk.text,
            timestamp=chunk_timestamp,
        )
    )
    node = MemoryNode(
        id=_node_id("transcript", f"{chunk.session_id}_{chunk.chunk_id}"),
        content=chunk.text,
        embedding=embed(chunk.text),
        node_type="omi_transcript_chunk",
        timestamp=chunk_timestamp,
        source="omi",
        metadata={
            "session_id": chunk.session_id,
            "chunk_id": chunk.chunk_id,
            "speaker": chunk.speaker,
            "is_user": chunk.is_user,
            "raw_payload": chunk.raw_payload,
            "deduped": not stored,
        },
    )

    if stored:
        memory_graph.add_node(node)
        _link_temporal_neighbor(node)
        session_chunks = memory_graph.get_session_chunks(chunk.session_id, limit=2)
        if len(session_chunks) >= 2:
            previous_chunk = session_chunks[-2]
            previous_node = memory_graph.get_node(_node_id("transcript", f"{previous_chunk.session_id}_{previous_chunk.chunk_id}"))
            if previous_node is not None:
                memory_graph.add_edge(
                    MemoryEdge(
                        id=_edge_id("same_session", previous_node.id, node.id, "same_session"),
                        source_id=previous_node.id,
                        target_id=node.id,
                        edge_type="same_session",
                        weight=1.0,
                        metadata={"session_id": chunk.session_id},
                    )
                )
    return node


def _infer_ara_node_type(action_type: str) -> str:
    lowered = action_type.lower()
    if "message" in lowered or "answer" in lowered:
        return "ara_message"
    if "observe" in lowered:
        return "ara_observation"
    return "ara_tool_call"


def ingest_ara_event(event: dict[str, Any]) -> MemoryNode:
    """Create an Ara event node and connect it to related memory."""
    action_type = str(event.get("action_type") or event.get("event_type") or "ara_event")
    content = str(event.get("content") or "").strip()
    metadata = dict(event.get("metadata") or {})
    summary = content or metadata.get("output_summary") or action_type
    if metadata.get("tool_name") and not content:
        summary = f"{metadata['tool_name']}: {metadata.get('output_summary', '')}".strip(": ")

    node = MemoryNode(
        id=_node_id("ara", str(event.get("id") or None)),
        content=summary,
        embedding=embed(summary),
        node_type=_infer_ara_node_type(action_type),
        timestamp=_iso_to_datetime(event.get("timestamp")),
        source="ara",
        metadata={
            "action_type": action_type,
            "metadata": metadata,
        },
    )
    memory_graph.add_node(node)
    memory_graph.add_ara_event(action_type, summary, metadata)

    neighbors = find_neighbors(node.embedding, exclude_ids={node.id})
    _link_semantic_neighbors(node, neighbors)
    _link_temporal_neighbor(node)

    for neighbor, score in neighbors[:3]:
        if neighbor.source == "omi":
            memory_graph.add_edge(
                MemoryEdge(
                    id=_edge_id("related_action", node.id, neighbor.id, "related_action"),
                    source_id=node.id,
                    target_id=neighbor.id,
                    edge_type="related_action",
                    weight=round(score, 4),
                    metadata={"similarity": round(score, 4)},
                )
            )
    return node
