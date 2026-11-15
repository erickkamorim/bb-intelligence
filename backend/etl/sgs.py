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


def _get_json(s, url: str, timeout: float, attempts: int, wait: float, sleep):
    """GET com novas tentativas: o SGS às vezes responde 5xx ou HTML no lugar de JSON."""
    last: Exception | None = None
    for i in range(attempts):
        try:
            r = s.get(url, timeout=timeout, headers={"Accept": "application/json"})
            if r.status_code == 404:
                return None  # sem dados na janela
            if r.status_code >= 500 or r.status_code == 429:
                raise SgsFormatError(f"HTTP {r.status_code}")
            r.raise_for_status()
            try:
                return r.json()
            except ValueError as exc:
                raise SgsFormatError("resposta não é JSON") from exc
        except Exception as exc:  # noqa: BLE001 - erros de rede e de formato entram no retry
            last = exc
            if i < attempts - 1:
                sleep(wait * (2 ** i))
    raise SgsFormatError(f"SGS indisponível após {attempts} tentativas ({url}): {last}")


def fetch(code: int, start: date, end: date, session=None, timeout: float = 30.0,
          attempts: int = 5, wait: float = 5.0, sleep=None) -> list[SgsPoint]:
    import time

    import requests  # import tardio: os testes de parsing não exigem rede

    s = session or requests.Session()
    sleep = sleep or time.sleep
    pts: list[SgsPoint] = []
    for a, b in windows(start, end):
        payload = _get_json(s, build_url(code, a, b), timeout, attempts, wait, sleep)
        if payload is not None:
            pts.extend(parse(payload))
    return dedupe(pts)
