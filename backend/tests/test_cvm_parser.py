import dataclasses
from datetime import date

import pytest

from etl import cvm
from etl.registry import INDICATORS
from tests.conftest import make_zip


def test_url_pattern():
    assert cvm.zip_url("itr", 2026) == \
        "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/ITR/DADOS/itr_cia_aberta_2026.zip"
    with pytest.raises(ValueError):
        cvm.zip_url("FRE", 2026)


def test_read_filters_company(itr_zip):
    df = cvm.read_statement(itr_zip, "DRE")
    assert set(df["CNPJ_CIA"]) == {"00.000.000/0001-91"}


def test_normalize_scale_version_and_order(itr_zip):
    df = cvm.normalize(cvm.read_statement(itr_zip, "DRE"))
    # PENÚLTIMO removido; só VERSAO 2 sobrevive em 2026-03-31
    q1 = df[df["DT_REFER"] == date(2026, 3, 31)]
    assert set(q1["VERSAO"]) == {2}
    assert len(q1) == 1
    # escala MIL aplicada
    assert q1.iloc[0]["value"] == 1_100_000 * 1_000


def test_extract_quarter_and_ytd(itr_zip):
    df = cvm.normalize(cvm.read_statement(itr_zip, "DRE"))
    obs = cvm.extract(df, INDICATORS["lucro_liquido_contabil"])
    kinds = {(o.period_end, o.period_type): o.value for o in obs}
    assert kinds[(date(2026, 6, 30), "quarter")] == 1_200_000_000
    assert kinds[(date(2026, 6, 30), "ytd")] == 2_300_000_000
    assert [o.period_end for o in cvm.quarter_isolated(obs)] == [date(2026, 3, 31), date(2026, 6, 30)]


def test_unconfirmed_mapping_is_blocked(itr_zip):
    df = cvm.normalize(cvm.read_statement(itr_zip, "DRE"))
    base = INDICATORS["lucro_liquido_controladores"]
    ind = dataclasses.replace(base, cvm=dataclasses.replace(base.cvm, confirmed=False))
    with pytest.raises(ValueError, match="não confirmado"):
        cvm.extract(df, ind)
    assert len(cvm.extract(df, ind, allow_unconfirmed=True)) == 1


def test_description_mismatch_raises(itr_zip):
    df = cvm.normalize(cvm.read_statement(itr_zip, "DRE"))
    ind = INDICATORS["lucro_liquido_contabil"]
    wrong = dataclasses.replace(ind, cvm=dataclasses.replace(ind.cvm, ds_regex=r"receita"))
    with pytest.raises(cvm.AccountMismatchError):
        cvm.extract(df, wrong)


def test_balance_sheet_is_instant(itr_zip):
    df = cvm.normalize(cvm.read_statement(itr_zip, "BPA"))
    obs = cvm.extract(df, INDICATORS["ativo_total"], allow_unconfirmed=True)
    assert obs[0].period_type == "instant" and obs[0].period_start is None


def test_missing_member_is_explicit_error(tmp_path):
    p = tmp_path / "x.zip"
    p.write_bytes(make_zip({"outro.csv": []}))
    with pytest.raises(cvm.CvmFormatError):
        cvm.read_statement(p, "DRE")


def test_missing_columns_is_explicit_error(tmp_path):
    import zipfile
    p = tmp_path / "x.zip"
    with zipfile.ZipFile(p, "w") as zf:
        zf.writestr("itr_cia_aberta_DRE_con_2026.csv", "CNPJ_CIA;VL_CONTA\n")
    with pytest.raises(cvm.CvmFormatError, match="Colunas ausentes"):
        cvm.read_statement(p, "DRE")


def test_earnings_per_share_is_not_scaled(itr_zip):
    df = cvm.normalize(cvm.read_statement(itr_zip, "DRE"))
    assert df[df["CD_CONTA"] == "3.99"].iloc[0]["value"] == 0.42
