"""Registro de fontes e dicionário de indicadores.

Regras:
- `verified_on` indica quando a URL/formato foi conferido manualmente.
- Mapeamentos de conta CVM com `confirmed=False` NÃO são carregados em produção
  até que alguém rode `python -m etl.cli cvm inspect` e confirme o código.
- Nenhum valor numérico mora neste arquivo.
"""
from __future__ import annotations

from dataclasses import dataclass, field

BB_CNPJ = "00.000.000/0001-91"
BB_CVM_REGISTRATION = "102-3"  # nos CSVs da CVM aparece como CD_CVM=1023 (conferir na 1ª carga)
BB_TICKER = "BBAS3"


@dataclass(frozen=True)
class Source:
    code: str
    name: str
    url: str
    license_notes: str
    verified_on: str | None
    notes: str = ""


SOURCES: dict[str, Source] = {
    "cvm_itr": Source(
        code="cvm_itr",
        name="CVM Dados Abertos — ITR (Informações Trimestrais)",
        url="https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/ITR/DADOS/",
        license_notes="ODbL (Open Data Commons Open Database License)",
        verified_on="2026-11-14",
        notes="ZIP anual itr_cia_aberta_AAAA.zip; CSV ';' em latin-1. Dicionário em /ITR/META/.",
    ),
    "cvm_dfp": Source(
        code="cvm_dfp",
        name="CVM Dados Abertos — DFP (Demonstrações Financeiras Padronizadas)",
        url="https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/",
        license_notes="ODbL (Open Data Commons Open Database License)",
        verified_on="2026-11-14",
        notes="ZIP anual dfp_cia_aberta_AAAA.zip. Necessário para derivar o 4º trimestre.",
    ),
    "bcb_sgs": Source(
        code="bcb_sgs",
        name="Banco Central — SGS (Sistema Gerenciador de Séries Temporais)",
        url="https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json",
        license_notes="ODbL (Open Data Commons Open Database License)",
        verified_on="2026-11-14",
        notes="Séries diárias: janela máxima de 10 anos por consulta (desde 26/03/2025).",
    ),
    "bcb_ifdata": Source(
        code="bcb_ifdata",
        name="Banco Central — IF.data (API Olinda/OData)",
        url="https://olinda.bcb.gov.br/olinda/servico/IFDATA/versao/v1/odata/",
        license_notes="ODbL (Open Data Commons Open Database License)",
        verified_on="2026-11-14",
        notes="Recursos IfDataCadastro e IfDataValores. Parâmetros ainda NÃO validados — Etapa 1b.",
    ),
    "ri_bb": Source(
        code="ri_bb",
        name="Banco do Brasil — Relações com Investidores",
        url="https://ri.bb.com.br/",
        license_notes="Conteúdo do emissor; verificar termos de uso antes de redistribuir arquivos.",
        verified_on=None,
        notes="Indicadores gerenciais (lucro ajustado, ROE, eficiência, carteira ampliada) via curadoria manual.",
    ),
    "b3": Source(
        code="b3",
        name="B3 — dados históricos e eventos corporativos",
        url="https://www.b3.com.br/",
        license_notes="Sujeito às regras de uso e redistribuição da B3 — NÃO integrar antes de checar licença.",
        verified_on=None,
    ),
}


@dataclass(frozen=True)
class CvmAccount:
    statement: str          # DRE | BPA | BPP
    cd_conta: str | None
    ds_regex: str           # proteção contra mudança de plano de contas
    confirmed: bool
    valid_from_year: int = 2020
    evidence: str = ""


@dataclass(frozen=True)
class Indicator:
    code: str
    name: str
    unit: str               # BRL | pct | pct_aa | index | BRL_per_USD
    frequency: str          # quarterly | daily | monthly
    definition: str
    scope: str              # consolidado | gerencial | macro
    source: str
    cvm: CvmAccount | None = None
    sgs_code: int | None = None
    sgs_period_type: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)


INDICATORS: dict[str, Indicator] = {
    # ---- Contábil (CVM) -------------------------------------------------
    "lucro_liquido_contabil": Indicator(
        code="lucro_liquido_contabil",
        name="Lucro líquido contábil consolidado",
        unit="BRL",
        frequency="quarterly",
        definition="Lucro/prejuízo consolidado do período conforme DRE consolidada enviada à CVM. "
                   "NÃO é o lucro líquido ajustado divulgado pelo RI.",
        scope="consolidado",
        source="cvm_itr",
        cvm=CvmAccount("DRE", "3.11", r"lucro|preju", confirmed=True,
                       evidence="cvm inspect ITR 2026 em 14/11/2026: 3.11 = 'Lucro ou Prejuízo Líquido Consolidado do Período'; soma 1T+2T = acumulado."),
    ),
    "lucro_liquido_controladores": Indicator(
        code="lucro_liquido_controladores",
        name="Lucro líquido atribuído aos controladores",
        unit="BRL",
        frequency="quarterly",
        definition="Parcela do lucro consolidado atribuída aos acionistas controladores.",
        scope="consolidado",
        source="cvm_itr",
        cvm=CvmAccount("DRE", "3.11.01", r"controlador", confirmed=True,
                       evidence="cvm inspect ITR 2025 e 2026 em 14/11/2026: 3.11.01 = 'Atribuído aos Sócios da Empresa Controladora'; 3.11.01 + 3.11.02 = 3.11."),
    ),
    "ativo_total": Indicator(
        code="ativo_total",
        name="Ativo total consolidado",
        unit="BRL",
        frequency="quarterly",
        definition="Saldo do ativo total no balanço patrimonial consolidado na data de referência.",
        scope="consolidado",
        source="cvm_itr",
        cvm=CvmAccount("BPA", "1", r"ativo total", confirmed=True,
                       evidence="cvm inspect ITR 2026 em 14/11/2026: conta 1 = 'Ativo Total'."),
    ),
    "patrimonio_liquido": Indicator(
        code="patrimonio_liquido",
        name="Patrimônio líquido consolidado",
        unit="BRL",
        frequency="quarterly",
        definition="Patrimônio líquido consolidado na data de referência.",
        scope="consolidado",
        source="cvm_itr",
        cvm=CvmAccount("BPP", "2.07", r"patrim[oô]nio l[ií]quido consolidado", confirmed=True,
                       evidence="cvm inspect ITR 2026 em 14/11/2026: conta 2.07 = 'Patrimônio Líquido Consolidado' (inclui minoritários)."),
    ),
    # ---- Gerencial (RI, curadoria manual) -------------------------------
    "lucro_liquido_ajustado": Indicator(
        code="lucro_liquido_ajustado",
        name="Lucro líquido ajustado",
        unit="BRL",
        frequency="quarterly",
        definition="Lucro gerencial divulgado pelo BB, que exclui itens extraordinários segundo critério do próprio banco. "
                   "Fonte: release/planilha de resultados do RI.",
        scope="gerencial",
        source="ri_bb",
    ),
    "roe_ajustado": Indicator(
        code="roe_ajustado", name="RSPL ajustado (ROE)", unit="pct", frequency="quarterly",
        definition="Retorno sobre PL ajustado, anualizado, conforme metodologia do release do BB.",
        scope="gerencial", source="ri_bb",
    ),
    "indice_eficiencia": Indicator(
        code="indice_eficiencia", name="Índice de eficiência", unit="pct", frequency="quarterly",
        definition="Conforme definição do release do BB (verificar se acumulado 12 meses ou trimestral).",
        scope="gerencial", source="ri_bb",
    ),
    "carteira_credito_ampliada": Indicator(
        code="carteira_credito_ampliada", name="Carteira de crédito ampliada", unit="BRL", frequency="quarterly",
        definition="Saldo da carteira de crédito ampliada conforme release do BB.",
        scope="gerencial", source="ri_bb",
    ),
    "carteira_pf": Indicator("carteira_pf", "Carteira — Pessoas Físicas", "BRL", "quarterly",
                             "Segmento da carteira ampliada, conforme release.", "gerencial", "ri_bb",
                             tags=("segmento",)),
    "carteira_pj": Indicator("carteira_pj", "Carteira — Pessoas Jurídicas", "BRL", "quarterly",
                             "Segmento da carteira ampliada, conforme release.", "gerencial", "ri_bb",
                             tags=("segmento",)),
    "carteira_agro": Indicator("carteira_agro", "Carteira — Agronegócio", "BRL", "quarterly",
                               "Segmento da carteira ampliada, conforme release.", "gerencial", "ri_bb",
                               tags=("segmento",)),
    "inad_90": Indicator("inad_90", "Inadimplência +90 dias", "pct", "quarterly",
                         "Operações vencidas há mais de 90 dias / carteira classificada, conforme release.",
                         "gerencial", "ri_bb"),
    # ---- Macro (SGS) ----------------------------------------------------
    "selic_meta": Indicator(
        code="selic_meta", name="Meta Selic (Copom)", unit="pct_aa", frequency="daily",
        definition="Meta para a taxa Selic definida pelo Copom, % a.a.",
        scope="macro", source="bcb_sgs", sgs_code=432, sgs_period_type="daily",
    ),
    "ipca_mensal": Indicator(
        code="ipca_mensal", name="IPCA — variação mensal", unit="pct", frequency="monthly",
        definition="Variação mensal do IPCA (%). O acumulado em 12 meses é calculado a partir desta série.",
        scope="macro", source="bcb_sgs", sgs_code=433, sgs_period_type="monthly",
    ),
    "dolar_ptax_venda": Indicator(
        code="dolar_ptax_venda", name="Dólar PTAX — venda", unit="BRL_per_USD", frequency="daily",
        definition="Taxa de câmbio R$/US$ PTAX, cotação de venda. Código 1 citado por fonte secundária: "
                   "confirmar metadados no portal do BCB antes de produção.",
        scope="macro", source="bcb_sgs", sgs_code=1, sgs_period_type="daily",
    ),
}
