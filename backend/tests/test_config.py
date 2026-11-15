from app.core.config import _normalize_db_url


def test_normalize_db_url():
    assert _normalize_db_url("postgresql://u:p@h/db?sslmode=require") == "postgresql+psycopg://u:p@h/db?sslmode=require"
    assert _normalize_db_url("postgres://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert _normalize_db_url("postgresql+psycopg://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
