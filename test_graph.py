"""Quick smoke test: add dummy nodes/edges, verify graph + ingest pipeline."""
import os
os.environ["MEMORY_PALACE_DB"] = "test_memory_palace.db"

# Use a test DB to avoid polluting the real one
import graph as graph_module
graph_module.memory_graph = graph_module.MemoryGraph("test_memory_palace.db")

import ingest
ingest.memory_graph = graph_module.memory_graph
ingest._previous_node_id = None

def separator(title):
    print(f"\n{'='*50}")
    print(f"  {title}")
    print('='*50)

# ── 1. Ingest Omi memories ──────────────────────────────
separator("Ingesting Omi memories")

omi_payloads = [
    {"text": "Had a great meeting with the team about the new product launch strategy"},
    {"transcript": "Discussed machine learning models for recommendation systems with Alice"},
    {"structured": {"overview": "Planning a trip to Tokyo in the summer"}},
    {"text": "Reviewed the quarterly budget and identified cost-saving opportunities"},
    {"text": "Talked about machine learning and AI trends at the conference"},
]

omi_nodes = []
for payload in omi_payloads:
    node = ingest.ingest_omi_memory(payload)
    omi_nodes.append(node)
    print(f"[omi]  {node.id[:8]}...  \"{node.content[:60]}\"")

# ── 2. Ingest Ara events ────────────────────────────────
separator("Ingesting Ara events")

ara_events = [
    ("web_search", "machine learning trends 2024", "Found 5 results about LLMs and diffusion models"),
    ("web_search", "Tokyo travel tips", "Best time to visit is spring (March-May) for cherry blossoms"),
    ("recall_context", "product launch", "Found 2 related memories about team meeting and strategy"),
]

ara_nodes = []
for event_type, inp, out in ara_events:
    node = ingest.ingest_ara_event(event_type, inp, out)
    ara_nodes.append(node)
    print(f"[ara]  {node.id[:8]}...  \"{node.content[:60]}\"")

# ── 3. Graph stats ──────────────────────────────────────
separator("Graph stats")
all_nodes = graph_module.memory_graph.get_all_nodes()
all_edges = graph_module.memory_graph.get_all_edges()
print(f"Nodes : {len(all_nodes)}")
print(f"Edges : {len(all_edges)}")

edge_types = {}
for e in all_edges:
    edge_types[e.edge_type] = edge_types.get(e.edge_type, 0) + 1
for etype, count in edge_types.items():
    print(f"  {etype:10s}: {count}")

# ── 4. PageRank ─────────────────────────────────────────
separator("PageRank (top 5)")
pr = graph_module.memory_graph.compute_pagerank()
top = sorted(pr.items(), key=lambda x: x[1], reverse=True)[:5]
for node_id, score in top:
    node = graph_module.memory_graph.get_node(node_id)
    print(f"  {score:.4f}  [{node.source:3s}]  \"{node.content[:55]}\"")

# ── 5. Neighbor search ──────────────────────────────────
separator("Neighbor search: 'machine learning AI'")
query_embedding = ingest.embed("machine learning AI")
neighbors = ingest.find_neighbors(query_embedding, k=5)
if neighbors:
    for node, score in neighbors:
        print(f"  {score:.4f}  [{node.source:3s}]  \"{node.content[:55]}\"")
else:
    print("  No neighbors above threshold 0.7")

# ── 6. Cleanup ──────────────────────────────────────────
separator("Cleanup")
import os
os.remove("test_memory_palace.db")
print("Removed test_memory_palace.db")
print("\nAll tests passed!")
