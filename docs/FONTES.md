# Validação de fontes — 14/11/2026

Verificação feita por consulta aos portais oficiais. **Nenhuma chamada real foi executada a partir do ambiente de desenvolvimento** (sem rede); a primeira execução local confirma formato e conteúdo.

| Fonte | URL | Formato | Licença | Status |
|---|---|---|---|---|
| CVM ITR | `https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/ITR/DADOS/itr_cia_aberta_AAAA.zip` | ZIP anual, CSV `;` latin-1; arquivos de 2011 a 2026 listados | ODbL | ✅ URL e padrão confirmados |
| CVM DFP | `https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_AAAA.zip` | ZIP anual | ODbL | ✅ URL confirmada |
| Dicionário ITR | `https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/ITR/META/meta_itr_cia_aberta_txt.zip` | TXT | ODbL | ⚠️ Ler na 1ª carga e conferir colunas |
| BCB SGS | `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json&dataInicial=dd/MM/aaaa&dataFinal=dd/MM/aaaa` | JSON/CSV | ODbL | ✅ Limite: janelas de até 10 anos em séries diárias |
| BCB IF.data | `https://olinda.bcb.gov.br/olinda/servico/IFDATA/versao/v1/odata/` | OData (JSON/CSV) | ODbL | ⚠️ Recursos `IfDataCadastro` e `IfDataValores` existem; parâmetros ainda não validados |
| RI BB | `https://ri.bb.com.br/` (PDFs servidos por `api.mziq.com`) | PDF/XLSX | Termos do emissor | ⚠️ Sem API; curadoria manual com URL + página |
| B3 | `https://www.b3.com.br/` | — | Restrita | ⛔ Não integrar antes de checar regras de redistribuição |

## Identificação do Banco do Brasil

- CNPJ: `00.000.000/0001-91` (filtro principal nos CSVs da CVM)
- Registro CVM: `102-3` → nos CSVs aparece como `CD_CVM`; conferir o formato na 1ª carga
- Ticker: BBAS3 · ISIN BRBBASACNOR3

## Contas CVM (DRE consolidada)

- `3.11` — lucro/prejuízo consolidado do período: usado para o CNPJ do BB a partir de 2020 (antes de 2020 era `3.09`). **Confirmado** por referência externa e protegido por regex na descrição.
- `3.11.01`, ativo total (`1`), patrimônio líquido: **não confirmados** — o ETL se recusa a carregar até rodar `cvm inspect` e atualizar `registry.py`.

## Séries SGS

| Indicador | Código | Status |
|---|---|---|
| Meta Selic | 432 | ✅ confirmado no portal do BCB (% a.a., diária) |
| IPCA mensal | 433 | ⚠️ citado por fonte secundária; conferir metadados |
| Dólar PTAX venda | 1 | ⚠️ citado por fonte secundária; conferir metadados |

## Lucro contábil × lucro ajustado

O **lucro ajustado** do mockup é um número gerencial do BB e não está na CVM. A plataforma guarda os dois com escopos diferentes (`consolidado` × `gerencial`) e a interface vai rotulá-los separadamente.
