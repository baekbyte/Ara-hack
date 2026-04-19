"""Snapshot export helpers for the Memory Palace graph."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from graph import memory_graph
from models import model_dump_compat
from retrieval import build_recent_context_pack, serialize_edge, serialize_node


EXPORT_DIR = Path("exports")
JSON_EXPORT_PATH = EXPORT_DIR / "memory_palace_snapshot.json"
MARKDOWN_EXPORT_PATH = EXPORT_DIR / "memory_palace_snapshot.md"


def build_memory_snapshot_json() -> dict[str, Any]:
    """Build a compact but useful graph snapshot for file-based sync."""
    pagerank = memory_graph.compute_pagerank()
    nodes = [
        model_dump_compat(serialize_node(node, pagerank=pagerank.get(node.id, 0.0)))
        for node in memory_graph.get_all_nodes()
    ]
    edges = [
        model_dump_compat(serialize_edge(edge))
        for edge in memory_graph.get_all_edges()
    ]
    recent = build_recent_context_pack(hours=24, limit=10)
    return {
        "summary": recent["summary"],
        "recent_memories": recent["recent_memories"],
        "recent_transcript_chunks": recent["recent_transcript_chunks"],
        "related_ara_actions": recent["related_ara_actions"],
        "task_candidates": recent["task_candidates"],
        "nodes": nodes,
        "edges": edges,
    }


def build_memory_snapshot_markdown() -> str:
    """Render a human-friendly markdown memory snapshot."""
    snapshot = build_memory_snapshot_json()
    lines: list[str] = [
        "# Memory Palace Snapshot",
        "",
        snapshot["summary"],
        "",
        "## Recent Memories",
    ]

    recent_memories = snapshot.get("recent_memories", [])
    if recent_memories:
        for item in recent_memories:
            lines.append(f"- {item['content']}")
    else:
        lines.append("- None yet")

    lines.extend(["", "## Recent Transcript Chunks"])
    recent_transcript = snapshot.get("recent_transcript_chunks", [])
    if recent_transcript:
        for item in recent_transcript:
            lines.append(f"- {item['content']}")
    else:
        lines.append("- None yet")

    lines.extend(["", "## Tasks"])
    tasks = snapshot.get("task_candidates", [])
    if tasks:
        for item in tasks:
            lines.append(f"- {item['content']}")
    else:
        lines.append("- None yet")

    lines.extend(["", "## Recent Ara Actions"])
    actions = snapshot.get("related_ara_actions", [])
    if actions:
        for item in actions:
            lines.append(f"- {item['content']}")
    else:
        lines.append("- None yet")

    lines.extend(
        [
            "",
            "## Graph Stats",
            f"- Nodes: {len(snapshot.get('nodes', []))}",
            f"- Edges: {len(snapshot.get('edges', []))}",
            "",
            "## Notes",
            "- Omi nodes reflect conversation/day-summary context ingested into the Memory Palace.",
            "- Ara action nodes reflect assistant activity written back into the graph.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_snapshot_files() -> dict[str, str]:
    """Write JSON + Markdown snapshots to disk after graph updates."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_json = build_memory_snapshot_json()
    JSON_EXPORT_PATH.write_text(
        json.dumps(snapshot_json, indent=2, default=str),
        encoding="utf-8",
    )
    MARKDOWN_EXPORT_PATH.write_text(build_memory_snapshot_markdown(), encoding="utf-8")
    return {
        "json_path": str(JSON_EXPORT_PATH.resolve()),
        "markdown_path": str(MARKDOWN_EXPORT_PATH.resolve()),
    }
