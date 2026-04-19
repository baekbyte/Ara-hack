"""Shared dataclasses and API schemas for the Memory Palace."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


@dataclass(slots=True)
class MemoryNode:
    id: str
    content: str
    embedding: list[float] | None
    node_type: str
    timestamp: datetime
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MemoryEdge:
    id: str
    source_id: str
    target_id: str
    edge_type: str
    weight: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SessionChunk:
    session_id: str
    chunk_id: str
    content: str
    timestamp: datetime


class OmiMemoryEvent(BaseModel):
    omi_id: str | None = None
    timestamp: datetime
    summary: str
    transcript_text: str | None = None
    action_items: list[str] = Field(default_factory=list)
    people: list[str] = Field(default_factory=list)
    client: str = "unknown"
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class OmiTranscriptChunk(BaseModel):
    session_id: str
    chunk_id: str
    timestamp: datetime
    text: str
    speaker: str | None = None
    is_user: bool | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class OmiConversationRecord(BaseModel):
    conversation_id: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    overview: str | None = None
    transcript_segments: list[dict[str, Any]] = Field(default_factory=list)
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class AraActionRequest(BaseModel):
    action_type: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RankedNodeResponse(BaseModel):
    node: dict[str, Any]
    score: float


class GraphNodeResponse(BaseModel):
    id: str
    content: str
    node_type: str
    source: str
    timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    pagerank: float = 0.0


class GraphEdgeResponse(BaseModel):
    id: str
    source: str
    target: str
    edge_type: str
    weight: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphResponse(BaseModel):
    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]


class IngestResponse(BaseModel):
    ok: bool
    node_id: str | None = None
    reason: str | None = None


class HealthResponse(BaseModel):
    ok: bool
    db_path: str
    node_count: int
    edge_count: int
    node_types: list[str]
    sources: list[str]


def model_dump_compat(model: BaseModel) -> dict[str, Any]:
    """Return a plain dict for either Pydantic v1 or v2."""
    if hasattr(model, "model_dump"):
        return model.model_dump()  # type: ignore[no-any-return]
    return model.dict()  # type: ignore[no-any-return]
