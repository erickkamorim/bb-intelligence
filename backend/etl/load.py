"""Gravação idempotente com versionamento de revisões.

- Mesma chave e mesmo valor  -> nada muda (idempotente).
- Mesma chave e valor novo   -> nova linha com revision+1 (histórico preservado).
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Document, EtlRun, IndicatorModel, Observation, Source
from .periods import derive_q4
from .registry import INDICATORS, SOURCES


@dataclass
class ObsIn:
    indicator_code: str
    period_start: date | None
    period_end: date
    period_type: str
    value: float
    published_at: datetime | None = None
    derivation: str | None = None
    extra: dict | None = None


def seed(session: Session) -> None:
    """Sincroniza fontes e dicionário de indicadores (sem valores)."""
    for s in SOURCES.values():
        row = session.scalar(select(Source).where(Source.code == s.code))
        checked = datetime.fromisoformat(s.verified_on).replace(tzinfo=timezone.utc) if s.verified_on else None
        if row is None:
            session.add(Source(code=s.code, name=s.name, url=s.url, license_notes=s.license_notes, checked_at=checked))
        else:
            row.name, row.url, row.license_notes, row.checked_at = s.name, s.url, s.license_notes, checked
    for i in INDICATORS.values():
        row = session.scalar(select(IndicatorModel).where(IndicatorModel.code == i.code))
        vals = dict(name=i.name, unit=i.unit, frequency=i.frequency, definition=i.definition, scope=i.scope)
        if row is None:
            session.add(IndicatorModel(code=i.code, **vals))
        else:
            for k, v in vals.items():
                setattr(row, k, v)
    session.flush()


def get_or_create_document(session: Session, source_code: str, document_type: str, url: str,
                           file_hash: str, retrieved_at: datetime, period: str | None = None,
                           published_at: datetime | None = None, locator: str | None = None) -> Document:
    src = session.scalar(select(Source).where(Source.code == source_code))
    if src is None:
        raise RuntimeError("Fonte não cadastrada — rode `python -m etl.cli seed` antes")
    doc = session.scalar(select(Document).where(Document.source_id == src.id, Document.file_hash == file_hash))
    if doc is None:
        doc = Document(source_id=src.id, document_type=document_type, url=url, file_hash=file_hash,
                       retrieved_at=retrieved_at, period=period, published_at=published_at, locator=locator)
        session.add(doc)
        session.flush()
    return doc


def upsert_observations(session: Session, doc: Document, rows: list[ObsIn]) -> tuple[int, int]:
    inserted = revised = 0
    ind_cache: dict[str, IndicatorModel] = {}
    for r in rows:
        ind = ind_cache.get(r.indicator_code) or session.scalar(
            select(IndicatorModel).where(IndicatorModel.code == r.indicator_code))
        if ind is None:
            raise RuntimeError(f"Indicador {r.indicator_code} não cadastrado")
        ind_cache[r.indicator_code] = ind
        meta = INDICATORS[r.indicator_code]
        key = (Observation.indicator_id == ind.id,
               Observation.period_start.is_(None) if r.period_start is None else Observation.period_start == r.period_start,
               Observation.period_end == r.period_end,
               Observation.period_type == r.period_type,
               Observation.entity_scope == meta.scope)
        latest = session.scalar(select(Observation).where(*key).order_by(Observation.revision.desc()).limit(1))
        new_val = Decimal(str(round(r.value, 6)))
        if latest is not None and Decimal(latest.value) == new_val:
            continue
        session.add(Observation(
            indicator_id=ind.id, period_start=r.period_start, period_end=r.period_end,
            period_type=r.period_type, value=new_val, unit=meta.unit, entity_scope=meta.scope,
            source_document_id=doc.id, published_at=r.published_at, retrieved_at=doc.retrieved_at,
            revision=0 if latest is None else latest.revision + 1,
            derivation=r.derivation, extra=r.extra,
        ))
        if latest is None:
            inserted += 1
        else:
            revised += 1
    session.flush()
    return inserted, revised


@contextmanager
def etl_run(session: Session, job_name: str):
    run = EtlRun(job_name=job_name, started_at=datetime.now(timezone.utc), status="running")
    session.add(run)
    session.commit()
    try:
        yield run
        run.status = "success"
    except Exception as exc:
        session.rollback()
        run = session.merge(run)
        run.status = "failed"
        run.error_message = f"{type(exc).__name__}: {exc}"[:4000]
        raise
    finally:
        run.ended_at = datetime.now(timezone.utc)
        session.commit()


def coverage(session: Session) -> list[dict]:
    """Resumo por indicador: nº de observações, primeiro e último período."""
    q = (select(IndicatorModel.code, func.count(Observation.id), func.min(Observation.period_end),
                func.max(Observation.period_end), func.max(Observation.retrieved_at))
         .join(Observation, Observation.indicator_id == IndicatorModel.id, isouter=True)
         .group_by(IndicatorModel.code).order_by(IndicatorModel.code))
    return [dict(indicator=c, n=n, first=f, last=l, retrieved=rt) for c, n, f, l, rt in session.execute(q)]


def derive_fourth_quarter(session: Session, year: int) -> int:
    """Cria o 4T isolado = exercício (DFP, fy) − acumulado 9M (ITR, ytd em 30/09).

    Só para indicadores de resultado (DRE). A observação fica marcada em `derivation`
    e aponta para o documento da DFP. Retorna quantas linhas foram inseridas/revisadas.
    """
    from datetime import date as _d
    total = 0
    for ind in INDICATORS.values():
        if ind.cvm is None or ind.cvm.statement != "DRE":
            continue
        im = session.scalar(select(IndicatorModel).where(IndicatorModel.code == ind.code))
        if im is None:
            continue

        def latest(period_type: str, start, end):
            return session.scalar(select(Observation).where(
                Observation.indicator_id == im.id, Observation.period_type == period_type,
                Observation.period_start == start, Observation.period_end == end,
            ).order_by(Observation.revision.desc()).limit(1))

        fy = latest("fy", _d(year, 1, 1), _d(year, 12, 31))
        ytd9 = latest("ytd", _d(year, 1, 1), _d(year, 9, 30))
        if fy is None or ytd9 is None:
            continue
        d = derive_q4(float(fy.value), float(ytd9.value))
        doc = session.get(Document, fy.source_document_id)
        i, r = upsert_observations(session, doc, [ObsIn(
            ind.code, _d(year, 10, 1), _d(year, 12, 31), "quarter", d.value,
            published_at=fy.published_at, derivation=d.method,
            extra={"fy_obs_id": fy.id, "ytd9_obs_id": ytd9.id})])
        total += i + r
    return total
