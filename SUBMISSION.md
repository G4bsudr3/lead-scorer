# [Submission] Gabriel Sudre — Challenge 003

## Sobre mim

- **Nome:** Gabriel Sudre
- **LinkedIn:** [Perfil LinkedIn]
- **Challenge:** 003 — Lead Scorer (Vendas / RevOps)

## Resumo Executivo

Construí uma plataforma web de priorização de oportunidades de vendas para um time de 35 vendedores distribuídos em escritórios regionais. A solução usa um scoring engine com 8 features ponderadas para classificar 2.089 oportunidades ativas em zonas de prioridade (Alta/Atenção/Baixa), integra IA (GPT-4o-mini) para explicações e recomendações acionáveis por deal, e oferece um chat assistente com contexto completo do pipeline. O vendedor abre na segunda-feira de manhã, vê "Foco Hoje" com os top 5 deals e sabe exatamente onde investir tempo.

## Solução

### Abordagem

1. **Análise exploratória dos dados**: identifiquei inconsistências (typos, deals sem conta), distribuições de stages, win rates homogêneos entre setores/produtos (61-65%), e preços com range extremo (R$55 a R$26.768).

2. **Scoring engine iterativo**: 3 versões. A v1 comprimia tudo entre 30-61 (sigmoid cliff no aging, min-max dominado pelo GTK 500). A v2 melhorou com log scale e sigmoid suave. A v3 (após validação externa) colapsou features redundantes, adicionou agent_load, reduziu agent_performance para evitar feedback loop, e calibrou fallbacks para deals sem conta.

3. **Arquitetura de produção**: React + FastAPI + Supabase. Não um notebook — uma ferramenta que um vendedor não-técnico abre no navegador e usa. Auth real (OTP email), RBAC (admin/vendedor/manager), RLS no banco.

4. **IA como camada de valor**: não substituindo o scoring (que é determinístico e explicável), mas adicionando: explicação em linguagem natural, recomendação de próximo passo, e chat para perguntas ad-hoc sobre o pipeline.

### Resultados

- **2.089 oportunidades ativas** scoradas em tempo real
- **Score range**: 39-77 com distribuição significativa (35% acima de 55, 1% acima de 70)
- **8 features de scoring** com pesos validados por agente externo
- **16 componentes React** com UX focada na tomada de decisão (dark/light mode, comparação side-by-side, health score)
- **13 endpoints API** todos autenticados (CRUD completo: criar, classificar, listar, filtrar)
- **3 roles** com visibilidade controlada (vendedor vê seus deals, manager vê o time, admin vê tudo)
- **22 testes de validação** (10 scoring + 12 pipeline) — todos passando
- **Auto-login como admin** para facilitar avaliação do projeto

### Recomendações

1. Conectar a um CRM real (Salesforce, HubSpot) para dados em tempo real
2. Implementar notificações para deals em risco (aging acima do limiar)
3. A/B test dos pesos de scoring com dados de conversão real
4. Adicionar feature de velocidade do deal (tempo Prospecting → Engaging) quando dado disponível

### Limitações

- Dataset estático (2016-2017) — scoring calibrado para esse período
- Win rates homogêneos limitam diferenciação por setor/produto
- 68% dos deals ativos sem conta definida — penaliza parcialmente mas reduz eficácia do account_fit
- 22 testes de validação (não pytest formal, mas cobrem scoring + pipeline + CRUD)
- Cache em memória (single worker)

## Process Log

Ver [PROCESS_LOG.md](PROCESS_LOG.md) para detalhamento completo.

### Ferramentas

| Ferramenta | Uso |
|------------|-----|
| Claude Code (Opus 4) | Arquitetura, implementação, debugging |
| OpenAI GPT-4o-mini | Explicações de deals, chat IA (runtime) |
| Agente externo | Validação independente do scoring |
| Supabase | PostgreSQL + Auth + RLS |
| React + Vite + Tailwind | Frontend |
| FastAPI | Backend API |

### Onde a IA errou

1. Scoring v1 comprimido (29-61) — normalização inadequada para dados com outliers
2. Feature duplicada (product_price_tier = potential_value)
3. Streamlit como frontend — inviável para 2.089 deals interativos
4. Import via porta errada do Supabase (transaction vs session mode)
5. Feedback loop no agent_performance (identificado por agente externo)

### O que eu adicionei

1. Decisão de banco centralizado (Supabase) por causa dos escritórios distribuídos
2. Validação externa do scoring via prompt estruturado
3. Migração Streamlit → React por decisão de UX
4. Feature agent_load (concentração de pipeline)
5. Design alinhado ao G4 (pesquisa do site)
6. CRUD de deals (criar + classificar Won/Lost)
7. Tradução contextual para vendedores BR

## Evidências

- Código fonte completo no repositório
- Documento de arquitetura: `infraestrutura_base.md`
- Schema SQL: `supabase/schema.sql`
- Process log detalhado: `PROCESS_LOG.md`
- Aplicação funcional deployável via Docker
