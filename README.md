# Submissao — Gabriel Sudre — Challenge 003

> **Acesse a aplicacao:** [https://caseg4.bredasudre.com](https://caseg4.bredasudre.com)
> Login com qualquer email via OTP. Documentacao tecnica: [DOCS.md](DOCS.md)

## Sobre mim

- **Nome:** Gabriel Breda Sudre
- **LinkedIn:** www.linkedin.com/in/gabriel-breda-sudre
- **Challenge escolhido:** 003 — Lead Scorer

## Executive Summary

Construi uma plataforma web de priorizacao de oportunidades de vendas para um time de 35 vendedores distribuidos em escritorios regionais. A solucao usa um scoring engine com 8 features ponderadas (sigmoid, log scale, confidence weighting) para classificar 2.089 oportunidades ativas em zonas de prioridade, integra IA (GPT-4o-mini) para explicacoes e recomendacoes acionaveis, e oferece um chat assistente com contexto completo do pipeline. A principal recomendacao é que o vendedor abra a ferramenta segunda de manha, veja o "Foco Hoje" e saiba exatamente onde investir tempo, sem depender de intuicao ou análises manuais. 
Toda a explicação do Score é fornecida diretamente no card do Deal, além de uma opção para comparar com outros Deals e ver qual deles faz mais sentido e porque. A aplicação foi desenvolvida com supabase como Backend para facilitar uma possível escalação futura e integração com uma ferramenta de CRM. Por se tratar de uma aplicação beta, todos usuários logados automáticamente assumem a rule de admin (as demais rules do sistema já estão configuradas).

---

## Solucao

1. **Analise dos dados primeiro**: antes de codar, analisei a proposta e os 4 CSVs com o Claude Code, justamente para conseguir definir uma estratégia mais clara para completar o desafio. Fiquei cerca de 50 minutos na fase de planejamento de estratégia e arquitetura e, durante essa etapa identifiquei inconsistencias (typos, 1.425 deals sem conta), distribuicoes de stages, win rates homogeneos (61-65% em todos os setores) e precos com range extremo (R$55 a R$26.768). Isso definiu as decisoes de normalizacao.

2. **Scoring iterativo (4 versoes)**: v1 comprimia scores entre 30-61. Identifiquei os problemas (sigmoid cliff, min-max dominado por outlier), corrigi com log scale e sigmoid suave (v2), validei com agente externo que identificou feedback loop e features duplicadas, e implementei correcoes finais (v3/v4). Basicamente, para definir o score criei uma V1 simples e depois de implementada, fui utilizando agentes externos (sem contexto) para avaliar a lógica. Todos os resultandos dessas análises eu passei ao agente principal e aplicamos o que fazia sentido.

3. **Arquitetura de producao**: comecei com Streamlit para válidar a estrutruta (rapido mas travado com 2.089 deals), migrei para React + FastAPI + Supabase. Decisao custou um retrabalho mas entregou uma ferramenta que um vendedor nao-tecnico consegue usar e sem gargalos. A ideia de disponibilizar ela via WEB (VPS da Hostinger + Supabase Cloud) foi justamente para abstrair a necessidade de usuário não técnicos terem que instalar dependências e ferramentas para o funcionamento correto.

4. **IA como camada de valor, nao de decisao**: o scoring e deterministico e explicavel. A IA adiciona linguagem natural, recomendacoes de proximos passos e chat, mas nao substitui a logica. O ideal seria que tivesse uma descrição dos produtos e empresa para criar um RAG vetorial para a IA auxiliar no fechamento, dando sugestões mais alinhadas ao produto, no entanto, vejo como uma possível feature futura.

### Resultados / Findings

- **2.089 oportunidades ativas** scoradas (range 38-78, media 51.6)
- **8 features de scoring** com pesos validados por agente externo independente
- **16 componentes React** com dark/light mode, comparacao side-by-side, health score do pipeline
- **13 endpoints API** autenticados com CRUD completo
- **3 roles** (admin/vendedor/manager) com visibilidade controlada via RLS
- **22 testes de validacao** (10 scoring + 12 pipeline) passando
- **Chat IA** com contexto completo: metricas, zonas, top deals, distribuicoes, criterios de score
- **Deploy**: Docker + EasyPanel na Hostinger
- **Tempo total**: 4h37min de desenvolvimento ativo

### Recomendacoes

1. Conectar a um CRM real (Salesforce, HubSpot) para dados em tempo real, visto que, o dataset estático é a principal limitação.
2. A/B test dos pesos de scoring com dados de conversão real do time.
3. Adicionar feature de velocidade do deal (Prospecting → Engaging) quando dado de criação estiver disponivel.
4. Implementar notificações automáticas para deals em risco (aging acima do limiar).

### Limitacoes

- Dataset estático com dados antigos (2016-2017). O scoring foi calibrado para esse periodo com o REFERENCE_DATE configurável para produção.
- Win rates homogeneos (61-65%) limitam diferenciação por setor/produto.Trata-se de uma limitacao do dataset, nao do modelo.
- 68% dos deals ativos sem conta definida o que resultou em uma penalização do scoring, perdendo a eficacia de account_fit
- Cache em memória, por se tratar de uma aplicação com dados estáticos. Para produção o ideal seria utilizar o Redis

---

## Process Log — Como usei IA

> **Este bloco e obrigatorio.** Sem ele, a submissao e desclassificada.

### Ferramentas usadas

| Ferramenta | Para que usou |
|------------|--------------|
| Claude Code (Opus 4) | Arquitetura, implementacao completa (backend + frontend), debugging, validacao |
| OpenAI GPT-4o-mini | Runtime na aplicacao: explicacoes de deals, recomendacoes, chat assistente |
| Agente externo (via prompt) | Validacao independente da logica de scoring — revisao critica com 8 acoes prioritarias |
| Supabase | Banco de dados PostgreSQL, autenticacao OTP, Row Level Security |
| Vite + React + Tailwind | Frontend SPA com TypeScript |
| FastAPI | Backend API REST |
| Recharts | Graficos do dashboard |

### Workflow

1. Discussão de arquitetura (45min): análisei o challenge, debati stack (Streamlit vs React, CSV vs Supabase, local vs cloud), defini scoring com 9 features iniciais, documentei em `infraestrutura_base.md`
2. Setup Supabase (40min): criei schema com FKs surrogate, importei CSVs, validei integridade dos dados.
3. Scoring engine v1-v4 (1h30): implementei, testei, identifiquei compressãi, corrigi formulas, enviei para validacao externa, implementei correções e ajustes.
4. Interface (2h): comecei com Streamlit para testes visuais (funciona mas trava muito), migrei para React + FastAPI, implementei dashboard com gráficos, pipeline com zonas, histórico e chat flutuante.
5. Refinamentos (40min): Pedi ao Claude seguir a mesma linha de DS do site do G4, implementei dark mode, CRUD de deals, comparação side-by-side, health score, guardrails de IA, traduções PT-BR, icones Lucide. Nessa etapa trabalhei apenas em melhorias.

### Onde a IA errou e como corrigi

1. **Scoring comprimido (v1)**: IA implementou min-max simples fazendo com que o GTK 500 (R$26.768) dominasse o potential_value, 95% dos deals tinham aging=0. Corrigi com log scale e sigmoid baseado em mediana dos deals ativos. Utilizei 3 agentes diferentes (diferentes modelos, inclusive) para analisar o calculo e chegar na versão final.
2. **Feature duplicada**: `product_price_tier` era copia identica de `potential_value`, ou seja, 5% do peso era desperdicado. Detectado por agente externo, removido.
3. **Import via porta errada**: IA tentou porta 5432 (transaction mode do PgBouncer) que cancelava statements. Diagnostiquei e mudei para 6543 (session mode). Tive que aplicar alguns ajustes no Pooler do Supabase manualmente para funcionar.
5. **Feedback loop no agent_performance**: vendedores com win rate baixo recebiam scores piores → focavam em menos deals → perdiam mais. Identificado pelo agente externo, corrigido reduzindo peso de 12% para 5% e simetrizando.
6. **agent_load penalizava produtividade**: logica invertida (menos deals = melhor) premiava vendedores ociosos. Corrigi para desvio da media (ambos extremos penalizados).
7. **Colunas fantasma no /api/init**: apos colapsar features, endpoint ainda referenciava colunas antigas. Corrigido na auditoria final.

### O que eu adicionei que a IA sozinha nao faria

1. **Decisao de Supabase centralizado**: a IA sugeriu CSV local. Eu identifiquei que 35 vendedores em escritorios regionais precisam de fonte unica de dados.
2. **Validacao externa do scoring**: enviei prompt estruturado para agente independente avaliar a logica. A IA que construiu o scoring nao identificaria seus proprios problemas.
3. **Migracao Streamlit → React**: decisao de UX baseada em experiencia, nao em sugestao da IA.
4. **Design alinhado ao G4**: pesquisei o site g4business.com e extraí cores (navy/gold), tipografia (Manrope), patterns visuais.
5. **Traducao contextual**: Won/Lost → Ganho/Perdido, Engaging → Em Negociacao. Decisao de UX para vendedores BR.
6. **REFERENCE_DATE configuravel**: em vez de hardcoded, parametrizavel via env var, ja que a IA nao teria pensado no cenario de producao vs avaliacao.

---

## Evidencias

- [ ] Git history (commits no repositorio)
- [x] Documento de arquitetura iterado: `infraestrutura_base.md`
- [x] Schema SQL versionado: `supabase/schema.sql`
- [x] Process log detalhado: `PROCESS_LOG.md`
- [x] Testes automatizados: `test_scoring.py` (10 checks) + `test_pipeline.py` (12 checks)
- [x] Build de producao limpo (TypeScript + Vite, zero erros)
- [x] Aplicacao funcional deployada via Docker no EasyPanel

---

## Documentação

DOCS.md
_Submissao enviada em: 31/03/2026_
