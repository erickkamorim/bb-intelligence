from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _normalize_db_url(url: str) -> str:
    """Aceita a URL como Neon/Supabase entregam (postgres:// ou postgresql://) e usa o driver psycopg 3."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


class Settings:
    database_url: str = _normalize_db_url(
        os.getenv("DATABASE_URL", "postgresql+psycopg://bb:bb@localhost:5432/bb_intelligence"))
    raw_dir: Path = Path(os.getenv("RAW_DATA_DIR", ROOT / "data" / "raw"))
    http_timeout: float = float(os.getenv("HTTP_TIMEOUT", "120"))
    user_agent: str = os.getenv("HTTP_USER_AGENT", "BB-Intelligence-ETL/0.1 (projeto independente)")


settings = Settings()
