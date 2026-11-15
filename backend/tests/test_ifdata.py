from datetime import date

import pytest

from etl import ifdata


def test_url_has_prudential_resumo_and_filter():
    u = ifdata.build_url("202606")
    assert "@AnoMes=202606" in u and "@TipoInstituicao=1" in u and "@Relatorio='1'" in u
    assert "C0080329" in u and "%27" in u  # filtro codificado


def test_parse_maps_metrics_and_scales_basel():
    payload = {"value": [  # valores FICTÍCIOS
        {"CodInst": "C0080329", "Conta": "140220", "NomeColuna": "Ativo Total", "Saldo": 100.0},
        {"CodInst": "C0080329", "Conta": "79664", "NomeColuna": "Índice de Basileia", "Saldo": 0.139},
        {"CodInst": "C0080329", "Conta": "999", "NomeColuna": "Outra", "Saldo": 1.0},
        {"CodInst": "XXXX", "Conta": "140220", "NomeColuna": "Ativo Total", "Saldo": 5.0},
    ]}
    rows = {r.metric: r for r in ifdata.parse(payload, "202606")}
    assert set(rows) == {"ativo_total", "basileia"}
    assert rows["basileia"].value == pytest.approx(13.9) and rows["ativo_total"].period_end == date(2026, 6, 30)


def test_parse_rejects_unexpected():
    with pytest.raises(ifdata.IfDataFormatError):
        ifdata.parse({"erro": 1}, "202606")


def test_quarterly_profit_from_semester_accumulation():
    acc = {date(2026, 3, 31): 3.0, date(2026, 6, 30): 6.5, date(2025, 9, 30): 3.1, date(2025, 12, 31): 8.2}
    q = ifdata.quarterly_profit(acc)
    assert q[date(2026, 3, 31)][0] == 3.0
    assert q[date(2026, 6, 30)][0] == pytest.approx(3.5)
    assert q[date(2025, 12, 31)][0] == pytest.approx(5.1)
    assert q[date(2026, 6, 30)][1].startswith("derived:")


def test_quarterly_profit_needs_previous_quarter():
    assert date(2026, 6, 30) not in ifdata.quarterly_profit({date(2026, 6, 30): 6.5})
