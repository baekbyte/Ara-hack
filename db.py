"""SQLite helpers for the Memory Palace graph."""

from __future__ import annotations

import json
import sqlite3
import tempfile
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import get_settings
from models import MemoryEdge, MemoryNode, SessionChunk


def _ensure_utc(timestamp: datetime) -> datetime:
    return timestamp.astimezone(timezone.utc) if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)


class SQLiteStore:
    """Small SQLite wrapper with JSON serialization helpers."""

    def __init__(self, db_path: str | None = None) -> None:
        configured_path = db_path or get_settings().db_path
        self.db_path = configured_path
        try:
            self._init_db()
        except sqlite3.OperationalError:
            fallback_name = configured_path.rsplit("\\", 1)[-1].rsplit("/", 1)[-1] or "memory_palace.db"
            self.db_path = str(Path(tempfile.gettempdir()) / fallback_name)
            self._init_db()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _init_db(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    node_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    content TEXT NOT NULL,
                    embedding_json TEXT,
                    timestamp TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS edges (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    edge_type TEXT NOT NULL,
                    weight REAL NOT NULL,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS session_chunks (
                    session_id TEXT NOT NULL,
                    chunk_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    PRIMARY KEY (session_id, chunk_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ara_events (
                    id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                )
                """
            )

    def upsert_node(self, node: MemoryNode) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO nodes
                (id, node_type, source, content, embedding_json, timestamp, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    node.id,
                    node.node_type,
                    node.source,
                    node.content,
                    json.dumps(node.embedding) if node.embedding is not None else None,
                    _ensure_utc(node.timestamp).isoformat(),
                    json.dumps(node.metadata),
                ),
            )

    def upsert_edge(self, edge: MemoryEdge) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO edges
                (id, source_id, target_id, edge_type, weight, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    edge.id,
                    edge.source_id,
                    edge.target_id,
                    edge.edge_type,
                    edge.weight,
                    json.dumps(edge.metadata),
                ),
            )

    def upsert_session_chunk(self, chunk: SessionChunk) -> bool:
        with self.connect() as conn:
            existing = conn.execute(
                "SELECT 1 FROM session_chunks WHERE session_id = ? AND chunk_id = ?",
                (chunk.session_id, chunk.chunk_id),
            ).fetchone()
            if existing:
                return False
            conn.execute(
                """
                INSERT INTO session_chunks (session_id, chunk_id, content, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (
                    chunk.session_id,
                    chunk.chunk_id,
                    chunk.content,
                    _ensure_utc(chunk.timestamp).isoformat(),
                ),
            )
            return True

    def insert_ara_event(self, *, event_type: str, content: str, metadata: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO ara_events (id, event_type, content, timestamp, metadata_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    f"ara_event_{uuid.uuid4().hex}",
                    event_type,
                    content,
                    datetime.now(timezone.utc).isoformat(),
                    json.dumps(metadata),
                ),
            )

    def fetch_nodes(self) -> list[MemoryNode]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM nodes ORDER BY timestamp ASC").fetchall()
        return [self._row_to_node(row) for row in rows]

    def fetch_edges(self) -> list[MemoryEdge]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM edges").fetchall()
        return [self._row_to_edge(row) for row in rows]

    def fetch_session_chunks(self, *, session_id: str | None = None, limit: int = 100) -> list[SessionChunk]:
        query = "SELECT * FROM session_chunks"
        params: tuple[Any, ...] = ()
        if session_id:
            query += " WHERE session_id = ?"
            params = (session_id,)
        query += " ORDER BY timestamp ASC LIMIT ?"
        params = (*params, limit)
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            SessionChunk(
                session_id=row["session_id"],
                chunk_id=row["chunk_id"],
                content=row["content"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
            )
            for row in rows
        ]

    def _row_to_node(self, row: sqlite3.Row) -> MemoryNode:
        embedding_json = row["embedding_json"]
        return MemoryNode(
            id=row["id"],
            node_type=row["node_type"],
            source=row["source"],
            content=row["content"],
            embedding=json.loads(embedding_json) if embedding_json else None,
            timestamp=datetime.fromisoformat(row["timestamp"]),
            metadata=json.loads(row["metadata_json"]),
        )

    def _row_to_edge(self, row: sqlite3.Row) -> MemoryEdge:
        return MemoryEdge(
            id=row["id"],
            source_id=row["source_id"],
            target_id=row["target_id"],
            edge_type=row["edge_type"],
            weight=row["weight"],
            metadata=json.loads(row["metadata_json"]),
        )


sqlite_store = SQLiteStore()
