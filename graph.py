import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import networkx as nx


@dataclass
class MemoryNode:
    id: str
    content: str
    embedding: list[float]
    node_type: str
    timestamp: datetime
    source: str
    metadata: dict


@dataclass
class MemoryEdge:
    source_id: str
    target_id: str
    edge_type: str
    weight: float


class MemoryGraph:
    def __init__(self, db_path: str = "memory_palace.db"):
        self.db_path = db_path
        self.graph = nx.DiGraph()
        self._init_db()
        self._load_from_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    node_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS edges (
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    edge_type TEXT NOT NULL,
                    weight REAL NOT NULL,
                    PRIMARY KEY (source_id, target_id, edge_type)
                )
            """)
            conn.commit()

    def _load_from_db(self):
        with self._connect() as conn:
            for row in conn.execute("SELECT * FROM nodes"):
                node = MemoryNode(
                    id=row[0],
                    content=row[1],
                    embedding=json.loads(row[2]),
                    node_type=row[3],
                    timestamp=datetime.fromisoformat(row[4]),
                    source=row[5],
                    metadata=json.loads(row[6]),
                )
                self.graph.add_node(node.id, data=node)

            for row in conn.execute("SELECT * FROM edges"):
                edge = MemoryEdge(
                    source_id=row[0],
                    target_id=row[1],
                    edge_type=row[2],
                    weight=row[3],
                )
                self.graph.add_edge(
                    edge.source_id,
                    edge.target_id,
                    edge_type=edge.edge_type,
                    weight=edge.weight,
                )

    def add_node(self, node: MemoryNode):
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    node.id,
                    node.content,
                    json.dumps(node.embedding),
                    node.node_type,
                    node.timestamp.isoformat(),
                    node.source,
                    json.dumps(node.metadata),
                ),
            )
            conn.commit()
        self.graph.add_node(node.id, data=node)

    def add_edge(self, edge: MemoryEdge):
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO edges VALUES (?, ?, ?, ?)",
                (edge.source_id, edge.target_id, edge.edge_type, edge.weight),
            )
            conn.commit()
        self.graph.add_edge(
            edge.source_id,
            edge.target_id,
            edge_type=edge.edge_type,
            weight=edge.weight,
        )

    def get_node(self, id: str) -> Optional[MemoryNode]:
        node_data = self.graph.nodes.get(id)
        if node_data is None:
            return None
        return node_data["data"]

    def get_all_nodes(self) -> list[MemoryNode]:
        return [data["data"] for _, data in self.graph.nodes(data=True)]

    def get_all_edges(self) -> list[MemoryEdge]:
        return [
            MemoryEdge(
                source_id=u,
                target_id=v,
                edge_type=data["edge_type"],
                weight=data["weight"],
            )
            for u, v, data in self.graph.edges(data=True)
        ]

    def compute_pagerank(self) -> dict[str, float]:
        if len(self.graph.nodes) == 0:
            return {}
        return nx.pagerank(self.graph, weight="weight")


memory_graph = MemoryGraph()
