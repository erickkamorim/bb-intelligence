"""Fixtures. TODOS os números aqui são FICTÍCIOS e servem só para testar o parser.
Eles imitam o formato dos CSVs da CVM, não os valores do Banco do Brasil."""
from __future__ import annotations

import io
import zipfile

import pytest

BB = "00.000.000/0001-91"
OUTRA = "11.111.111/0001-11"
HEADER = ("CNPJ_CIA;DT_REFER;VERSAO;DENOM_CIA;CD_CVM;GRUPO_DFP;MOEDA;ESCALA_MOEDA;ORDEM_EXERC;"
          "DT_INI_EXERC;DT_FIM_EXERC;CD_CONTA;DS_CONTA;VL_CONTA;ST_CONTA_FIXA")


def _row(cnpj, refer, ver, ordem, ini, fim, conta, desc, valor, escala="MIL"):
    return f"{cnpj};{refer};{ver};EMPRESA FICTICIA;1023;DF Consolidado;REAL;{escala};{ordem};{ini};{fim};{conta};{desc};{valor};S"


def _dre_rows():
    r = []
    # 1T26 (FICTÍCIO): versão 1 e reapresentação versão 2 — só a v2 deve sobrar
    r.append(_row(BB, "2026-03-31", 1, "ÚLTIMO", "2026-01-01", "2026-03-31", "3.11", "Lucro ou Prejuízo Líquido Consolidado do Período", "1000000"))
    r.append(_row(BB, "2026-03-31", 2, "ÚLTIMO", "2026-01-01", "2026-03-31", "3.11", "Lucro ou Prejuízo Líquido Consolidado do Período", "1100000"))
    r.append(_row(BB, "2026-03-31", 2, "PENÚLTIMO", "2025-01-01", "2025-03-31", "3.11", "Lucro ou Prejuízo Líquido Consolidado do Período", "900000"))
    # 2T26 (FICTÍCIO): trimestre isolado + acumulado no ano
    r.append(_row(BB, "2026-06-30", 1, "ÚLTIMO", "2026-04-01", "2026-06-30", "3.11", "Lucro ou Prejuízo Líquido Consolidado do Período", "1200000"))
    r.append(_row(BB, "2026-06-30", 1, "ÚLTIMO", "2026-01-01", "2026-06-30", "3.11", "Lucro ou Prejuízo Líquido Consolidado do Período", "2300000"))
    r.append(_row(BB, "2026-06-30", 1, "ÚLTIMO", "2026-04-01", "2026-06-30", "3.11.01", "Atribuído a Sócios da Empresa Controladora", "1150000"))
    r.append(_row(BB, "2026-06-30", 1, "ÚLTIMO", "2026-04-01", "2026-06-30", "3.99", "Lucro por Ação (R$/Ação)", "0.42"))
    # Outra companhia deve ser descartada
    r.append(_row(OUTRA, "2026-06-30", 1, "ÚLTIMO", "2026-04-01", "2026-06-30", "3.11", "Lucro", "5"))
    return r


def _bpa_rows():
    return [_row(BB, "2026-06-30", 1, "ÚLTIMO", "", "2026-06-30", "1", "Ativo Total", "2500000000")]


def make_zip(members: dict[str, list[str]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, rows in members.items():
            zf.writestr(name, ("\n".join([HEADER, *rows]) + "\n").encode("latin-1"))
    return buf.getvalue()


@pytest.fixture
def itr_zip(tmp_path):
    p = tmp_path / "itr_cia_aberta_2026.zip"
    p.write_bytes(make_zip({
        "itr_cia_aberta_DRE_con_2026.csv": _dre_rows(),
        "itr_cia_aberta_BPA_con_2026.csv": _bpa_rows(),
    }))
    return p
