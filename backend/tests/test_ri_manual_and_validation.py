from datetime import date

import pytest

from etl import ri_manual, validation

HEAD = "indicator_code,period,value,unit,source_url,source_locator,published_at,collected_by\n"


def _write(tmp_path, body):
    p = tmp_path / "ri.csv"
    p.write_text(HEAD + body, encoding="utf-8")
    return p


def test_ri_manual_accepts_well_formed_line(tmp_path):
    # valor FICTÍCIO, apenas para o teste
    p = _write(tmp_path, "roe_ajustado,2026Q2,12.3,pct,https://ri.bb.com.br/x.pdf,p. 5 tabela 1,2026-08-10,erick\n")
    [o] = ri_manual.load_csv(p)
    assert o.period_end == date(2026, 6, 30) and o.value == 12.3


@pytest.mark.parametrize("line,msg", [
    ("roe_ajustado,2026Q2,12.3,pct,https://blog.qualquer.com/x,p.5,2026-08-10,e\n", "hosts oficiais"),
    ("roe_ajustado,2026Q2,12.3,pct,https://ri.bb.com.br/x,,2026-08-10,e\n", "source_locator"),
    ("roe_ajustado,2026Q2,12.3,BRL,https://ri.bb.com.br/x,p.5,2026-08-10,e\n", "unidade"),
    ("roe_ajustado,2026Q2,0.123e4,pct,https://ri.bb.com.br/x,p.5,2026-08-10,e\n", "percentual"),
    ("roe_ajustado,2026Q2,12.3,pct,https://ri.bb.com.br/x,p.5,2026-05-01,e\n", "anterior"),
    ("selic_meta,2026Q2,15,pct_aa,https://ri.bb.com.br/x,p.5,2026-08-10,e\n", "não é um indicador"),
    ("inventado,2026Q2,1,pct,https://ri.bb.com.br/x,p.5,2026-08-10,e\n", "desconhecido"),
])
def test_ri_manual_rejects(tmp_path, line, msg):
    with pytest.raises(ri_manual.ManualDataError, match=msg):
        ri_manual.load_csv(_write(tmp_path, line))


def test_quarter_sum_ok_and_error():
    q = {date(2026, 3, 31): 100.0, date(2026, 6, 30): 120.0}
    assert not validation.has_errors(validation.check_quarter_sum(q, {date(2026, 6, 30): 220.0}, "x"))
    assert validation.has_errors(validation.check_quarter_sum(q, {date(2026, 6, 30): 300.0}, "x"))


def test_gaps_and_duplicates():
    gaps = validation.check_gaps([date(2025, 12, 31), date(2026, 6, 30)], "x")
    assert "2026Q1" in gaps[0].message
    assert validation.check_no_duplicates([(1,), (1,)], "x")[0].severity == "error"
    assert validation.check_finite([1.0, float("nan")], "x")


def test_ri_manual_ytd_rows(tmp_path):
    p = tmp_path / "ri.csv"
    p.write_text(HEAD.strip() + ",period_type\n"
                 "lucro_liquido_ajustado,2026Q3,100,BRL,https://ri.bb.com.br/x.pdf,p. 10,2026-11-11,e,ytd\n"
                 "roe_ajustado,2026Q3,2.8,pct,https://ri.bb.com.br/x.pdf,p. 10,2026-11-11,e,\n", encoding="utf-8")
    a, b = ri_manual.load_csv(p)
    assert a.period_type == "ytd" and a.period_start == date(2026, 1, 1)
    assert b.period_type == "quarter" and b.period_start == date(2026, 7, 1)
