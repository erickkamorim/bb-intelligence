from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services import queries as q
from etl.periods import parse_period_code
from etl.registry import INDICATORS

router = APIRouter(prefix="/api/v1")

API_VERSION = "1.0.0"
DISCLAIMER = ("Projeto independente, não oficial e não afiliado ao Banco do Brasil. "
              "Informações para fins analíticos, não recomendação de investimento.")


def envelope(data, **extra) -> dict:
    return {"data": data, "meta": {"api_version": API_VERSION, "generated_at": datetime.now(timezone.utc),
                                   "disclaimer": DISCLAIMER, **extra}}


def _period_or_latest(db: Session, period: str | None) -> str:
    if period:
        try:
            parse_period_code(period)
        except ValueError as exc:
            raise HTTPException(400, detail={"code": "invalid_period", "message": str(exc)})
        return period.upper()
    periods = q.available_periods(db)
    if not periods:
        raise HTTPException(404, detail={"code": "no_data", "message": "Nenhum período carregado ainda."})
    return periods[0]["code"]


@router.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:  # noqa: BLE001
        db_ok = False
    return envelope({"status": "ok" if db_ok else "degraded", "database": db_ok})


@router.get("/periods")
def periods(db: Session = Depends(get_db)):
    return envelope(q.available_periods(db))


@router.get("/indicators")
def indicators(period: str | None = Query(None, description="AAAAQn, ex.: 2026Q3. Padrão: último disponível"),
               db: Session = Depends(get_db)):
    p = _period_or_latest(db, period)
    return envelope(q.indicator_snapshot(db, p), period=p)


@router.get("/series/{code}")
def series(code: str,
           from_: date | None = Query(None, alias="from"),
           to: date | None = Query(None),
           period_type: str | None = Query(None, description="quarter | ytd | fy | instant | daily | monthly"),
           db: Session = Depends(get_db)):
    meta = INDICATORS.get(code)
    ind = q.indicator_by_code(db, code) if meta else None
    if meta is None or ind is None:
        raise HTTPException(404, detail={"code": "unknown_indicator", "message": f"Indicador '{code}' não existe."})
    if period_type is None:
        if meta.frequency != "quarterly":
            period_type = meta.sgs_period_type or "daily"
        else:
            period_type = "instant" if (meta.cvm and meta.cvm.statement in {"BPA", "BPP"}) else "quarter"
    rows = q.observations(db, ind, period_type=period_type, start=from_, end=to)
    points = [{"period_start": o.period_start, "period_end": o.period_end, "value": float(o.value),
               **q.source_meta(o, d, s)} for o, d, s in rows]
    return envelope(points, indicator={"code": code, "name": meta.name, "unit": meta.unit, "scope": meta.scope,
                                       "definition": meta.definition, "period_type": period_type},
                    count=len(points), status="ok" if points else "missing")


@router.get("/credit/segments")
def credit_segments(period: str | None = Query(None), db: Session = Depends(get_db)):
    p = _period_or_latest(db, period)
    return envelope(q.credit_segments(db, p), period=p)


@router.get("/data-quality")
def data_quality(db: Session = Depends(get_db)):
    return envelope(q.data_quality(db))


@router.get("/events")
def events():
    # Agenda oficial ainda não coletada: devolver vazio com status explícito, nunca datas inventadas.
    return envelope([], status="not_collected",
                    note="Agenda de eventos do RI ainda não integrada (Etapa 1b).")
