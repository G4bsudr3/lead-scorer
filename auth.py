import streamlit as st
from supabase import create_client


def init_supabase():
    """Initialize Supabase client with anon key (respects RLS)."""
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    if not url or not key:
        st.error("SUPABASE_URL e SUPABASE_KEY não configurados.")
        st.stop()
    return create_client(url, key)


def init_supabase_admin():
    """Initialize Supabase client with service role key (bypasses RLS)."""
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        st.error("SUPABASE_SERVICE_KEY não configurado.")
        st.stop()
    return create_client(url, key)


def get_user_profile(supabase_admin, user_id: str) -> dict | None:
    """Fetch user profile from users table."""
    result = supabase_admin.table("users").select("*").eq("id", user_id).execute()
    if result.data:
        return result.data[0]
    return None


def login_page(supabase):
    """Render login page with OTP email flow."""
    st.markdown(
        """
        <div style="text-align: center; padding: 2rem 0;">
            <h1>🎯 Lead Scorer</h1>
            <p style="color: #888;">Priorize seus deals com inteligência</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "otp_sent" not in st.session_state:
        st.session_state.otp_sent = False
    if "auth_email" not in st.session_state:
        st.session_state.auth_email = ""

    if not st.session_state.otp_sent:
        with st.form("login_form"):
            email = st.text_input("Email corporativo", placeholder="seu@email.com")
            submitted = st.form_submit_button("Enviar código", use_container_width=True)

            if submitted and email:
                try:
                    supabase.auth.sign_in_with_otp({"email": email})
                    st.session_state.otp_sent = True
                    st.session_state.auth_email = email
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao enviar código: {e}")
    else:
        st.info(f"Código enviado para **{st.session_state.auth_email}**")

        with st.form("otp_form"):
            token = st.text_input("Código OTP", placeholder="123456")
            submitted = st.form_submit_button("Verificar", use_container_width=True)

            if submitted and token:
                try:
                    result = supabase.auth.verify_otp(
                        {"email": st.session_state.auth_email, "token": token, "type": "email"}
                    )
                    if result.user:
                        st.session_state.user = result.user
                        st.session_state.access_token = result.session.access_token
                        st.session_state.otp_sent = False
                        st.rerun()
                    else:
                        st.error("Código inválido.")
                except Exception as e:
                    st.error(f"Erro na verificação: {e}")

        if st.button("← Voltar", use_container_width=True):
            st.session_state.otp_sent = False
            st.rerun()


def require_auth():
    """
    Main auth gate. Returns (supabase, supabase_admin, user_profile) or stops.
    Call this at the top of app.py.
    """
    supabase = init_supabase()
    supabase_admin = init_supabase_admin()

    if "user" not in st.session_state:
        login_page(supabase)
        st.stop()

    user = st.session_state.user
    profile = get_user_profile(supabase_admin, user.id)

    if not profile:
        st.error("Acesso não autorizado. Seu email não está cadastrado no sistema.")
        st.caption("Solicite acesso ao administrador.")
        if st.button("Sair"):
            logout()
        st.stop()

    st.session_state.profile = profile
    return supabase, supabase_admin, profile


def logout():
    """Clear session and rerun."""
    for key in ["user", "access_token", "profile", "otp_sent", "auth_email"]:
        st.session_state.pop(key, None)
    st.rerun()
