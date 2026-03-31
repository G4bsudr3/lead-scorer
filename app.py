import streamlit as st

st.set_page_config(
    page_title="Lead Scorer",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

from auth import require_auth, logout
from data_source import load_all_data, get_agent_pipeline, get_manager_pipeline
from scoring.engine import score_pipeline, get_pipeline_metrics
from components.dashboard import (
    render_metrics,
    render_deal_table,
    render_filters,
    render_manager_filters,
    render_deals_paginated,
    render_agent_ranking,
    render_chat,
)
from ai.client import get_openai_client


# --- Auth ---
supabase, supabase_admin, profile = require_auth()

# --- Sidebar header ---
st.sidebar.markdown(f"### {profile['email']}")
st.sidebar.caption(f"Perfil: **{profile['role'].capitalize()}**")
if st.sidebar.button("Sair", use_container_width=True):
    logout()
st.sidebar.markdown("---")

# --- Load data (cached 10min) ---
data = load_all_data()
pipeline = data["pipeline"]
accounts = data["accounts"]
products = data["products"]
teams = data["teams"]

# Store for lazy explanations
st.session_state["_app_data"] = data

# --- Filter pipeline by role ---
if profile["role"] == "vendedor":
    user_pipeline = get_agent_pipeline(pipeline, profile["sales_team_id"])
    agent_info = teams[teams["id"] == profile["sales_team_id"]]
    if not agent_info.empty:
        st.title(f"Meu Pipeline — {agent_info.iloc[0]['sales_agent']}")
    else:
        st.title("Meu Pipeline")
elif profile["role"] == "manager":
    user_pipeline = get_manager_pipeline(pipeline, teams, profile["manager_name"])
    st.title(f"Pipeline do Time — {profile['manager_name']}")
else:  # admin
    user_pipeline = pipeline
    st.title("Lead Scorer — Visão Admin")

# --- Score active deals (cached) ---
if "scored_cache" not in st.session_state or st.session_state.get("_cache_pipeline_len") != len(user_pipeline):
    with st.spinner("Calculando scores..."):
        scored = score_pipeline(user_pipeline, accounts, products, teams)
        st.session_state["scored_cache"] = scored
        st.session_state["_cache_pipeline_len"] = len(user_pipeline)
else:
    scored = st.session_state["scored_cache"]

# --- Metrics ---
metrics = get_pipeline_metrics(user_pipeline, scored)
render_metrics(metrics, profile["role"])

st.markdown("---")

# --- Filters ---
filtered = render_filters(scored)

if profile["role"] == "manager":
    filtered = render_manager_filters(filtered, teams)

# --- Tabs ---
tab_active, tab_history, tab_chat = st.tabs(["Deals Ativos", "Histórico", "Chat IA"])

ai_client = get_openai_client()

with tab_active:
    render_deals_paginated(filtered, ai_client)

    if profile["role"] == "manager":
        st.markdown("---")
        render_agent_ranking(scored, user_pipeline, teams)

        if ai_client:
            st.markdown("---")
            if st.button("Gerar Resumo Executivo do Time", use_container_width=True):
                with st.spinner("Gerando resumo com IA..."):
                    from ai.client import generate_manager_summary
                    metrics_str = "\n".join([f"- {k}: {v}" for k, v in metrics.items()])
                    top_str = "\n".join([
                        f"- {d['account_name']} ({d['product_name']}): score {d['score']}"
                        for _, d in scored.head(5).iterrows()
                    ])
                    risk_str = "\n".join([
                        f"- {d['account_name']} ({d['product_name']}): score {d['score']}"
                        for _, d in scored[scored["score"] < 40].head(5).iterrows()
                    ]) or "Nenhum deal em risco."
                    summary = generate_manager_summary(ai_client, metrics_str, top_str, risk_str)
                    st.markdown(summary)

with tab_history:
    st.markdown("#### Deals Fechados (Won / Lost)")
    history = user_pipeline[user_pipeline["deal_stage"].isin(["Won", "Lost"])].copy()

    if history.empty:
        st.info("Nenhum deal fechado encontrado.")
    else:
        product_map = products.set_index("id")["name"].to_dict()
        account_map = accounts.set_index("id")["name"].to_dict()
        agent_map = teams.set_index("id")["sales_agent"].to_dict()

        history["product_name"] = history["product_id"].map(product_map)
        history["account_name"] = history["account_id"].map(account_map)
        history["agent_name"] = history["sales_agent_id"].map(agent_map)

        col1, col2 = st.columns(2)
        with col1:
            stage_filter = st.multiselect("Stage", ["Won", "Lost"], default=["Won", "Lost"])
        with col2:
            sort_by = st.selectbox("Ordenar por", ["close_date", "close_value"], index=0)

        history = history[history["deal_stage"].isin(stage_filter)]
        history = history.sort_values(sort_by, ascending=False)

        st.dataframe(
            history[["deal_stage", "account_name", "product_name", "agent_name", "close_value", "close_date"]].rename(
                columns={
                    "deal_stage": "Stage", "account_name": "Conta", "product_name": "Produto",
                    "agent_name": "Vendedor", "close_value": "Valor", "close_date": "Data Fechamento",
                }
            ),
            use_container_width=True, hide_index=True,
            column_config={"Valor": st.column_config.NumberColumn(format="$%,.0f")},
        )

with tab_chat:
    if ai_client:
        context_parts = [
            f"Pipeline: {len(scored)} deals ativos",
            f"Win rate: {metrics['win_rate']}%, Ticket médio: ${metrics['avg_ticket']:,.0f}",
            f"Deals em risco: {metrics['at_risk']}",
            f"Potencial total: ${metrics['total_potential']:,.0f}",
        ]
        if not scored.empty:
            context_parts.append(f"Top deal: {scored.iloc[0]['account_name']} - {scored.iloc[0]['product_name']} (score {scored.iloc[0]['score']})")
        render_chat(ai_client, "\n".join(context_parts))
    else:
        st.warning("Chat IA indisponível. Configure a OPENAI_API_KEY para habilitar.")
        st.caption("O scoring e explicações por fatores funcionam sem IA.")

# --- Admin link ---
if profile["role"] == "admin":
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Admin")
    supabase_url = st.secrets.get("SUPABASE_URL", "")
    st.sidebar.markdown(f"[Abrir Supabase Dashboard]({supabase_url})")
