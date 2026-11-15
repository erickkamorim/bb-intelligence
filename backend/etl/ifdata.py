"""Cliente do IF.data (Banco Central, API Olinda/OData) para comparação entre bancos.

Validado em 15/11/2026 (sondas no GitHub Actions):
- IfDataValores(AnoMes, TipoInstituicao=1 [conglomerados prudenciais], Relatorio='1' [Resumo])
- Valores em reais; Índice de Basileia em fração (0,139 = 13,9%).
- "Lucro Líquido" vem ACUMULADO NO SEMESTRE: mar = 1T, jun = 1S, set = 3T, dez = 2S.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from urllib.parse import quote

BASE = "https://olinda.bcb.gov.br/olinda/servico/IFDATA/versao/v1/odata"

# Conglomerados prudenciais (cadastro IF.data de 202606)
BANKS: dict[str, str] = {
    "C0080329": "Banco do Brasil",
    "C0080099": "Itaú",
    "C0080075": "Bradesco",
    "C0080185": "Santander",
    "C0080738": "Caixa",
}
BB_CODE = "C0080329"

# Conta do relatório Resumo -> métrica interna
METRICS: dict[str, tuple[str, str]] = {
    "140220": ("ativo_total", "BRL"),
    "141873": ("carteira_credito", "BRL"),
    "140246": ("patrimonio_liquido", "BRL"),
    "141870": ("lucro_semestre_acum", "BRL"),
    "79664": ("basileia", "pct"),
}


class IfDataFormatError(ValueError):
    pass


@dataclass(frozen=True)
class PeerRow:
    cod_inst: str
    institution: str
    period_end: date
    metric: str
    value: float
    unit: str


def month_end(ano_mes: str) -> date:
    y, m = int(ano_mes[:4]), int(ano_mes[4:])
    nxt = date(y + (m == 12), m % 12 + 1, 1)
    return date.fromordinal(nxt.toordinal() - 1)


def build_url(ano_mes: str, banks: dict[str, str] = BANKS) -> str:
    flt = " or ".join(f"CodInst eq '{c}'" for c in banks)
    return (f"{BASE}/IfDataValores(AnoMes=@AnoMes,TipoInstituicao=@TipoInstituicao,Relatorio=@Relatorio)"
            f"?@AnoMes={ano_mes}&@TipoInstituicao=1&@Relatorio='1'&$format=json"
            f"&$filter={quote(flt)}&$select=CodInst,AnoMes,Conta,NomeColuna,Saldo")


def parse(payload: object, ano_mes: str, banks: dict[str, str] = BANKS) -> list[PeerRow]:
    if not isinstance(payload, dict) or "value" not in payload:
        raise IfDataFormatError(f"Resposta inesperada do IF.data: {str(payload)[:200]}")
    end = month_end(ano_mes)
    out: dict[tuple[str, str], PeerRow] = {}
    for r in payload["value"]:
        cod, conta = r.get("CodInst"), str(r.get("Conta"))
        if cod not in banks or conta not in METRICS or r.get("Saldo") is None:
            continue
        metric, unit = METRICS[conta]
        v = float(r["Saldo"])
        if metric == "basileia":
            v *= 100
        out[(cod, metric)] = PeerRow(cod, banks[cod], end, metric, v, unit)  # duplicatas: fica a última
    return list(out.values())


def quarterly_profit(semester_acc: dict[date, float]) -> dict[date, tuple[float, str]]:
    """Converte lucro acumulado no semestre em lucro do trimestre isolado.

    1T e 3T = o próprio valor; 2T = jun − mar; 4T = dez − set (exige o trimestre anterior).
    """
    out: dict[date, tuple[float, str]] = {}
    for end, v in semester_acc.items():
        if end.month in (3, 9):
            out[end] = (v, "ifdata:semestre_1o_trimestre")
        else:
            prev = month_end(f"{end.year}{end.month - 3:02d}")
            if prev in semester_acc:
                out[end] = (v - semester_acc[prev], "derived:semestre_menos_trimestre_anterior")
    return out


def fetch(ano_mes: str, session=None, timeout: float = 180.0, attempts: int = 4, sleep=None) -> list[PeerRow]:
    import time

    import requests

    s = session or requests.Session()
    sleep = sleep or time.sleep
    last: Exception | None = None
    for i in range(attempts):
        try:
            r = s.get(build_url(ano_mes), timeout=timeout, headers={"Accept": "application/json"})
            if r.status_code >= 500:
                raise IfDataFormatError(f"HTTP {r.status_code}")
            r.raise_for_status()
            return parse(r.json(), ano_mes)
        except Exception as exc:  # noqa: BLE001
            last = exc
            if i < attempts - 1:
                sleep(5 * 2 ** i)
    raise IfDataFormatError(f"IF.data indisponível para {ano_mes}: {last}")
