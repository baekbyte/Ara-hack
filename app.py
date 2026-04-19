import ara_sdk as ara
import httpx

MEMORY_PALACE_URL = ara.env("MEMORY_PALACE_URL", default="http://localhost:8000")


@ara.tool
def query_memory_palace(question: str) -> dict:
    response = httpx.get(f"{MEMORY_PALACE_URL}/query", params={"q": question})
    response.raise_for_status()
    return response.json()


@ara.tool
def web_search(query: str) -> dict:
    key = ara.secret("TAVILY_API_KEY")
    response = httpx.post(
        "https://api.tavily.com/search",
        json={"api_key": key, "query": query, "max_results": 5},
    )
    response.raise_for_status()
    results = response.json()
    httpx.post(
        f"{MEMORY_PALACE_URL}/webhook/ara",
        json={"event_type": "web_search", "input": query, "output": str(results)},
    )
    return results


@ara.tool
def recall_context(topic: str) -> dict:
    response = httpx.get(f"{MEMORY_PALACE_URL}/query", params={"q": topic, "k": 10})
    response.raise_for_status()
    data = response.json()
    all_results = data.get("results", [])
    omi_memories = [r for r in all_results if r.get("source") == "omi"]
    ara_actions = [r for r in all_results if r.get("source") == "ara"]
    return {"omi_memories": omi_memories, "ara_actions": ara_actions, "all_results": all_results}


ara.Automation(
    "memory-palace-agent",
    system_instructions=(
        "You are a personal AI assistant with a memory palace. "
        "Before answering ANYTHING, call query_memory_palace to check what you already know. "
        "Every web search you do is automatically logged to your memory palace. "
        "Use recall_context to retrieve relevant memories before acting. "
        "Your memory palace contains both your user's real-life conversations (from Omi) "
        "and your own past actions — use both to give personalized, context-aware answers."
    ),
    tools=[query_memory_palace, web_search, recall_context],
)
