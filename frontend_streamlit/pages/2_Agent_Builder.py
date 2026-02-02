import streamlit as st
import requests

st.set_page_config(page_title="Agent Builder", layout="wide")

if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.warning("Please login first.")
    st.stop()

# Sidebar Logout
if st.sidebar.button("Logout"):
    st.session_state["authenticated"] = False
    st.session_state["access_token"] = None
    st.rerun()

st.markdown("# 🛠️ Agent Builder")
st.sidebar.markdown("# Agent Builder")

with st.form("agent_form"):
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Agent Name", placeholder="e.g. SalesBot")
        voice_id = st.selectbox("Voice ID", ["aura-asteria-en", "aura-luna-en", "aura-orion-en"])
    
    with col2:
        system_prompt = st.text_area("System Prompt", placeholder="You are a helpful assistant...", height=200)
        
    submitted = st.form_submit_button("Create Agent")
    
    if submitted:
        token = st.session_state.get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            response = requests.post(
                "http://localhost:8000/api/agents/", 
                json={
                    "name": name,
                    "voice_id": voice_id,
                    "system_prompt": system_prompt
                },
                headers=headers
            )
            if response.status_code == 201:
                st.success(f"Agent '{name}' created successfully!")
                st.balloons()
            else:
                st.error(f"Error: {response.status_code} - {response.text}")
        except Exception as e:
            st.error(f"Connection Error: {e}")

