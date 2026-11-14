"""Testes de carga com SQLite em memória (o PostgreSQL real é usado no fluxo ponta a ponta)."""
from datetime import date, datetime, timezone

import pytest

sa = pytest.importorskip("sqlalchemy")

from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db.models import Base, EtlRun, Observation  # noqa: E402
from etl import cvm  # noqa: E402
from etl.load import ObsIn, etl_run, get_or_create_document, seed, upsert_observations  # noqa: E402
from etl.registry import INDICATORS  # noqa: E402

pytestmark = pytest.mark.db


@pytest.fixture
def session():
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng)
    with Session(eng) as s:
        seed(s)
        s.commit()
        yield s


def _doc(s, h="h1"):
    return get_or_create_document(s, "cvm_itr", "ITR", "https://dados.cvm.gov.br/x.zip", h,
                                  datetime.now(timezone.utc), period="2026")


def test_end_to_end_parse_and_load(session, itr_zip):
    df = cvm.normalize(cvm.read_statement(itr_zip, "DRE"))
    obs = cvm.extract(df, INDICATORS["lucro_liquido_contabil"])
    rows = [ObsIn(o.indicator_code, o.period_start, o.period_end, o.period_type, o.value) for o in obs]
    ins, rev = upsert_observations(session, _doc(session), rows)
    assert (ins, rev) == (3, 0)
    # rodar de novo não duplica (idempotência)
    assert upsert_observations(session, _doc(session), rows) == (0, 0)


def test_revision_is_versioned(session):
    r = ObsIn("lucro_liquido_contabil", date(2026, 4, 1), date(2026, 6, 30), "quarter", 10.0)
    upsert_observations(session, _doc(session), [r])
    r2 = ObsIn(**{**r.__dict__, "value": 11.0})
    assert upsert_observations(session, _doc(session, "h2"), [r2]) == (0, 1)
    revs = session.scalars(select(Observation.revision).order_by(Observation.revision)).all()
    assert revs == [0, 1]


def test_etl_run_records_failure(session):
    with pytest.raises(RuntimeError):
        with etl_run(session, "teste"):
            raise RuntimeError("falha simulada")
    run = session.scalars(select(EtlRun)).one()
    assert run.status == "failed" and "falha simulada" in run.error_message
