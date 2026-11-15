"""Curadoria manual de indicadores gerenciais do RI do Banco do Brasil.

Por que manual na Etapa 1: os releases/planilhas do RI não têm API documentada,
e o formato muda entre trimestres. Cada linha precisa apontar para o documento
oficial e a página/aba de onde o número saiu — sem isso, a linha é rejeitada.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

from .periods import parse_period_code
from .registry import INDICATORS

REQUIRED = ["indicator_code", "period", "value", "unit", "source_url", "source_locator",
            "published_at", "collected_by"]
# Hosts onde o RI do BB publica arquivos. api.mziq.com hospeda os PDFs do RI.
ALLOWED_HOSTS = {"ri.bb.com.br", "api.mziq.com"}


class ManualDataError(ValueError):
    pass


@dataclass
class ManualObservation:
    indicator_code: str
    period_start: date
    period_end: date
    value: float
    unit: str
    source_url: str
    source_locator: str
    published_at: date
    collected_by: str


def load_csv(path: str | Path) -> list[ManualObservation]:
    df = pd.read_csv(path, dtype=str, comment="#").fillna("")
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ManualDataError(f"Colunas ausentes: {missing}")

    errors: list[str] = []
    out: list[ManualObservation] = []
    for i, r in df.iterrows():
        line = i + 2
        code = r["indicator_code"].strip()
        ind = INDICATORS.get(code)
        if ind is None:
            errors.append(f"linha {line}: indicador desconhecido {code!r}")
            continue
        if ind.source != "ri_bb":
            errors.append(f"linha {line}: {code} não é um indicador de curadoria do RI")
            continue
        if r["unit"].strip() != ind.unit:
            errors.append(f"linha {line}: unidade {r['unit']!r} difere do dicionário ({ind.unit})")
        host = urlparse(r["source_url"].strip()).hostname or ""
        if host not in ALLOWED_HOSTS:
            errors.append(f"linha {line}: source_url fora dos hosts oficiais ({host or 'vazio'})")
        if not r["source_locator"].strip():
            errors.append(f"linha {line}: informe página/aba/tabela em source_locator")
        try:
            start, end = parse_period_code(r["period"])
            value = float(r["value"].replace(",", "."))
            published = date.fromisoformat(r["published_at"].strip())
        except ValueError as exc:
            errors.append(f"linha {line}: {exc}")
            continue
        if published < end:
            errors.append(f"linha {line}: published_at anterior ao fim do período")
        if ind.unit == "pct" and not (-500 <= value <= 500):
            errors.append(f"linha {line}: percentual fora de [-500, 500] — use 21.6 para 21,6%")
        out.append(ManualObservation(code, start, end, value, ind.unit, r["source_url"].strip(),
                                     r["source_locator"].strip(), published, r["collected_by"].strip()))
    if errors:
        raise ManualDataError("Arquivo rejeitado:\n  " + "\n  ".join(errors))
    return out
