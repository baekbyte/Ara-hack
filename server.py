"""FastAPI bridge for Omi ingestion, graph retrieval, and Ara logging."""

from __future__ import annotations

import json
import logging
from typing import Any

import uvicorn
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from graph import memory_graph
from ingest import ingest_ara_event, ingest_omi_conversation, ingest_omi_day_summary, ingest_omi_memory, ingest_omi_transcript
from models import AraActionRequest, GraphResponse, HealthResponse, IngestResponse, model_dump_compat
from retrieval import build_context_pack, build_recent_context_pack, serialize_edge, serialize_node
from snapshot import JSON_EXPORT_PATH, MARKDOWN_EXPORT_PATH, build_memory_snapshot_json, build_memory_snapshot_markdown, write_snapshot_files


settings = get_settings()
app = FastAPI(title="Memory Palace API", version="0.1.0")
logger = logging.getLogger("memory_palace.webhooks")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _verify_token(x_api_token: str | None) -> None:
    """Best-effort token verification for bridge calls."""
    expected = settings.api_token
    if not expected or expected == "dev-token":
        return
    if x_api_token != expected:
        raise HTTPException(status_code=401, detail="invalid api token")


def _preview_payload(payload: dict[str, Any], *, max_len: int = 240) -> str:
    try:
        preview = json.dumps(payload, default=str)
    except TypeError:
        preview = str(payload)
    preview = preview.replace("\n", " ")
    if len(preview) > max_len:
        return preview[: max_len - 3] + "..."
    return preview


def _log_webhook(name: str, payload: dict[str, Any]) -> None:
    logger.info(
        "webhook_received endpoint=%s keys=%s preview=%s",
        name,
        sorted(payload.keys()),
        _preview_payload(payload),
    )


@app.post("/webhook/omi/memory", response_model=IngestResponse)
async def webhook_omi_memory(
    payload: dict[str, Any],
    x_api_token: str | None = Header(default=None),
) -> IngestResponse:
    _verify_token(x_api_token)
    _log_webhook("omi_memory", payload)
    node = ingest_omi_memory(payload)
    write_snapshot_files()
    return IngestResponse(ok=True, node_id=node.id)


@app.post("/webhook/omi/conversation", response_model=IngestResponse)
async def webhook_omi_conversation(
    payload: dict[str, Any],
    x_api_token: str | None = Header(default=None),
) -> IngestResponse:
    _verify_token(x_api_token)
    _log_webhook("omi_conversation", payload)
    try:
        node = ingest_omi_conversation(payload)
        write_snapshot_files()
        return IngestResponse(ok=True, node_id=node.id)
    except Exception:
        logger.exception("webhook_failed endpoint=omi_conversation preview=%s", _preview_payload(payload))
        raise


@app.get("/webhook/omi/conversation")
async def webhook_omi_conversation_status() -> dict[str, Any]:
    return {"ok": True, "endpoint": "omi_conversation", "method": "POST"}


@app.post("/webhook/omi/day-summary", response_model=IngestResponse)
async def webhook_omi_day_summary(
    payload: dict[str, Any],
    x_api_token: str | None = Header(default=None),
) -> IngestResponse:
    _verify_token(x_api_token)
    _log_webhook("omi_day_summary", payload)
    try:
        node = ingest_omi_day_summary(payload)
        write_snapshot_files()
        return IngestResponse(ok=True, node_id=node.id)
    except Exception:
        logger.exception("webhook_failed endpoint=omi_day_summary preview=%s", _preview_payload(payload))
        raise


@app.get("/webhook/omi/day-summary")
async def webhook_omi_day_summary_status() -> dict[str, Any]:
    return {"ok": True, "endpoint": "omi_day_summary", "method": "POST"}


@app.post("/webhook/omi/transcript", response_model=IngestResponse)
async def webhook_omi_transcript(
    payload: dict[str, Any],
    x_api_token: str | None = Header(default=None),
) -> IngestResponse:
    _verify_token(x_api_token)
    _log_webhook("omi_transcript", payload)
    node = ingest_omi_transcript(payload)
    write_snapshot_files()
    return IngestResponse(ok=True, node_id=node.id)


@app.post("/webhook/ara/action", response_model=IngestResponse)
async def webhook_ara_action(
    event: AraActionRequest,
    x_api_token: str | None = Header(default=None),
) -> IngestResponse:
    _verify_token(x_api_token)
    payload = model_dump_compat(event)
    _log_webhook("ara_action", payload)
    try:
        node = ingest_ara_event(payload)
    except ValueError as e:
        logger.info("skipped event: %s", e)
        return IngestResponse(ok=True, node_id=None, reason=str(e))
    write_snapshot_files()
    return IngestResponse(ok=True, node_id=node.id)


@app.post("/webhook/omi", response_model=IngestResponse)
async def webhook_omi_legacy(payload: dict[str, Any]) -> IngestResponse:
    """Backward-compatible alias for early hackathon wiring."""
    _log_webhook("omi_legacy", payload)
    node = ingest_omi_memory(payload)
    write_snapshot_files()
    return IngestResponse(ok=True, node_id=node.id)


@app.post("/webhook/ara", response_model=IngestResponse)
async def webhook_ara_legacy(event: dict[str, Any]) -> IngestResponse:
    """Backward-compatible alias for the original stub contract."""
    _log_webhook("ara_legacy", event)
    node = ingest_ara_event(
        {
            "action_type": event.get("event_type", "legacy_ara_event"),
            "content": str(event.get("output") or event.get("content") or ""),
            "metadata": {
                "input": event.get("input"),
                "output": event.get("output"),
            },
        }
    )
    write_snapshot_files()
    return IngestResponse(ok=True, node_id=node.id)


@app.get("/query")
async def query_memory(
    q: str = Query(..., min_length=1),
    k: int = Query(default=settings.semantic_top_k, ge=1, le=25),
    x_api_token: str | None = Header(default=None),
) -> dict[str, Any]:
    _verify_token(x_api_token)
    return build_context_pack(q, limit=k)


@app.get("/context/recent")
async def recent_context(
    hours: int = Query(default=6, ge=1, le=168),
    limit: int = Query(default=10, ge=1, le=50),
    x_api_token: str | None = Header(default=None),
) -> dict[str, Any]:
    _verify_token(x_api_token)
    return build_recent_context_pack(hours=hours, limit=limit)


@app.get("/graph", response_model=GraphResponse)
async def get_graph() -> GraphResponse:
    pagerank = memory_graph.compute_pagerank()
    nodes = [serialize_node(node, pagerank=pagerank.get(node.id, 0.0)) for node in memory_graph.get_all_nodes()]
    edges = [serialize_edge(edge) for edge in memory_graph.get_all_edges()]
    return GraphResponse(nodes=nodes, edges=edges)


@app.get("/export/memory-palace.json")
async def export_memory_palace_json() -> dict[str, Any]:
    snapshot = build_memory_snapshot_json()
    write_snapshot_files()
    return snapshot


@app.get("/export/memory-palace.md")
async def export_memory_palace_markdown() -> dict[str, str]:
    markdown = build_memory_snapshot_markdown()
    write_snapshot_files()
    return {
        "path": str(MARKDOWN_EXPORT_PATH.resolve()),
        "content": markdown,
    }


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    stats = memory_graph.stats()
    return HealthResponse(ok=True, **stats)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
