"""Environment-driven configuration for the Memory Palace backend."""

from __future__ import annotations

import os
import tempfile
from functools import lru_cache

from pydantic import BaseModel, Field


class Settings(BaseModel):
    db_path: str = Field(default_factory=lambda: os.path.join(tempfile.gettempdir(), "memory_palace.db"))
    api_base: str = Field(default="http://localhost:8000")
    api_token: str = Field(default="dev-token")
    omi_api_base: str = Field(default="https://api.omi.me/v1/dev/user")
    omi_api_key: str | None = Field(default=None)
    embedding_model_name: str = Field(default="all-MiniLM-L6-v2")
    fallback_embedding_dim: int = Field(default=128)
    semantic_top_k: int = Field(default=6)
    semantic_threshold: float = Field(default=0.35)
    recent_context_hours: int = Field(default=6)
    recent_context_limit: int = Field(default=8)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    default_db_path = os.path.join(tempfile.gettempdir(), "memory_palace.db")
    return Settings(
        db_path=os.getenv("MEMORY_PALACE_DB", default_db_path),
        api_base=os.getenv("MEMORY_PALACE_API_BASE", "http://localhost:8000"),
        api_token=os.getenv("MEMORY_PALACE_API_TOKEN", "dev-token"),
        omi_api_base=os.getenv("OMI_API_BASE", "https://api.omi.me/v1/dev/user"),
        omi_api_key=os.getenv("OMI_API_KEY"),
        embedding_model_name=os.getenv("MEMORY_PALACE_EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        fallback_embedding_dim=int(os.getenv("MEMORY_PALACE_FALLBACK_EMBED_DIM", "128")),
        semantic_top_k=int(os.getenv("MEMORY_PALACE_TOP_K", "6")),
        semantic_threshold=float(os.getenv("MEMORY_PALACE_SEMANTIC_THRESHOLD", "0.35")),
        recent_context_hours=int(os.getenv("MEMORY_PALACE_RECENT_HOURS", "6")),
        recent_context_limit=int(os.getenv("MEMORY_PALACE_RECENT_LIMIT", "8")),
    )
