from datetime import date

import pytest

from etl import sgs


def test_build_url_format():
    url = sgs.build_url(432, date(2024, 1, 1), date(2024, 12, 31))
    assert url == ("https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados?formato=json"
                   "&dataInicial=01/01/2024&dataFinal=31/12/2024")


def test_windows_respect_10_year_limit():
    ws = sgs.windows(date(2000, 1, 1), date(2026, 11, 14))
    assert ws[0][0] == date(2000, 1, 1) and ws[-1][1] == date(2026, 11, 14)
    assert all((b - a).days <= sgs.MAX_WINDOW_DAYS for a, b in ws)
    assert all((ws[i + 1][0] - ws[i][1]).days == 1 for i in range(len(ws) - 1))


def test_build_url_rejects_long_window():
    with pytest.raises(ValueError):
        sgs.build_url(432, date(2000, 1, 1), date(2026, 1, 1))


def test_parse_and_dedupe():
    payload = [{"data": "02/01/2026", "valor": "15.00"}, {"data": "03/01/2026", "valor": "15,00"}]
    pts = sgs.dedupe(sgs.parse(payload) + sgs.parse(payload[:1]))
    assert [p.date for p in pts] == [date(2026, 1, 2), date(2026, 1, 3)]
    assert pts[1].value == 15.0


@pytest.mark.parametrize("bad", [{"error": "x"}, "texto", [{"data": "2026-01-02", "valor": "1"}], [{"valor": "1"}]])
def test_parse_rejects_bad_payload(bad):
    with pytest.raises(sgs.SgsFormatError):
        sgs.parse(bad)


@pytest.mark.integration
def test_live_selic_last_values():
    import requests
    r = requests.get("https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/2?formato=json", timeout=30)
    r.raise_for_status()
    assert len(sgs.parse(r.json())) == 2
