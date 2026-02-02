import streamlit as st

st.set_page_config(page_title="Dashboard", layout="wide")

if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.warning("Please login first.")
    st.stop()

# Sidebar Logout
if st.sidebar.button("Logout"):
    st.session_state["authenticated"] = False
    st.session_state["access_token"] = None
    st.rerun()

st.markdown("# 📊 Dashboard")
st.sidebar.markdown("# Dashboard")

col1, col2, col3 = st.columns(3)
col1.metric("Active Agents", "3")
col2.metric("Total Calls", "128")
col3.metric("Avg Latency", "450ms")

st.markdown("### Recent Activity")
st.dataframe({
    "Time": ["10:00", "10:05", "10:15"],
    "Agent": ["SalesBot", "SupportBot", "SalesBot"],
    "Duration": ["2m 30s", "45s", "5m 12s"],
    "Status": ["Completed", "Failed", "Completed"]
})

