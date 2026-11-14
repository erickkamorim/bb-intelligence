# Plano de execução — BB Intelligence

> Projeto independente, não oficial e não afiliado ao Banco do Brasil. Informações para fins analíticos, não recomendação de investimento.

## Princípio que guia tudo

O KPI só aparece na tela se tiver **fonte, data de publicação, data de coleta e definição** no banco. Por isso a ordem é: dado → validação → API → interface. A interface nunca recebe número que não veio da API.

## Etapas

| Etapa | Entrega | Critério para avançar |
|---|---|---|
| **1 — Dados** (esta entrega) | Registro de fontes, dicionário de indicadores, ETL CVM (ITR/DFP) + SGS + curadoria manual do RI, PostgreSQL com migrations, testes | Contas CVM confirmadas com `cvm inspect`; 8 trimestres carregados; amostra conferida contra 2 releases |
| 1b — Dados complementares | Cliente IF.data (parâmetros validados), derivação do 4T via DFP, eventos do RI | Carteira por segmento e inadimplência com fonte |
| 2 — API | FastAPI com os 7 endpoints do briefing, metadados em toda resposta, erros claros | Testes de contrato + ausência de dados tratada |
| 3 — Interface | Next.js, sidebar navy/amarelo recolhível, 4 KPIs, gráfico lucro × ROE com 2 eixos, carteira por segmento, filtros reais | Lighthouse a11y ≥ 90; filtros alteram a consulta |
| 4 — Produção | Agendamento, logs, observabilidade, deploy, página de transparência | Fluxo ponta a ponta automatizado |

## De onde vem cada KPI da primeira dobra

| KPI do mockup | Fonte | Situação |
|---|---|---|
| Lucro Líquido Ajustado | RI (release) — curadoria manual | Gerencial; não existe na CVM |
| Lucro líquido contábil | CVM ITR, DRE consolidada, conta 3.11 | Automatizado |
| ROE | RI (RSPL ajustado) | Curadoria manual |
| Carteira de Crédito | RI (carteira ampliada) | Curadoria manual; IF.data na 1b |
| Índice de Eficiência | RI | Curadoria manual |
| Carteira por segmento | RI | Curadoria manual |
| Selic, IPCA, dólar | BCB SGS | Automatizado (dólar: confirmar código) |
| Ibovespa | B3 | **Bloqueado** até checar licença de redistribuição |
| Próximos eventos | Calendário do RI | Etapa 1b; nunca inventar datas |

## Árvore de arquivos

```
bb-intelligence/
├── README.md
├── .env.example
├── docker-compose.yml               # PostgreSQL 16 local
├── .github/workflows/
│   ├── ci.yml                       # testes + migrations em cada push
│   └── etl.yml                      # ETL agendado (desligado até a Etapa 4)
├── data/
│   ├── raw/                         # downloads brutos versionados + manifest.jsonl (git-ignored)
│   └── manual/ri_bb_template.csv    # curadoria do RI com URL e página obrigatórias
├── docs/
│   ├── PLANO.md                     # este arquivo
│   └── FONTES.md                    # validação de cada fonte
├── backend/
│   ├── requirements.txt / requirements-dev.txt / pytest.ini / alembic.ini
│   ├── alembic/versions/0001_initial_schema.py
│   ├── app/
│   │   ├── core/config.py
│   │   └── db/{models.py, session.py}
│   ├── etl/
│   │   ├── registry.py              # fontes + dicionário de indicadores (sem valores)
│   │   ├── periods.py               # trimestre × YTD × FY × saldo
│   │   ├── storage.py               # download bruto, SHA-256, idempotência
│   │   ├── cvm.py                   # parser ITR/DFP
│   │   ├── sgs.py                   # cliente SGS com janelas de 10 anos
│   │   ├── ri_manual.py             # validação da curadoria manual
│   │   ├── validation.py            # regras (soma trimestral, lacunas, duplicidade)
│   │   ├── load.py                  # upsert com revisões + etl_runs
│   │   └── cli.py                   # python -m etl ...
│   └── tests/                       # fixtures 100% fictícias
├── api/      (Etapa 2)  backend/app/api/v1/...
└── frontend/ (Etapa 3)  Next.js App Router + Tailwind + ECharts
```

## Observação sobre o mockup

As imagens de referência usam o logotipo oficial do BB e uma fachada com a marca. Pelo próprio briefing, a interface real vai usar identidade **textual** "BB Intelligence" e uma imagem neutra com licença verificada (ou nenhuma). Todos os números dos mockups são exemplos e não serão reaproveitados.
