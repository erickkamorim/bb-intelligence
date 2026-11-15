from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.orm import Session


def get_db() -> Iterator[Session]:
    from app.db.session import SessionLocal  # import tardio: os testes trocam esta dependência
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
