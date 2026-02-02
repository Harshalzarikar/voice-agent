import streamlit as st
import requests

st.set_page_config(
    page_title="Voice Agent - Home",
    page_icon="🎙️",
    layout="wide"
)

# Authentication Logic
def login(username, password):
    try:
        response = requests.post(
            "http://localhost:8000/api/token/",
            json={"username": username, "password": password}
        )
        if response.status_code == 200:
            st.session_state["authenticated"] = True
            st.session_state["access_token"] = response.json().get("access")
            st.success("Logged in successfully!")
            st.rerun()
        else:
            st.error("Invalid credentials.")
    except Exception as e:
        st.error(f"Connection error: {e}")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# Sidebar Logout
if st.session_state["authenticated"]:
    if st.sidebar.button("Logout"):
        st.session_state["authenticated"] = False
        st.session_state["access_token"] = None
        st.rerun()

# Main UI
if not st.session_state["authenticated"]:
    st.title("🎙️ AI Voice Orchestrator - Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            login(username, password)
    
    st.info("Tip: Create a superuser in Django (python manage.py createsuperuser) to login.")
else:
    st.title("🎙️ AI Voice Orchestrator")

    st.markdown("""
    ## Welcome to the Real-Time AI Voice Orchestration Platform
    
    This platform allows you to create and interact with AI voice agents.
    
    ### Quick Links
    - 👈 **Dashboard**: View system stats.
    - 👈 **Agent Builder**: Create and configure new agents.
    - 👈 **Voice Client**: Talk to your agents in real-time.
    
    ### System Architecture
    - **Orchestrator**: LangGraph (Router + Qwen/Llama)
    - **Voice Processing**: Deepgram
    - **Backend**: Django (Core) + FastAPI (Streaming)
    """)

