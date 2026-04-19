from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import sqlite3
import json
import networkx as nx

DB_PATH = "memory_palace.db"


@dataclass
class MemoryNode:
    id: str
    content: str
    embedding: list[float]
    node_type: str  # "omi_memory" | "ara_tool_call" | "ara_message" | "ara_observation"
    timestamp: datetime
    source: str     # "omi" | "ara"
    metadata: dict


@dataclass
class MemoryEdge:
    source_id: str
    target_id: str
    edge_type: str  # "semantic" | "temporal" | "causal"
    weight: float


class MemoryGraph:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.graph = nx.DiGraph()
        self._init_db()
        self._load_from_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
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
        with sqlite3.connect(self.db_path) as conn:
            for row in conn.execute("SELECT * FROM nodes"):
                id_, content, embedding, node_type, timestamp, source, metadata = row
                node = MemoryNode(
                    id=id_,
                    content=content,
                    embedding=json.loads(embedding),
                    node_type=node_type,
                    timestamp=datetime.fromisoformat(timestamp),
                    source=source,
                    metadata=json.loads(metadata),
                )
                self.graph.add_node(id_, data=node)
            for row in conn.execute("SELECT * FROM edges"):
                source_id, target_id, edge_type, weight = row
                self.graph.add_edge(source_id, target_id, edge_type=edge_type, weight=weight)

    def add_node(self, node: MemoryNode):
        self.graph.add_node(node.id, data=node)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?)",
                (node.id, node.content, json.dumps(node.embedding), node.node_type,
                 node.timestamp.isoformat(), node.source, json.dumps(node.metadata))
            )
            conn.commit()

    def add_edge(self, edge: MemoryEdge):
        self.graph.add_edge(edge.source_id, edge.target_id, edge_type=edge.edge_type, weight=edge.weight)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO edges VALUES (?, ?, ?, ?)",
                (edge.source_id, edge.target_id, edge.edge_type, edge.weight)
            )
            conn.commit()

    def get_all_nodes(self) -> list[MemoryNode]:
        return [data["data"] for _, data in self.graph.nodes(data=True)]

    def get_all_edges(self) -> list[MemoryEdge]:
        return [
            MemoryEdge(source_id=u, target_id=v, edge_type=d["edge_type"], weight=d["weight"])
            for u, v, d in self.graph.edges(data=True)
        ]

    def compute_pagerank(self) -> dict[str, float]:
        if not self.graph.nodes:
            return {}
        try:
            return nx.pagerank(self.graph, weight="weight")
        except nx.PowerIterationFailedConvergence:
            n = len(self.graph.nodes)
            return {node: 1.0 / n for node in self.graph.nodes}

    def get_node(self, node_id: str) -> Optional[MemoryNode]:
        if node_id in self.graph.nodes:
            return self.graph.nodes[node_id]["data"]
        return None

    def to_dict(self) -> dict:
        pagerank = self.compute_pagerank()
        nodes = [
            {
                "id": node.id,
                "content": node.content,
                "node_type": node.node_type,
                "timestamp": node.timestamp.isoformat(),
                "source": node.source,
                "metadata": node.metadata,
                "importance": pagerank.get(node.id, 0.0),
            }
            for _, data in self.graph.nodes(data=True)
            for node in [data["data"]]
        ]
        edges = [
            {
                "source": u,
                "target": v,
                "edge_type": d["edge_type"],
                "weight": d["weight"],
            }
            for u, v, d in self.graph.edges(data=True)
        ]
        return {"nodes": nodes, "edges": edges}


_graph: Optional[MemoryGraph] = None


def get_graph() -> MemoryGraph:
    global _graph
    if _graph is None:
        _graph = MemoryGraph()
    return _graph
