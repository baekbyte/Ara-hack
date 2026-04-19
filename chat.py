"""Local chat CLI that injects memory palace context into every Ara message."""
from dotenv import load_dotenv
load_dotenv()

import httpx
import os
import sys

MEMORY_PALACE_URL = os.getenv("MEMORY_PALACE_URL", "http://localhost:8000")
ARA_API_KEY = os.getenv("ARA_API_KEY", "")
ARA_API_URL = "https://api.ara.so"


def query_palace(question: str) -> list[dict]:
    try:
        r = httpx.get(f"{MEMORY_PALACE_URL}/query", params={"q": question, "k": 5}, timeout=5)
        return r.json().get("results", [])
    except Exception:
        return []


def log_to_palace(event_type: str, summary: str):
    try:
        httpx.post(f"{MEMORY_PALACE_URL}/webhook/ara",
                   json={"event_type": event_type, "input": summary, "output": "logged"},
                   timeout=5)
    except Exception:
        pass


def chat(message: str, conversation_id: str = "") -> str:
    memories = query_palace(message)
    context = ""
    if memories:
        context = "\n\nRelevant memories from your palace:\n" + "\n".join(
            f"- [{r['node']['source'].upper()}] {r['node']['content']}" for r in memories
        )

    augmented = message + context

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {ARA_API_KEY}"}
    body = {"messages": [{"role": "user", "content": augmented}]}
    if conversation_id:
        body["chatId"] = conversation_id

    with httpx.stream("POST", f"{ARA_API_URL}/chat", json=body, headers=headers, timeout=60) as r:
        full_response = ""
        for line in r.iter_lines():
            if line.startswith("data:"):
                data = line[5:].strip()
                if data and data != "[DONE]":
                    try:
                        import json
                        chunk = json.loads(data)
                        text = chunk.get("text") or chunk.get("content") or chunk.get("delta", {}).get("text", "")
                        if text:
                            print(text, end="", flush=True)
                            full_response += text
                    except Exception:
                        pass
        print()
        return full_response


def main():
    print("Memory Palace Chat — type 'quit' to exit")
    print(f"Connected to palace at {MEMORY_PALACE_URL}\n")
    conversation_id = ""

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not user_input or user_input.lower() == "quit":
            break

        print("Ara: ", end="", flush=True)
        response = chat(user_input, conversation_id)
        if response:
            log_to_palace("response", f"Q: {user_input[:100]} | A: {response[:200]}")


if __name__ == "__main__":
    main()
