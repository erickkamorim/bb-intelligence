"""Testes da API com SQLite em memória. Valores FICTÍCIOS."""
from datetime import date, datetime, timezone

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.api.deps import get_db  # noqa: E402
from app.db.models import Base  # noqa: E402
from app.main import app  # noqa: E402
from etl.load import ObsIn, get_or_create_document, seed, upsert_observations  # noqa: E402

Q = "quarter"


@pytest.fixture
def client():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng, expire_on_commit=False)
    with Session() as s:
        seed(s)
        now = datetime.now(timezone.utc)
        ri = get_or_create_document(s, "ri_bb", "RI_RELEASE", "https://ri.bb.com.br/x", "h-ri", now,
                                    locator="Tabela 1, p. 10")
        upsert_observations(s, ri, [
            ObsIn("lucro_liquido_ajustado", date(2025, 7, 1), date(2025, 9, 30), Q, 300.0),
            ObsIn("lucro_liquido_ajustado", date(2026, 4, 1), date(2026, 6, 30), Q, 400.0),
            ObsIn("lucro_liquido_ajustado", date(2026, 7, 1), date(2026, 9, 30), Q, 100.0),
            ObsIn("roe_ajustado", date(2026, 4, 1), date(2026, 6, 30), Q, 8.3),
            ObsIn("roe_ajustado", date(2026, 7, 1), date(2026, 9, 30), Q, 2.8),
            ObsIn("carteira_credito_ampliada", date(2026, 7, 1), date(2026, 9, 30), Q, 1000.0),
            ObsIn("carteira_pf", date(2026, 7, 1), date(2026, 9, 30), Q, 300.0),
            ObsIn("carteira_pj", date(2026, 7, 1), date(2026, 9, 30), Q, 350.0),
            ObsIn("carteira_agro", date(2026, 7, 1), date(2026, 9, 30), Q, 300.0),
        ])
        sgs = get_or_create_document(s, "bcb_sgs", "SGS", "https://api.bcb.gov.br/x", "h-sgs", now)
        upsert_observations(s, sgs, [ObsIn("ipca_mensal", None, date(2026, m, 1), "monthly", 0.5)
                                     for m in range(1, 10)] +
                            [ObsIn("ipca_mensal", None, date(2025, m, 1), "monthly", 0.5) for m in range(10, 13)])
        s.commit()

    def _db():
        with Session() as s:
            yield s
    app.dependency_overrides[get_db] = _db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200 and r.json()["data"]["database"] is True
    assert "não oficial" in r.json()["meta"]["disclaimer"]


def test_periods_latest_first(client):
    codes = [p["code"] for p in client.get("/api/v1/periods").json()["data"]]
    assert codes[0] == "2026Q3" and "2026Q2" in codes


def test_indicators_snapshot_with_deltas_and_source(client):
    body = client.get("/api/v1/indicators?period=2026Q3").json()
    by = {i["code"]: i for i in body["data"]}
    lla = by["lucro_liquido_ajustado"]
    assert lla["status"] == "ok" and lla["value"] == 100.0
    assert lla["qoq"] == {"value": -75.0, "unit": "%"}
    assert lla["yoy"]["unit"] == "%" and round(lla["yoy"]["value"], 2) == -66.67
    assert lla["locator"] == "Tabela 1, p. 10" and lla["source_code"] == "ri_bb"
    assert by["roe_ajustado"]["qoq"] == {"value": -5.5, "unit": "p.p."}
    assert by["lucro_liquido_contabil"]["status"] == "missing"   # ausência explícita, nunca zero
    assert by["ipca_mensal"]["ipca_12m"]["derivation"].startswith("derived:")


def test_indicators_default_and_invalid_period(client):
    assert client.get("/api/v1/indicators").json()["meta"]["period"] == "2026Q3"
    r = client.get("/api/v1/indicators?period=2026Q9")
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_period"


def test_series(client):
    body = client.get("/api/v1/series/lucro_liquido_ajustado?from=2026-01-01").json()
    assert [p["period_end"] for p in body["data"]] == ["2026-06-30", "2026-09-30"]
    assert body["meta"]["indicator"]["unit"] == "BRL"
    r = client.get("/api/v1/series/inventado")
    assert r.status_code == 404 and r.json()["error"]["code"] == "unknown_indicator"


def test_credit_segments_shares(client):
    d = client.get("/api/v1/credit/segments?period=2026Q3").json()["data"]
    shares = {s["code"]: s["share_pct"] for s in d["segments"]}
    assert shares == {"carteira_pf": 30.0, "carteira_pj": 35.0, "carteira_agro": 30.0, "outros": 5.0}
    assert d["segments"][-1]["derivation"] == "derived:total_minus_segments"


def test_data_quality_and_events(client):
    dq = client.get("/api/v1/data-quality").json()["data"]
    st = {i["code"]: i["status"] for i in dq["indicators"]}
    assert st["dolar_ptax_venda"] == "missing" and st["lucro_liquido_ajustado"] in {"ok", "stale"}
    ev = client.get("/api/v1/events").json()
    assert ev["data"] == [] and ev["meta"]["status"] == "not_collected"


def test_unknown_route_is_json_error(client):
    r = client.get("/api/v1/nada")
    assert r.status_code == 404 and "error" in r.json()
