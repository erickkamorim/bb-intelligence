"""Utilitários de período.

Distingue explicitamente: trimestre isolado (Q), acumulado no ano (YTD),
12 meses (LTM), posição em data (INSTANT) e ano fechado (FY).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum


class PeriodType(str, Enum):
    QUARTER = "quarter"      # trimestre isolado
    YTD = "ytd"              # acumulado no ano
    FY = "fy"                # exercício completo (12 meses jan-dez)
    LTM = "ltm"              # últimos 12 meses, janela móvel
    INSTANT = "instant"      # saldo em data (balanço)
    DAILY = "daily"
    MONTHLY = "monthly"


def quarter_of(d: date) -> int:
    return (d.month - 1) // 3 + 1


def quarter_start(d: date) -> date:
    return date(d.year, 3 * (quarter_of(d) - 1) + 1, 1)


def quarter_end(year: int, q: int) -> date:
    if q == 4:
        return date(year, 12, 31)
    return date(year, 3 * q + 1, 1) - timedelta(days=1)


def period_code(d: date) -> str:
    """2026-09-30 -> '2026Q3'."""
    return f"{d.year}Q{quarter_of(d)}"


def parse_period_code(code: str) -> tuple[date, date]:
    """'2026Q3' -> (2026-07-01, 2026-09-30)."""
    code = code.strip().upper()
    if len(code) != 6 or code[4] != "Q" or code[5] not in "1234":
        raise ValueError(f"Período inválido: {code!r}. Use o formato AAAAQn, ex.: 2026Q3")
    year, q = int(code[:4]), int(code[5])
    end = quarter_end(year, q)
    return quarter_start(end), end


def classify_window(start: date | None, end: date) -> PeriodType:
    """Classifica a janela de uma conta de resultado da CVM.

    - start ausente  -> INSTANT (contas de balanço)
    - começa em 1/jan e termina em 31/dez -> FY
    - começa em 1/jan -> YTD (no 1º trimestre YTD == trimestre; tratamos como QUARTER)
    - começa no início do trimestre de `end` -> QUARTER
    """
    if start is None:
        return PeriodType.INSTANT
    if start == date(end.year, 1, 1):
        if end == date(end.year, 12, 31):
            return PeriodType.FY
        if quarter_of(end) == 1:
            return PeriodType.QUARTER
        return PeriodType.YTD
    if start == quarter_start(end):
        return PeriodType.QUARTER
    raise ValueError(f"Janela não reconhecida: {start} a {end}")


@dataclass(frozen=True)
class DerivedValue:
    value: float
    method: str


def derive_q4(fy_value: float, ytd_9m_value: float) -> DerivedValue:
    """4º trimestre isolado = exercício (DFP) − acumulado 9M (ITR do 3T).

    O ITR não cobre o 4º trimestre; o valor é DERIVADO e deve ser marcado como tal.
    """
    return DerivedValue(fy_value - ytd_9m_value, "derived:FY_minus_9M_YTD")
