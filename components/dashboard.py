import streamlit as st
import pandas as pd
from ai.client import get_openai_client, explain_deal, generate_manager_summary, chat_response


DEALS_PER_PAGE = 20


def render_metrics(metrics: dict, profile_role: str):
    cols = st.columns(4)
    with cols[0]:
        st.metric("Deals Ativos", metrics["active_deals"])
    with cols[1]:
        st.metric("Win Rate", f"{metrics['win_rate']}%")
    with cols[2]:
        st.metric("Ticket Médio", f"${metrics['avg_ticket']:,.0f}")
    with cols[3]:
        st.metric("Em Risco", metrics["at_risk"], delta_color="inverse")


def _score_badge(score: float) -> str:
    if score >= 70:
        color, label = "#22C55E", "Alto"
    elif score >= 40:
        color, label = "#F59E0B", "Médio"
    else:
        color, label = "#EF4444", "Baixo"
    return (
        f"<div style='text-align:center;padding:8px;border-radius:8px;background:{color}20;'>"
        f"<span style='font-size:1.5em;font-weight:bold;color:{color};'>{score}</span>"
        f"<br><small>{label}</small></div>"
    )


def _get_explanations(deal: pd.Series) -> list[dict]:
    """Lazy-load explanations from cached stats."""
    stats = st.session_state.get("_scoring_stats")
    if not stats:
        return []

    cache_key = f"_exp_{deal['opportunity_id']}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    from scoring.engine import get_deal_explanations
    data = st.session_state.get("_app_data", {})
    products = data.get("products", pd.DataFrame())
    accounts = data.get("accounts", pd.DataFrame())
    teams = data.get("teams", pd.DataFrame())

    explanations = get_deal_explanations(deal, stats, products, accounts, teams)
    st.session_state[cache_key] = explanations
    return explanations


def render_deal_card(deal: pd.Series, ai_client=None):
    with st.container(border=True):
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.markdown(f"**{deal['account_name']}** — {deal['product_name']}")
            st.caption(f"{deal['deal_stage']} | {deal['agent_name']}")
        with col2:
            st.markdown(f"**${deal['potential_value']:,.0f}**")
            st.caption("Valor potencial")
        with col3:
            st.markdown(_score_badge(deal["score"]), unsafe_allow_html=True)

        with st.expander("Ver fatores do score"):
            explanations = _get_explanations(deal)
            for exp in explanations:
                icon = {"positive": "+", "negative": "-", "neutral": "~"}[exp["impact"]]
                exp_color = {"positive": "green", "negative": "red", "neutral": "gray"}[exp["impact"]]
                st.markdown(f":{exp_color}[**{icon}**] {exp['text']}")

            if ai_client:
                if st.button("Análise IA", key=f"ai_{deal['opportunity_id']}"):
                    with st.spinner("Gerando análise..."):
                        deal_info = f"{deal['account_name']} - {deal['product_name']} ({deal['deal_stage']})"
                        factors = "\n".join([f"- {e['text']}" for e in explanations])
                        result = explain_deal(ai_client, deal_info, deal["score"], factors)
                        st.markdown(result)


def render_deal_table(scored: pd.DataFrame):
    display_cols = ["score", "account_name", "product_name", "deal_stage",
                    "agent_name", "potential_value", "engage_date"]
    display_names = {
        "score": "Score", "account_name": "Conta", "product_name": "Produto",
        "deal_stage": "Stage", "agent_name": "Vendedor",
        "potential_value": "Valor Potencial", "engage_date": "Data Engaging",
    }
    available_cols = [c for c in display_cols if c in scored.columns]
    df = scored[available_cols].rename(columns=display_names)

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Score": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
            "Valor Potencial": st.column_config.NumberColumn(format="$%,.0f"),
        },
    )


def render_filters(scored: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.markdown("### Filtros")

    stages = sorted(scored["deal_stage"].unique().tolist())
    selected_stages = st.sidebar.multiselect("Stage", stages, default=stages)

    products = sorted(scored["product_name"].dropna().unique().tolist())
    selected_products = st.sidebar.multiselect("Produto", products, default=products)

    min_score, max_score = st.sidebar.slider("Score", 0, 100, (0, 100))

    filtered = scored[
        (scored["deal_stage"].isin(selected_stages)) &
        (scored["product_name"].isin(selected_products)) &
        (scored["score"] >= min_score) &
        (scored["score"] <= max_score)
    ]

    st.sidebar.markdown(f"**{len(filtered)}** de {len(scored)} deals")
    return filtered


def render_manager_filters(scored: pd.DataFrame, teams: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Filtros do Time")

    agents = sorted(scored["agent_name"].dropna().unique().tolist())
    selected_agents = st.sidebar.multiselect("Vendedor", agents, default=agents)

    offices = sorted(scored["regional_office"].dropna().unique().tolist())
    selected_offices = st.sidebar.multiselect("Escritório", offices, default=offices)

    return scored[
        (scored["agent_name"].isin(selected_agents)) &
        (scored["regional_office"].isin(selected_offices))
    ]


def render_deals_paginated(filtered: pd.DataFrame, ai_client=None):
    """Render deals with pagination to avoid rendering 2000+ cards."""
    total = len(filtered)
    if total == 0:
        st.info("Nenhum deal encontrado com os filtros selecionados.")
        return

    view = st.radio("Visualização", ["Tabela", "Cards"], horizontal=True, label_visibility="collapsed")

    if view == "Tabela":
        render_deal_table(filtered)
    else:
        # Pagination
        page = st.number_input("Página", min_value=1, max_value=max(1, (total - 1) // DEALS_PER_PAGE + 1), value=1, step=1)
        start = (page - 1) * DEALS_PER_PAGE
        end = min(start + DEALS_PER_PAGE, total)
        st.caption(f"Mostrando {start+1}-{end} de {total} deals")

        page_deals = filtered.iloc[start:end]

        # Top deals highlight (only on page 1)
        if page == 1 and len(page_deals) >= 5:
            st.markdown("#### Top Deals para Focar")
            for _, deal in page_deals.head(5).iterrows():
                render_deal_card(deal, ai_client)
            st.markdown("#### Demais Deals")
            for _, deal in page_deals.iloc[5:].iterrows():
                render_deal_card(deal, ai_client)
        else:
            for _, deal in page_deals.iterrows():
                render_deal_card(deal, ai_client)


def render_agent_ranking(scored: pd.DataFrame, pipeline: pd.DataFrame, teams: pd.DataFrame):
    st.markdown("### Performance do Time")
    closed = pipeline[pipeline["deal_stage"].isin(["Won", "Lost"])]
    agent_stats = []

    for _, agent in teams.iterrows():
        agent_closed = closed[closed["sales_agent_id"] == agent["id"]]
        agent_active = scored[scored["sales_agent_id"] == agent["id"]]
        won = len(agent_closed[agent_closed["deal_stage"] == "Won"])
        total = len(agent_closed)
        wr = (won / total * 100) if total > 0 else 0
        avg_score = agent_active["score"].mean() if len(agent_active) > 0 else 0

        agent_stats.append({
            "Vendedor": agent["sales_agent"],
            "Escritório": agent["regional_office"],
            "Win Rate": round(wr, 1),
            "Deals Ativos": len(agent_active),
            "Score Médio": round(float(avg_score), 1),
            "Potencial": float(agent_active["potential_value"].sum()) if len(agent_active) > 0 else 0,
        })

    df = pd.DataFrame(agent_stats).sort_values("Score Médio", ascending=False)
    st.dataframe(
        df, use_container_width=True, hide_index=True,
        column_config={
            "Win Rate": st.column_config.NumberColumn(format="%.1f%%"),
            "Score Médio": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
            "Potencial": st.column_config.NumberColumn(format="$%,.0f"),
        },
    )


def render_chat(ai_client, context: str):
    st.markdown("### Chat IA")

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Pergunte sobre seus deals..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                response = chat_response(ai_client, st.session_state.chat_messages, context)
                st.markdown(response)
                st.session_state.chat_messages.append({"role": "assistant", "content": response})
