# BB Intelligence

> **Projeto independente, não oficial e não afiliado ao Banco do Brasil. Informações para fins analíticos, não recomendação de investimento.**

Plataforma de inteligência financeira sobre o Banco do Brasil construída só com fontes públicas auditáveis. Esta versão entrega a **Etapa 1 — Dados**: coleta, validação e armazenamento. API e interface vêm nas Etapas 2 e 3 (ver `docs/PLANO.md`).

## Requisitos

- Python 3.11+ · Docker (para o PostgreSQL 16) · acesso à internet

## Rodando localmente

```bash
cp .env.example .env
docker compose up -d db

cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
export $(grep -v '^#' ../.env | xargs)                   # Windows: defina DATABASE_URL manualmente

pytest -q                       # testes unitários + carga em SQLite
alembic upgrade head            # cria as tabelas no PostgreSQL
python -m etl seed              # cadastra fontes e dicionário de indicadores
```

## Como testar a Etapa 1 (com dados reais)

1. **Conferir o plano de contas do BB** (obrigatório antes da 1ª carga):
   ```bash
   python -m etl cvm inspect --doc ITR --year 2026 --statement DRE
   python -m etl cvm inspect --doc ITR --year 2026 --statement BPA --level 1
   python -m etl cvm inspect --doc ITR --year 2026 --statement BPP --level 2
   ```
   Confira se `3.11` é o lucro consolidado, ache os códigos de ativo total e patrimônio líquido e atualize `etl/registry.py` (`cd_conta` e `confirmed=True`).
2. **Carregar dois anos de ITR**:
   ```bash
   python -m etl cvm load --doc ITR --year 2025
   python -m etl cvm load --doc ITR --year 2026
   ```
   A carga é abortada se a soma dos trimestres não bater com o acumulado do ano, se houver duplicidade ou se a descrição da conta mudar.
3. **Séries macro**:
   ```bash
   python -m etl sgs load --indicator selic_meta --start 2016-01-01
   ```
4. **Indicadores gerenciais do RI**: copie `data/manual/ri_bb_template.csv` para `ri_bb.csv`, preencha a partir do release (com URL e página) e rode `python -m etl ri load --file ../data/manual/ri_bb.csv`.
5. **Conferência manual**: compare 2 trimestres do lucro contábil carregado com o release do RI e anote o resultado.
6. `python -m etl quality` mostra cobertura por indicador e as últimas execuções.

Rodar qualquer comando duas vezes não duplica dados; um valor diferente para o mesmo período vira uma nova revisão (`revision+1`), preservando o histórico.

## API (Etapa 2)

```bash
cd backend
uvicorn app.main:app --reload          # http://localhost:8000/docs
```

| Endpoint | O que devolve |
|---|---|
| `GET /api/v1/health` | status da API e do banco |
| `GET /api/v1/periods` | trimestres disponíveis (mais recente primeiro) |
| `GET /api/v1/indicators?period=2026Q3` | todos os indicadores no período, com variação t/t e a/a, fonte e status |
| `GET /api/v1/series/{code}?from=&to=&period_type=` | série histórica com fonte por ponto |
| `GET /api/v1/credit/segments?period=2026Q3` | carteira por segmento e participação |
| `GET /api/v1/data-quality` | cobertura, atraso (`ok`/`stale`/`missing`) e últimas execuções do ETL |
| `GET /api/v1/results/bridge?period=` | ponte do lucro ajustado entre trimestres (DRE gerencial) |
| `GET /api/v1/alerts?period=` | variações fora do comum, com polaridade por indicador |
| `GET /api/v1/notes?period=` | explicações do release (paráfrases com página) |
| `GET /api/v1/peers?period=` | BB vs Itaú, Bradesco, Santander e Caixa (IF.data) |
| `GET /api/v1/events` | agenda oficial — vazia com `status: not_collected` até ser integrada |

Toda resposta tem `data` e `meta` (versão, horário e aviso de projeto não oficial). Erros vêm como `{"error": {"code", "message"}}`. Indicador sem dado aparece com `status: "missing"`, nunca como zero. O workflow **api-smoke** sobe a API no GitHub lendo o Neon e chama todos os endpoints.

## Variáveis de ambiente

| Variável | Padrão | Uso |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://bb:bb@localhost:5432/bb_intelligence` | conexão |
| `RAW_DATA_DIR` | `./data/raw` | arquivos brutos e `manifest.jsonl` |
| `HTTP_TIMEOUT` | `120` | segundos |
| `HTTP_USER_AGENT` | `BB-Intelligence-ETL/0.1` | identifique-se para os portais |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | domínios do frontend liberados no CORS (separados por vírgula) |

## Regras do projeto

- Nenhum valor numérico no código; mock só em testes, marcado como fictício.
- Lucro contábil (CVM) e lucro ajustado (RI) são indicadores diferentes.
- Trimestre isolado, acumulado no ano e saldo são guardados com `period_type` explícito.
- Dados da B3 só depois de verificar a licença de redistribuição.

## Deploy (Etapa 4)

Frontend na Vercel; API e PostgreSQL em serviço compatível; `DATABASE_URL` como secret; CORS restrito ao domínio do frontend; `.github/workflows/etl.yml` habilitado com agendamento.
