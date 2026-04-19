from dotenv import load_dotenv
load_dotenv()

import json
import ara_sdk as ara
import httpx

MEMORY_PALACE_URL = ara.env("MEMORY_PALACE_URL", default="https://avoiding-learning-fill-numerous.trycloudflare.com")


@ara.tool
def query_memory_palace(question: str) -> dict:
    response = httpx.get(f"{MEMORY_PALACE_URL}/query", params={"q": question})
    response.raise_for_status()
    return response.json()


@ara.tool
def recall_context(topic: str) -> dict:
    response = httpx.get(f"{MEMORY_PALACE_URL}/query", params={"q": topic, "k": 10})
    response.raise_for_status()
    data = response.json()
    all_results = data.get("results", [])
    omi_memories = [r for r in all_results if r["node"].get("source") == "omi"]
    ara_actions = [r for r in all_results if r["node"].get("source") == "ara"]
    return {"omi_memories": omi_memories, "ara_actions": ara_actions, "all_results": all_results}


@ara.tool
def log_to_palace(event_type: str, summary: str) -> dict:
    response = httpx.post(
        f"{MEMORY_PALACE_URL}/webhook/ara",
        json={"event_type": event_type, "input": summary, "output": "logged"},
    )
    response.raise_for_status()
    return {"status": "logged", "node_id": response.json().get("node_id")}


ara.Automation(
    "memory-palace-agent",
    system_instructions=(
        "You are a background memory agent. Your job is to keep the memory palace up to date. "
        "When triggered on a schedule: call recall_context with 'recent activity' to review what's been logged, "
        "then call log_to_palace with event_type='observation' and a one-sentence summary of the current state of memory. "
        "When given a specific question or task: call query_memory_palace first, then answer using what you find, "
        "then call log_to_palace to record what you did. "
        "Keep all log summaries short and factual."
    ),
    entrypoint=(
        "You have been triggered on a schedule. "
        "Call recall_context with topic='recent activity' to see what is in the memory palace. "
        "Then call log_to_palace with event_type='observation' and a brief summary of what you found."
    ),
    tools=[query_memory_palace, recall_context, log_to_palace],
)
