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
from etl.load import ObsIn, get_or_create_document, seed, upsert_observations, upsert_peer_values  # noqa: E402

Q = "quarter"
# componentes FICTÍCIOS que somam o lucro: 2T26 = 400, 3T26 = 100
COMP_2T = {"margem_financeira_bruta": 1000.0, "custo_credito": -500.0, "receitas_servicos": 200.0,
           "despesas_administrativas": -250.0, "outras_receitas_despesas_op": -20.0, "provisoes": -10.0,
           "resultado_nao_operacional": 0.0, "ir_csll": 10.0, "participacoes_estatutarias": -10.0,
           "participacoes_minoritarias": -20.0}
COMP_3T = {**COMP_2T, "custo_credito": -800.0}


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
            ObsIn("inad_90", date(2026, 4, 1), date(2026, 6, 30), Q, 5.6),
            ObsIn("inad_90", date(2026, 7, 1), date(2026, 9, 30), Q, 6.1),
        ] + [ObsIn(c, date(2026, 4, 1), date(2026, 6, 30), Q, v2) for c, v2 in COMP_2T.items()]
          + [ObsIn(c, date(2026, 7, 1), date(2026, 9, 30), Q, v3) for c, v3 in COMP_3T.items()])
        sgs = get_or_create_document(s, "bcb_sgs", "SGS", "https://api.bcb.gov.br/x", "h-sgs", now)
        upsert_observations(s, sgs, [ObsIn("ipca_mensal", None, date(2026, m, 1), "monthly", 0.5)
                                     for m in range(1, 10)] +
                            [ObsIn("ipca_mensal", None, date(2025, m, 1), "monthly", 0.5) for m in range(10, 13)])
        ifd = get_or_create_document(s, "bcb_ifdata", "IFDATA_RESUMO", "https://olinda.bcb.gov.br/x", "h-if", now)
        from etl.ifdata import PeerRow
        rows = []
        for cod, name, pl, l1, l2 in [("C0080329", "Banco do Brasil", 100.0, 3.0, 6.0), ("C0080099", "Itaú", 200.0, 10.0, 21.0)]:
            for end, lucro in [(date(2026, 3, 31), l1), (date(2026, 6, 30), l2)]:
                rows += [PeerRow(cod, name, end, "patrimonio_liquido", pl, "BRL"),
                         PeerRow(cod, name, end, "lucro_semestre_acum", lucro, "BRL"),
                         PeerRow(cod, name, end, "basileia", 14.0, "pct")]
        upsert_peer_values(s, ifd, rows)
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


def test_series_compact(client):
    body = client.get("/api/v1/series/ipca_mensal?compact=true").json()
    assert set(body["data"][0]) == {"period_end", "value"}
    assert body["meta"]["source"]["source_code"] == "bcb_sgs"


def test_bridge_closes(client):
    d = client.get("/api/v1/results/bridge?period=2026Q3").json()["data"]
    assert d["status"] == "ok" and d["from_period"] == "2026Q2"
    assert d["start"] == 400.0 and d["end"] == 100.0 and d["closes"] is True
    assert d["steps"][0] == {"code": "custo_credito", "label": "Custo do crédito", "delta": -300.0}


def test_bridge_missing_period(client):
    d = client.get("/api/v1/results/bridge?period=2025Q3").json()["data"]
    assert d["status"] == "missing"


def test_alerts_flag_adverse_moves(client):
    al = {a["code"]: a for a in client.get("/api/v1/alerts?period=2026Q3").json()["data"]}
    assert al["inad_90"]["tone"] == "negative" and al["inad_90"]["delta_unit"] == "p.p."
    assert al["custo_credito"]["tone"] == "negative" and al["custo_credito"]["delta"] == 60.0
    assert al["lucro_liquido_ajustado"]["compare"] == "t/t"


def test_notes_endpoint(client):
    body = client.get("/api/v1/notes?period=2026Q3").json()
    assert body["data"] and all(n["source_locator"] for n in body["data"])


def test_peers_quarterly_profit_and_roe(client):
    d = client.get("/api/v1/peers").json()["data"]
    assert d["status"] == "ok" and d["period"] == "2026Q2"
    bb = next(b for b in d["banks"] if b["is_bb"])
    assert bb["lucro_trimestre"] == 3.0 and bb["lucro_derivacao"].startswith("derived:")
    assert round(bb["roe_anualizado"], 2) == 12.0
    assert d["bb_rank"]["roe_anualizado"] == {"position": 2, "of": 2}  # Itaú: 11 × 4 / 200 = 22%
