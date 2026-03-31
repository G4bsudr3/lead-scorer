import pandas as pd
import streamlit as st


@st.cache_resource
def get_supabase_admin():
    """Cached Supabase admin client (persists across reruns)."""
    from supabase import create_client
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_SERVICE_KEY", "")
    return create_client(url, key)


@st.cache_data(ttl=600, show_spinner=False)
def _load_all_from_supabase() -> dict:
    """Load ALL data once and cache for 10 minutes."""
    sb = get_supabase_admin()

    accounts = pd.DataFrame(sb.table("accounts").select("*").execute().data)
    products = pd.DataFrame(sb.table("products").select("*").execute().data)
    teams = pd.DataFrame(sb.table("sales_teams").select("*").execute().data)

    # Pipeline with pagination
    all_data = []
    offset = 0
    while True:
        result = sb.table("sales_pipeline").select("*").range(offset, offset + 999).execute()
        if not result.data:
            break
        all_data.extend(result.data)
        if len(result.data) < 1000:
            break
        offset += 1000

    pipeline = pd.DataFrame(all_data)
    if not pipeline.empty:
        pipeline["engage_date"] = pd.to_datetime(pipeline["engage_date"])
        pipeline["close_date"] = pd.to_datetime(pipeline["close_date"])

    return {
        "accounts": accounts,
        "products": products,
        "teams": teams,
        "pipeline": pipeline,
    }


def load_all_data(supabase_admin=None) -> dict:
    """Load all tables. Uses aggressive caching."""
    return _load_all_from_supabase()


def get_agent_pipeline(pipeline: pd.DataFrame, sales_team_id: int) -> pd.DataFrame:
    return pipeline[pipeline["sales_agent_id"] == sales_team_id].copy()


def get_manager_pipeline(pipeline: pd.DataFrame, teams: pd.DataFrame, manager_name: str) -> pd.DataFrame:
    team_ids = teams[teams["manager"] == manager_name]["id"].tolist()
    return pipeline[pipeline["sales_agent_id"].isin(team_ids)].copy()


def get_active_deals(pipeline: pd.DataFrame) -> pd.DataFrame:
    return pipeline[pipeline["deal_stage"].isin(["Engaging", "Prospecting"])].copy()


def get_historical_deals(pipeline: pd.DataFrame) -> pd.DataFrame:
    return pipeline[pipeline["deal_stage"].isin(["Won", "Lost"])].copy()
