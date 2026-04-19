"""Omi payload normalization and optional polling client."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

import httpx

from config import get_settings
from models import OmiConversationRecord, OmiMemoryEvent, OmiTranscriptChunk


def _parse_timestamp(raw: Any) -> datetime:
    if isinstance(raw, datetime):
        return raw.astimezone(timezone.utc) if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _extract_action_items(value: Any) -> list[str]:
    items: list[str] = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                description = str(item.get("description") or item.get("title") or "").strip()
                if description:
                    items.append(description)
            else:
                text = str(item).strip()
                if text:
                    items.append(text)
    elif isinstance(value, str) and value.strip():
        items.append(value.strip())
    return items


def _extract_people(payload: dict[str, Any], structured: dict[str, Any], transcript_segments: list[dict[str, Any]]) -> list[str]:
    people = _string_list(payload.get("people") or structured.get("people"))
    for segment in transcript_segments:
        speaker_name = str(segment.get("speaker_name") or segment.get("person_name") or "").strip()
        if speaker_name and speaker_name not in people and not speaker_name.startswith("SPEAKER_"):
            people.append(speaker_name)
    return people


def _segments_to_text(segments: list[dict[str, Any]]) -> str | None:
    texts = [str(segment.get("text") or "").strip() for segment in segments]
    cleaned = [text for text in texts if text]
    if not cleaned:
        return None
    return " ".join(cleaned)


class OmiAdapter:
    """Normalize webhook payloads and expose optional polling helpers."""

    def __init__(self, *, api_base: str | None = None, api_token: str | None = None) -> None:
        settings = get_settings()
        base = api_base or settings.omi_api_base
        self.api_base = base.rstrip("/") if base else None
        self.api_token = api_token or settings.omi_api_key

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    def handle_memory_webhook(self, payload: dict[str, Any]) -> OmiMemoryEvent:
        structured = payload.get("structured")
        if not isinstance(structured, dict):
            structured = {}
        transcript_segments = list(payload.get("transcript_segments") or [])
        transcript_text = (
            payload.get("transcript")
            or payload.get("transcript_text")
            or _segments_to_text(transcript_segments)
        )
        summary = (
            payload.get("summary")
            or payload.get("text")
            or structured.get("overview")
            or structured.get("title")
            or structured.get("summary")
            or payload.get("title")
            or transcript_text
            or "Untitled Omi memory"
        )
        people = _extract_people(payload, structured, transcript_segments)
        action_items = _extract_action_items(payload.get("action_items") or structured.get("action_items"))
        client = str(
            payload.get("client")
            or payload.get("device_type")
            or payload.get("source")
            or "unknown"
        )
        return OmiMemoryEvent(
            omi_id=str(payload.get("id") or payload.get("memory_id") or "") or None,
            timestamp=_parse_timestamp(
                payload.get("timestamp")
                or payload.get("created_at")
                or payload.get("finished_at")
                or payload.get("started_at")
            ),
            summary=str(summary),
            transcript_text=str(transcript_text) if transcript_text else None,
            action_items=action_items,
            people=people,
            client=client,
            raw_payload=payload,
        )

    def handle_day_summary_webhook(self, payload: dict[str, Any]) -> OmiMemoryEvent:
        sections = payload.get("sections") or payload.get("highlights") or []
        summary_bits = [str(payload.get("summary") or payload.get("title") or "").strip()]
        if isinstance(sections, list):
            summary_bits.extend(str(item).strip() for item in sections if str(item).strip())
        summary = " | ".join(bit for bit in summary_bits if bit) or "Omi day summary"
        action_items = _extract_action_items(payload.get("action_items") or payload.get("tasks"))
        return OmiMemoryEvent(
            omi_id=str(payload.get("id") or payload.get("day_summary_id") or "") or None,
            timestamp=_parse_timestamp(payload.get("timestamp") or payload.get("created_at") or payload.get("date")),
            summary=summary,
            transcript_text=None,
            action_items=action_items,
            people=_string_list(payload.get("people")),
            client=str(payload.get("source") or payload.get("client") or "unknown"),
            raw_payload=payload,
        )

    def handle_transcript_webhook(self, payload: dict[str, Any]) -> OmiTranscriptChunk:
        session_id = str(payload.get("session_id") or payload.get("conversation_id") or "unknown-session")
        text = str(payload.get("text") or payload.get("transcript") or "").strip()
        chunk_id = str(payload.get("chunk_id") or payload.get("id") or hashlib.sha1(text.encode("utf-8")).hexdigest()[:12])
        return OmiTranscriptChunk(
            session_id=session_id,
            chunk_id=chunk_id,
            timestamp=_parse_timestamp(payload.get("timestamp") or payload.get("created_at")),
            text=text or "(empty transcript chunk)",
            speaker=payload.get("speaker"),
            is_user=payload.get("is_user"),
            raw_payload=payload,
        )

    def normalize_conversation(self, payload: dict[str, Any]) -> OmiConversationRecord:
        return OmiConversationRecord(
            conversation_id=str(payload.get("id") or payload.get("conversation_id") or "unknown-conversation"),
            started_at=_parse_timestamp(payload.get("started_at")) if payload.get("started_at") else None,
            finished_at=_parse_timestamp(payload.get("finished_at")) if payload.get("finished_at") else None,
            overview=payload.get("overview") or payload.get("summary"),
            transcript_segments=list(payload.get("transcript_segments") or []),
            raw_payload=payload,
        )

    async def list_recent_memories(self, since_ts: str | None = None) -> list[dict[str, Any]]:
        if not self.api_base:
            return []
        params = {"since": since_ts} if since_ts else None
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f"{self.api_base}/memories", params=params, headers=self._headers())
            response.raise_for_status()
            data = response.json()
        return list(data if isinstance(data, list) else data.get("memories", []))

    async def list_recent_conversations(self, since_ts: str | None = None) -> list[dict[str, Any]]:
        if not self.api_base:
            return []
        params = {"since": since_ts} if since_ts else None
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f"{self.api_base}/conversations", params=params, headers=self._headers())
            response.raise_for_status()
            data = response.json()
        return list(data if isinstance(data, list) else data.get("conversations", []))

    async def list_recent_action_items(self, since_ts: str | None = None) -> list[dict[str, Any]]:
        if not self.api_base:
            return []
        params = {"since": since_ts} if since_ts else None
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f"{self.api_base}/action-items", params=params, headers=self._headers())
            response.raise_for_status()
            data = response.json()
        return list(data if isinstance(data, list) else data.get("action_items", []))
