# Lead Scorer — Documentacao Tecnica

> **Submissao do challenge:** [README.md](README.md)

Ferramenta de priorizacao inteligente de oportunidades de vendas para times comerciais distribuidos.

O vendedor abre na segunda-feira de manha, ve seu pipeline e sabe exatamente onde focar.

## Stack

- **Frontend:** React 18 + TypeScript + Vite + Tailwind CSS
- **Backend/API:** Python + FastAPI
- **Banco de dados:** Supabase (PostgreSQL + Auth + RLS)
- **IA:** OpenAI GPT-4o-mini (explicações, recomendações, chat)
- **Scoring:** Engine proprietária com 8 features ponderadas

## Como rodar

### Pré-requisitos

- Python 3.11+
- Node.js 18+ ou Bun
- Conta Supabase (ou instância self-hosted)
- Chave API OpenAI (opcional — scoring funciona sem IA)

### 1. Backend (API)

```bash
cd lead-scorer
cp .env.example .env
# Preencha as variáveis no .env

pip install -r requirements.txt
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### 2. Frontend (React)

```bash
cd lead-scorer/web
cp .env.example .env
# Preencha VITE_SUPABASE_URL e VITE_SUPABASE_KEY

bun install  # ou npm install
bun run dev  # ou npm run dev
```

### 3. Banco de dados (Supabase)

```bash
# 1. Criar projeto no Supabase
# 2. Executar o schema:
psql $DATABASE_URL -f supabase/schema.sql

# 3. Importar CSVs via dashboard do Supabase:
#    - accounts.csv → tabela accounts
#    - products.csv → tabela products
#    - sales_teams.csv → tabela sales_teams
#    - sales_pipeline.csv → tabela sales_pipeline_staging

# 4. Executar mapeamento de FKs:
psql $DATABASE_URL -f supabase/import_pipeline.sql

# 5. Cadastrar usuários na tabela users via Supabase Dashboard
```

### 4. Docker (deploy)

```bash
docker build -t lead-scorer .
docker run -p 8501:8501 --env-file .env lead-scorer
```

### Variáveis de ambiente

| Variável | Descrição |
|----------|-----------|
| `SUPABASE_URL` | URL do projeto Supabase |
| `SUPABASE_KEY` | Anon key (respeita RLS) |
| `SUPABASE_SERVICE_KEY` | Service role key (scoring engine) |
| `OPENAI_API_KEY` | Chave da API OpenAI |
| `ALLOWED_ORIGINS` | Origens CORS (default: localhost) |
| `REFERENCE_DATE` | Data de referência para scoring. Use `auto` para produção (today). Default: `2017-12-31` (dataset) |

## Lógica de Scoring

Cada oportunidade ativa (Em Negociação ou Prospecção) recebe um score de 0 a 100. Quanto maior o score, mais vale a pena o vendedor investir tempo nessa oportunidade.

O score é a soma ponderada de 8 fatores, cada um avaliando um aspecto diferente da oportunidade. Todos os fatores são normalizados entre 0 e 1 antes de serem multiplicados pelo peso.

### Os 8 fatores e por que cada um importa

| Fator | Peso | O que avalia | Como funciona na prática |
|-------|------|-------------|--------------------------|
| **Tempo no pipeline** | 22% | Há quanto tempo a oportunidade está parada | Oportunidades recentes pontuam mais. Quanto mais tempo parada, mais o score cai — seguindo uma curva suave (não um corte abrupto). Usamos a mediana real das oportunidades ativas como referência, não um valor arbitrário. Oportunidades em Prospecção (ainda sem engajamento) recebem uma nota baixa fixa (0.30) porque são naturalmente mais frias. |
| **Valor potencial** | 18% | Quanto essa oportunidade pode gerar de receita | Baseado no preço do produto, ajustado pelo porte da conta. Uma oportunidade de R$5.000 numa empresa grande vale mais do que a mesma oportunidade numa empresa pequena (70% preço + 30% preço × porte). Usamos escala logarítmica para que o produto mais caro (R$26.768) não domine completamente o cálculo. |
| **Conversão do setor + produto** | 15% | Qual o histórico de fechamento dessa combinação | Calcula a taxa de conversão média do setor da conta e do produto, e compara com a média geral (63%). Se a combinação converte acima da média, pontua mais. Essas duas métricas foram unificadas porque individualmente variavam muito pouco (61-65%). |
| **Porte da empresa** | 12% | Tamanho da conta (receita e funcionários) | Empresas maiores tendem a ter mais orçamento e capacidade de compra. Normalizado em escala logarítmica para que grandes outliers não distorçam. Oportunidades sem conta definida recebem nota abaixo da mediana (penalização parcial por falta de informação). |
| **Cliente recorrente** | 10% | Quantas vezes essa conta já comprou antes | Contas que já fecharam negócios anteriores têm maior probabilidade de comprar novamente. Quanto mais compras anteriores, maior a nota — mas com retornos decrescentes (a diferença entre 10 e 11 compras é menor que entre 0 e 1). |
| **Carga do vendedor** | 10% | Quantas oportunidades o vendedor tem no pipeline | Vendedores com carga próxima da média do time pontuam mais. Tanto vendedores sobrecarregados (risco de falta de foco) quanto ociosos (possível baixa performance) são penalizados. A penalização é simétrica — ambos os extremos perdem nota igualmente. |
| **Histórico da conta** | 8% | Taxa de conversão dessa conta específica | Contas com bom histórico de fechamento pontuam mais. Porém, contas com poucos registros históricos ficam próximas do neutro — não confiamos em uma amostra pequena. A confiança aumenta gradualmente até a conta ter 10+ oportunidades no histórico. |
| **Performance do vendedor** | 5% | Taxa de conversão do vendedor vs média do time | Vendedores com taxa acima da média pontuam levemente mais. O peso é propositalmente baixo (5%) para evitar um ciclo vicioso: se o vendedor com taxa baixa sempre recebesse scores ruins, focaria em menos oportunidades, perderia mais, e sua taxa cairia ainda mais. |

### Decisões importantes

**Por que os fatores ficam entre 0.05 e 0.95 (nunca 0 ou 1)?**
Para que nenhum fator isolado consiga zerar o score inteiro. Um vendedor pode ter taxa baixa, mas se o deal é recente, o produto converte bem e a conta é grande, o score ainda reflete isso.

**Como tratamos as 1.425 oportunidades sem conta definida (68% dos ativos)?**
Recebem notas abaixo da mediana nos fatores de porte e recorrência. Não zeramos (seria injusto — o deal pode ser bom, só falta informação) nem damos nota neutra (seria generoso demais — a falta de informação é um risco real).

**Por que usamos a data 31/12/2017 como referência?**
O dataset contém dados de Out/2016 a Dez/2017. Todas as métricas temporais usam essa data como "hoje". Em produção com dados reais, seria substituída pela data atual (configurável via variável de ambiente).

**Como garantimos que o cálculo está correto?**
22 testes automatizados validam: soma dos pesos = 1.0, scores nunca são NaN, limites respeitados, ordenação correta, deals sem conta nunca no top 10, Prospecção penalizada vs Negociação, classificação de deals funciona, entre outros.

### Zonas de prioridade

Os vendedores veem as oportunidades organizadas em 3 zonas:

| Zona | Score | Significado | Ação esperada |
|------|-------|-------------|---------------|
| **Alta Prioridade** | 55+ | Maior probabilidade de fechamento | Contatar esta semana |
| **Atenção** | 40-54 | Potencial, mas precisa de acompanhamento | Avaliar e planejar próximo passo |
| **Baixa Prioridade** | <40 | Risco alto ou pouca informação | Reavaliar se vale investir tempo |

### Distribuição atual

| Métrica | Valor |
|---------|-------|
| Score mínimo | 38.2 |
| Score máximo | 77.9 |
| Média | 51.6 |
| Alta Prioridade (55+) | 583 oportunidades (28%) |
| Atenção (40-54) | 1.490 oportunidades (71%) |
| Baixa Prioridade (<40) | 16 oportunidades (1%) |
| Oportunidades com conta (média) | 56.9 |
| Oportunidades sem conta (média) | 49.1 |

## Funcionalidades

### Para o vendedor
- **Foco Hoje**: top 5 oportunidades com explicações automáticas
- **Zonas de prioridade**: Alta / Atenção / Baixa com valor total por zona
- **Explicação por deal**: fatores positivos, pontos de atenção e contexto
- **Análise IA**: recomendação de próximo passo por deal (GPT-4o-mini)
- **Chat IA**: perguntas livres sobre pipeline, performance e estratégia
- **Criar oportunidade**: formulário com vendedor, produto, conta e etapa
- **Classificar**: marcar deal como Ganho (com valor) ou Perdido
- **Filtros**: por etapa, produto, vendedor, escritório (colapsáveis com badge de contagem)
- **Export CSV**: download dos deals filtrados
- **Comparar oportunidades**: side-by-side de 2 deals com recomendação automática
- **Criar oportunidade**: formulário com vendedor, produto, conta, etapa
- **Classificar deal**: marcar como Ganho (com valor) ou Perdido diretamente no card
- **Dark/Light mode**: toggle na sidebar com persistência no localStorage

### Para o gestor
- Dashboard com gráficos: distribuição por prioridade, pipeline por stage, potencial por produto, evolução mensal
- **Pipeline Health Score**: nota composta (0-100) com 5 indicadores (volume, qualidade, conversão, score médio, risco)
- Ranking de performance do time
- Top contas por potencial
- Visão consolidada de todos os vendedores

### Chat IA (flutuante)
- Botão fixo no canto inferior direito
- Contexto completo do pipeline injetado (métricas, zonas, top deals, distribuições, critérios de score)
- Guardrails contra prompt injection, invenção de dados e vazamento de informações entre roles
- Output em HTML formatado (não markdown)
- Sugestões de perguntas para onboarding

### Segurança
- Auth OTP por email (Supabase Auth)
- Auto-criação de perfil no primeiro login como admin (para facilitar avaliação — em produção, seria "vendedor")
- 3 roles: admin, vendedor, manager
- RLS no banco de dados com 10 policies + 3 helper functions
- Service key apenas no backend (nunca exposta ao frontend)
- Validação de token JWT em todos os endpoints com cache de 5min
- CORS configurável via env var (não wildcard)

## Limitações

- **Dataset estático**: os dados são de 2016-2017. Não há atualização em tempo real. Em produção, conectaria a um CRM.
- **Win rates homogêneos**: setores e produtos têm taxas de conversão muito similares (61-65%). A diferenciação nesse eixo é limitada pelo dataset.
- **1.425 deals sem conta**: ~68% dos deals ativos não têm conta definida. O scoring penaliza parcialmente mas não consegue usar account_fit e repeat_customer de forma eficaz.
- **Score máximo ~77**: o teto teórico com esse dataset é ~85. Nenhum deal combina todos os fatores no máximo simultaneamente.
- **Testes**: 22 testes de validação (10 scoring + 12 pipeline) passam, mas não são testes unitários tradicionais (pytest).
- **Cache em memória**: adequado para single-worker. Multi-worker precisaria de Redis ou similar.
- **IA usa `dangerouslySetInnerHTML`**: output da OpenAI renderizado como HTML. Risco controlado (fonte confiável) mas não ideal.

## Correções aplicadas nos dados

| Correção | Arquivo | De → Para |
|----------|---------|-----------|
| Nome do produto | sales_pipeline.csv | "GTXPro" → "GTX Pro" (1.480 registros) |
| Setor | accounts.csv | "technolgy" → "technology" (12 registros) |
| Conta vazia | sales_pipeline | 1.425 deals sem conta → placeholder "(Não definida)" |

## Estrutura do projeto

```
lead-scorer/
├── api/main.py              # FastAPI (13 endpoints, auth JWT)
├── scoring/
│   ├── engine.py             # Score pipeline vetorizado (8 features)
│   └── features.py           # Features + explicações + pesos
├── ai/
│   └── prompts.py            # System prompts + guardrails (HTML output)
├── web/                      # React 18 + TypeScript + Vite + Tailwind
│   └── src/components/       # 16 componentes (dark mode, compare, health)
├── test_scoring.py           # 10 validações do scoring engine
├── test_pipeline.py          # 12 validações do pipeline (CRUD, filtros, export)
├── supabase/
│   ├── schema.sql            # 5 tabelas + RLS + constraints
│   └── import_pipeline.sql   # Mapeamento CSV → FKs
├── Dockerfile
├── requirements.txt
├── .env.example
└── PROCESS_LOG.md
```
