"""Parser dos ZIPs de ITR/DFP da CVM.

Formato esperado (conferir com o dicionário em /DOC/ITR/META/ na 1ª carga):
- ZIP anual com um CSV de índice (itr_cia_aberta_AAAA.csv) e um CSV por
  demonstração e consolidação: itr_cia_aberta_DRE_con_AAAA.csv, ..._BPA_con_..., etc.
- Separador ';', codificação latin-1.
- Colunas usadas: CNPJ_CIA, CD_CVM, DT_REFER, VERSAO, ORDEM_EXERC, MOEDA,
  ESCALA_MOEDA, DT_INI_EXERC, DT_FIM_EXERC, CD_CONTA, DS_CONTA, VL_CONTA.
"""
from __future__ import annotations

import re
import unicodedata
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from .periods import PeriodType, classify_window
from .registry import BB_CNPJ, CvmAccount, Indicator

REQUIRED_COLUMNS = {
    "CNPJ_CIA", "DT_REFER", "VERSAO", "ORDEM_EXERC", "ESCALA_MOEDA",
    "DT_FIM_EXERC", "CD_CONTA", "DS_CONTA", "VL_CONTA",
}
SCALE = {"UNIDADE": 1, "MIL": 1_000, "MILHAO": 1_000_000}


class CvmFormatError(ValueError):
    """O arquivo não tem o formato esperado — nunca seguir adiante em silêncio."""


class AccountMismatchError(ValueError):
    """O código de conta existe, mas a descrição não bate com o esperado."""


def zip_url(doc: str, year: int) -> str:
    doc = doc.upper()
    if doc not in {"ITR", "DFP"}:
        raise ValueError("doc deve ser ITR ou DFP")
    return f"https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/{doc}/DADOS/{doc.lower()}_cia_aberta_{year}.zip"


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def _find_member(zf: zipfile.ZipFile, statement: str, consolidated: bool) -> str:
    suffix = "con" if consolidated else "ind"
    pattern = re.compile(rf"_{statement}_{suffix}_\d{{4}}\.csv$", re.IGNORECASE)
    matches = [n for n in zf.namelist() if pattern.search(n)]
    if len(matches) != 1:
        raise CvmFormatError(
            f"Esperado 1 arquivo {statement}_{suffix} no ZIP, encontrados {len(matches)}: {zf.namelist()[:10]}"
        )
    return matches[0]


def _find_index_member(zf: zipfile.ZipFile) -> str | None:
    pattern = re.compile(r"^(itr|dfp)_cia_aberta_\d{4}\.csv$", re.IGNORECASE)
    for n in zf.namelist():
        if pattern.search(Path(n).name):
            return n
    return None


def read_statement(zip_path: str | Path, statement: str, consolidated: bool = True,
                   cnpj: str = BB_CNPJ) -> pd.DataFrame:
    """Lê uma demonstração do ZIP e devolve apenas as linhas do CNPJ informado."""
    with zipfile.ZipFile(zip_path) as zf:
        member = _find_member(zf, statement, consolidated)
        with zf.open(member) as fh:
            df = pd.read_csv(fh, sep=";", encoding="latin-1", dtype=str)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise CvmFormatError(f"Colunas ausentes em {member}: {sorted(missing)}")
    df = df[df["CNPJ_CIA"] == cnpj].copy()
    df["_member"] = member
    return df


def read_index(zip_path: str | Path, cnpj: str = BB_CNPJ) -> pd.DataFrame:
    """Índice de documentos (data de recebimento e link). Pode não existir em anos antigos."""
    with zipfile.ZipFile(zip_path) as zf:
        member = _find_index_member(zf)
        if member is None:
            return pd.DataFrame()
        with zf.open(member) as fh:
            df = pd.read_csv(fh, sep=";", encoding="latin-1", dtype=str)
    return df[df.get("CNPJ_CIA") == cnpj].copy() if "CNPJ_CIA" in df.columns else pd.DataFrame()


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Converte tipos, aplica escala, mantém só o exercício atual e a última versão."""
    if df.empty:
        return df.assign(value=pd.Series(dtype=float))
    out = df.copy()
    ordem = out["ORDEM_EXERC"].map(lambda s: _strip_accents(str(s)).upper())
    out = out[ordem == "ULTIMO"]

    escala = out["ESCALA_MOEDA"].map(lambda s: _strip_accents(str(s)).upper())
    unknown = set(escala) - set(SCALE)
    if unknown:
        raise CvmFormatError(f"ESCALA_MOEDA desconhecida: {unknown}")

    out["VERSAO"] = out["VERSAO"].astype(int)
    out["DT_REFER"] = pd.to_datetime(out["DT_REFER"]).dt.date
    out["DT_FIM_EXERC"] = pd.to_datetime(out["DT_FIM_EXERC"]).dt.date
    if "DT_INI_EXERC" in out.columns:
        ini = pd.to_datetime(out["DT_INI_EXERC"], errors="coerce")
        out["DT_INI_EXERC"] = pd.Series([None if pd.isna(x) else x.date() for x in ini],
                                        index=out.index, dtype=object)
    else:
        out["DT_INI_EXERC"] = pd.Series([None] * len(out), index=out.index, dtype=object)

    # Lucro por ação (3.99.*) vem em R$/ação e NÃO deve receber a escala MIL da demonstração
    per_share = out["CD_CONTA"].str.startswith("3.99")
    factor = escala.map(SCALE).loc[out.index].where(~per_share, 1)
    out["value"] = pd.to_numeric(out["VL_CONTA"], errors="raise") * factor

    # Reapresentações: mantém só a maior VERSAO por data de referência
    max_ver = out.groupby("DT_REFER")["VERSAO"].transform("max")
    out = out[out["VERSAO"] == max_ver]

    out["period_type"] = [
        classify_window(s if isinstance(s, date) else None, e).value
        for s, e in zip(out["DT_INI_EXERC"], out["DT_FIM_EXERC"])
    ]
    return out.reset_index(drop=True)


@dataclass
class CvmObservation:
    indicator_code: str
    period_start: date | None
    period_end: date
    period_type: str
    value: float
    version: int
    cd_conta: str
    ds_conta: str
    member: str


def extract(df_norm: pd.DataFrame, indicator: Indicator, allow_unconfirmed: bool = False) -> list[CvmObservation]:
    acc: CvmAccount | None = indicator.cvm
    if acc is None:
        raise ValueError(f"{indicator.code} não é um indicador CVM")
    if acc.cd_conta is None or (not acc.confirmed and not allow_unconfirmed):
        raise ValueError(
            f"Mapeamento de {indicator.code} não confirmado. Rode `python -m etl.cli cvm inspect` e "
            f"confirme o CD_CONTA no registry antes de carregar."
        )
    rows = df_norm[df_norm["CD_CONTA"] == acc.cd_conta]
    regex = re.compile(acc.ds_regex, re.IGNORECASE)
    obs: list[CvmObservation] = []
    for _, r in rows.iterrows():
        if not regex.search(_strip_accents(str(r["DS_CONTA"])) ) and not regex.search(str(r["DS_CONTA"])):
            raise AccountMismatchError(
                f"{indicator.code}: conta {acc.cd_conta} tem descrição {r['DS_CONTA']!r}, esperado /{acc.ds_regex}/"
            )
        obs.append(CvmObservation(
            indicator_code=indicator.code,
            period_start=r["DT_INI_EXERC"] if isinstance(r["DT_INI_EXERC"], date) else None,
            period_end=r["DT_FIM_EXERC"],
            period_type=r["period_type"],
            value=float(r["value"]),
            version=int(r["VERSAO"]),
            cd_conta=r["CD_CONTA"],
            ds_conta=r["DS_CONTA"],
            member=r["_member"],
        ))
    return obs


def list_accounts(df_norm: pd.DataFrame, max_level: int = 2) -> pd.DataFrame:
    """Lista contas do BB (até `max_level` níveis) para confirmar códigos manualmente."""
    if df_norm.empty:
        return df_norm
    lvl = df_norm["CD_CONTA"].str.count(r"\.") + 1
    cols = ["CD_CONTA", "DS_CONTA", "DT_REFER", "period_type", "value"]
    return (df_norm[lvl <= max_level][cols]
            .drop_duplicates(subset=["CD_CONTA", "DT_REFER", "period_type"])
            .sort_values(["DT_REFER", "CD_CONTA"]))


def quarter_isolated(observations: list[CvmObservation]) -> list[CvmObservation]:
    """Filtra apenas observações de trimestre isolado (o ITR traz também o YTD)."""
    return [o for o in observations if o.period_type == PeriodType.QUARTER.value]
