#!/usr/bin/env python3
"""Memory palace CLI — called by Ara via exec tool."""
from dotenv import load_dotenv
load_dotenv()

import sys
import json
import httpx
import os

MEMORY_PALACE_URL = os.getenv("MEMORY_PALACE_URL", "http://localhost:8000")


def query(q: str):
    r = httpx.get(f"{MEMORY_PALACE_URL}/query", params={"q": q, "k": 8}, timeout=10)
    results = r.json().get("results", [])
    if not results:
        print("No relevant memories found.")
        return
    for item in results:
        node = item["node"]
        src = "🔵 Omi" if node["source"] == "omi" else "🟠 Ara"
        print(f"{src} [{node['node_type']}] {node['content']}")


def log(event_type: str, summary: str):
    r = httpx.post(
        f"{MEMORY_PALACE_URL}/webhook/ara",
        json={"event_type": event_type, "input": summary, "output": "logged"},
        timeout=10,
    )
    print(f"Logged to memory palace: {r.json().get('node_id', '')[:8]}")


def graph():
    r = httpx.get(f"{MEMORY_PALACE_URL}/graph", timeout=10)
    d = r.json()
    print(f"Memory Palace: {len(d['nodes'])} nodes, {len(d['edges'])} edges")
    for node in sorted(d["nodes"], key=lambda n: n.get("pagerank", 0), reverse=True)[:5]:
        src = "🔵" if node["source"] == "omi" else "🟠"
        print(f"  {src} {node['content'][:80]}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: palace.py query <text> | log <type> <summary> | graph")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "query" and len(sys.argv) >= 3:
        query(" ".join(sys.argv[2:]))
    elif cmd == "log" and len(sys.argv) >= 4:
        log(sys.argv[2], " ".join(sys.argv[3:]))
    elif cmd == "graph":
        graph()
    else:
        print("Usage: palace.py query <text> | log <type> <summary> | graph")
