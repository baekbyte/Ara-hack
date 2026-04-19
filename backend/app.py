"""
Ara agent with memory palace tools.
Swap `import ara` for the actual Ara SDK import once available at the hackathon.
"""
import httpx

# import ara  # ← replace with actual Ara SDK

API = "http://localhost:8000"
_client = httpx.Client(base_url=API, timeout=10)


def _log_ara_event(event_type: str, input_data: str, output_data: str, tool: str = ""):
    _client.post("/webhook/ara", json={
        "event_type": event_type,
        "input": input_data,
        "output": str(output_data),
        "metadata": {"tool": tool},
    })


# @ara.tool
def query_memory_palace(question: str) -> dict:
    """Semantic search over the memory palace. Call this before answering anything."""
    resp = _client.get("/query", params={"q": question, "k": 10})
    return resp.json()


# @ara.tool
def web_search(query: str) -> dict:
    """Search the web and automatically log the action to the memory palace."""
    # TODO: replace stub with real search (e.g. Tavily, SerpAPI, Brave)
    result = {"query": query, "results": [], "note": "plug in real search here"}
    _log_ara_event("tool_call", query, str(result), tool="web_search")
    return result


# @ara.tool
def recall_context(topic: str) -> dict:
    """Retrieve the most relevant past memories (Omi + Ara) for a topic."""
    resp = _client.get("/query", params={"q": topic, "k": 5})
    data = resp.json()
    _log_ara_event("observation", topic, f"Retrieved {len(data['results'])} memories", tool="recall_context")
    return data


# ara.Automation(
#     "memory-palace-agent",
#     system_instructions=(
#         "Before answering anything, call query_memory_palace "
#         "to check what you already know. Every action you take "
#         "is logged to your memory palace automatically."
#     ),
#     tools=[query_memory_palace, web_search, recall_context],
# )
