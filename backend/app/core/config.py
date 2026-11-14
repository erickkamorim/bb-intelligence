from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


class Settings:
    database_url: str = os.getenv("DATABASE_URL", "postgresql+psycopg://bb:bb@localhost:5432/bb_intelligence")
    raw_dir: Path = Path(os.getenv("RAW_DATA_DIR", ROOT / "data" / "raw"))
    http_timeout: float = float(os.getenv("HTTP_TIMEOUT", "120"))
    user_agent: str = os.getenv("HTTP_USER_AGENT", "BB-Intelligence-ETL/0.1 (projeto independente)")


settings = Settings()
