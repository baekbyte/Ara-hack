"""Graph storage and query primitives for the Memory Palace.

Local run notes:
- Start the API with: `uvicorn server:app --reload`
- The graph persists to the SQLite database configured by `MEMORY_PALACE_DB`
- Use `/graph` to inspect the in-memory + SQLite-backed graph state
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from typing import Any

import networkx as nx

from config import get_settings
from db import SQLiteStore, sqlite_store
from models import MemoryEdge, MemoryNode, SessionChunk


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class MemoryGraph:
    """SQLite-backed directed graph with a NetworkX in-memory index."""

    def __init__(self, store: SQLiteStore | None = None) -> None:
        self.settings = get_settings()
        self.store = store or sqlite_store
        self.graph = nx.DiGraph()
        self._load_from_store()

    def _load_from_store(self) -> None:
        """Hydrate the in-memory graph from SQLite."""
        self.graph.clear()
        for node in self.store.fetch_nodes():
            self.graph.add_node(node.id, data=node)
        for edge in self.store.fetch_edges():
            self.graph.add_edge(
                edge.source_id,
                edge.target_id,
                data=edge,
                edge_type=edge.edge_type,
                weight=edge.weight,
            )

    def add_node(self, node: MemoryNode) -> MemoryNode:
        """Persist and index a node."""
        self.store.upsert_node(node)
        self.graph.add_node(node.id, data=node)
        return node

    def add_edge(self, edge: MemoryEdge) -> MemoryEdge:
        """Persist and index an edge."""
        self.store.upsert_edge(edge)
        self.graph.add_edge(
            edge.source_id,
            edge.target_id,
            data=edge,
            edge_type=edge.edge_type,
            weight=edge.weight,
        )
        return edge

    def upsert_session_chunk(self, chunk: SessionChunk) -> bool:
        """Insert a transcript chunk if it is new."""
        return self.store.upsert_session_chunk(chunk)

    def add_ara_event(self, event_type: str, content: str, metadata: dict[str, Any]) -> None:
        """Persist an Ara event row for audit/debugging."""
        self.store.insert_ara_event(event_type=event_type, content=content, metadata=metadata)

    def get_node(self, node_id: str) -> MemoryNode | None:
        """Fetch a node from the in-memory graph."""
        payload = self.graph.nodes.get(node_id)
        if payload is None:
            return None
        return payload["data"]

    def get_all_nodes(self) -> list[MemoryNode]:
        """Return every indexed node."""
        return [payload["data"] for _, payload in self.graph.nodes(data=True)]

    def get_all_edges(self) -> list[MemoryEdge]:
        """Return every indexed edge."""
        return [payload["data"] for _, _, payload in self.graph.edges(data=True)]

    def get_recent_nodes(
        self,
        *,
        limit: int = 10,
        hours: int = 24,
        node_types: Iterable[str] | None = None,
        source: str | None = None,
    ) -> list[MemoryNode]:
        """Return recent nodes, optionally filtered by type/source."""
        cutoff = utc_now() - timedelta(hours=hours)
        allowed_types = set(node_types or [])
        nodes: list[MemoryNode] = []
        for node in self.get_all_nodes():
            if node.timestamp < cutoff:
                continue
            if allowed_types and node.node_type not in allowed_types:
                continue
            if source and node.source != source:
                continue
            nodes.append(node)
        nodes.sort(key=lambda item: item.timestamp, reverse=True)
        return nodes[:limit]

    def get_previous_node(
        self,
        *,
        before: datetime | None = None,
        source: str | None = None,
        exclude_id: str | None = None,
    ) -> MemoryNode | None:
        """Return the most recent node before the supplied timestamp."""
        boundary = before or utc_now()
        candidates = [
            node
            for node in self.get_all_nodes()
            if node.timestamp <= boundary
            and node.id != exclude_id
            and (source is None or node.source == source)
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda item: item.timestamp, reverse=True)
        return candidates[0]

    def get_session_chunks(self, session_id: str, *, limit: int = 100) -> list[SessionChunk]:
        """Fetch transcript chunks for a session in chronological order."""
        return self.store.fetch_session_chunks(session_id=session_id, limit=limit)

    def compute_pagerank(self) -> dict[str, float]:
        """Compute PageRank for ranking and graph visualization."""
        if not self.graph.nodes:
            return {}
        try:
            return nx.pagerank(self.graph, weight="weight")
        except nx.NetworkXException:
            return {node_id: 0.0 for node_id in self.graph.nodes}

    def stats(self) -> dict[str, Any]:
        """Return light health/debug stats."""
        nodes = self.get_all_nodes()
        edges = self.get_all_edges()
        return {
            "db_path": self.store.db_path,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "node_types": sorted({node.node_type for node in nodes}),
            "sources": sorted({node.source for node in nodes}),
        }


memory_graph = MemoryGraph()
