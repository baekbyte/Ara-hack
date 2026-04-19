"""Posts a heartbeat node to the memory palace every 60 seconds."""
from dotenv import load_dotenv
load_dotenv()

import time
import httpx
import os
from datetime import datetime

MEMORY_PALACE_URL = os.getenv("MEMORY_PALACE_URL", "http://localhost:8000")

print(f"Heartbeat started → {MEMORY_PALACE_URL}")

while True:
    try:
        r = httpx.get(f"{MEMORY_PALACE_URL}/graph", timeout=5)
        d = r.json()
        node_count = len(d.get("nodes", []))
        summary = f"Memory palace has {node_count} nodes at {datetime.now().strftime('%H:%M')}"

        httpx.post(f"{MEMORY_PALACE_URL}/webhook/ara", json={
            "event_type": "observation",
            "input": summary,
            "output": "heartbeat"
        }, timeout=5)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Logged: {summary}")
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Error: {e}")

    time.sleep(60)
