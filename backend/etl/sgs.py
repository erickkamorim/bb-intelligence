"""Cliente do SGS (Banco Central).

Endpoint documentado no portal de dados abertos do BCB:
  https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json&dataInicial=dd/MM/aaaa&dataFinal=dd/MM/aaaa
Desde 26/03/2025 séries diárias exigem filtro de datas, com janela máxima de 10 anos.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable

BASE = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"
MAX_WINDOW_DAYS = 365 * 10 - 3  # margem para anos bissextos


class SgsFormatError(ValueError):
    pass


@dataclass(frozen=True)
class SgsPoint:
    date: date
    value: float


def windows(start: date, end: date, max_days: int = MAX_WINDOW_DAYS) -> list[tuple[date, date]]:
    if start > end:
        raise ValueError("start > end")
    out: list[tuple[date, date]] = []
    cur = start
    while cur <= end:
        w_end = min(cur + timedelta(days=max_days), end)
        out.append((cur, w_end))
        cur = w_end + timedelta(days=1)
    return out


def build_url(code: int, start: date, end: date) -> str:
    if (end - start).days > MAX_WINDOW_DAYS:
        raise ValueError("Janela acima de 10 anos — use windows()")
    return (f"{BASE.format(code=code)}?formato=json"
            f"&dataInicial={start:%d/%m/%Y}&dataFinal={end:%d/%m/%Y}")


def parse(payload: object) -> list[SgsPoint]:
    """Converte a resposta JSON ([{"data": "dd/mm/aaaa", "valor": "1.23"}, ...])."""
    if isinstance(payload, dict) and "error" in payload:
        raise SgsFormatError(f"Erro retornado pela API: {payload}")
    if not isinstance(payload, list):
        raise SgsFormatError(f"Esperada lista, recebido {type(payload).__name__}")
    pts: list[SgsPoint] = []
    for item in payload:
        try:
            d = datetime.strptime(item["data"], "%d/%m/%Y").date()
            v = float(str(item["valor"]).replace(",", "."))
        except (KeyError, ValueError, TypeError) as exc:
            raise SgsFormatError(f"Item inválido: {item!r}") from exc
        pts.append(SgsPoint(d, v))
    return pts


def dedupe(points: Iterable[SgsPoint]) -> list[SgsPoint]:
    """Janelas adjacentes podem repetir a data de borda; mantém a última ocorrência."""
    by_date = {p.date: p for p in points}
    return [by_date[d] for d in sorted(by_date)]


def fetch(code: int, start: date, end: date, session=None, timeout: float = 30.0) -> list[SgsPoint]:
    import requests  # import tardio: os testes de parsing não exigem rede

    s = session or requests.Session()
    pts: list[SgsPoint] = []
    for a, b in windows(start, end):
        r = s.get(build_url(code, a, b), timeout=timeout, headers={"Accept": "application/json"})
        if r.status_code == 404:
            continue  # sem dados na janela
        r.raise_for_status()
        pts.extend(parse(r.json()))
    return dedupe(pts)
