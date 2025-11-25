import streamlit as st
import requests
import uuid
import json
import os

# --- CONFIGURATION ---
# Try to get the URL from Streamlit Secrets, otherwise default to your specific Cloud Run URL
DEFAULT_API_URL = "https://scipaper-analyzer-550651297425.us-central1.run.app"

if "api_url" in st.secrets:
    API_URL = st.secrets["api_url"]
else:
    API_URL = DEFAULT_API_URL

st.set_page_config(page_title="SciPaper Chat Demo", layout="wide")

# --- STATE MANAGEMENT ---
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "current_paper_id" not in st.session_state:
    st.session_state.current_paper_id = None

if "current_summary" not in st.session_state:
    st.session_state.current_summary = None

# --- SIDEBAR ---
with st.sidebar:
    st.header("System Configuration")
    # Allow overriding the URL in the UI for debugging
    api_base_url = st.text_input("Backend API URL", value=API_URL)

    st.divider()
    st.header("User Role")
    user_role = st.radio(
        "Select Role for Demo:",
        ["Student / Researcher", "System Admin"],
        index=0
    )

    if user_role == "System Admin":
        if st.button("Reset Session"):
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.messages = []
            st.session_state.current_paper_id = None
            st.session_state.current_summary = None
            st.rerun()

# --- MAIN APP: STUDENT ROLE ---
if user_role == "Student / Researcher":
    st.title("📚 Scientific Paper Analyzer")
    st.caption(f"Session ID: {st.session_state.session_id}")

    with st.expander("📄 Upload Paper", expanded=(st.session_state.current_paper_id is None)):
        uploaded_file = st.file_uploader("Upload a PDF scientific paper", type=["pdf"])

        if uploaded_file and st.button("Analyze Paper"):
            with st.spinner("Ingesting..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
                    response = requests.post(f"{api_base_url}/upload", files=files)

                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.current_paper_id = data["paper_id"]
                        st.session_state.current_summary = data["summary"]
                        st.success(f"Paper ingested! ID: {data['paper_id']}")
                    else:
                        st.error(f"Error {response.status_code}: {response.text}")
                except Exception as e:
                    st.error(f"Connection Error: {e}")

    if st.session_state.current_summary:
        st.subheader("📝 Running Summary")
        st.info(st.session_state.current_summary)

    st.divider()
    st.subheader("💬 Q&A with Document")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask a question about the paper..."):
        if not st.session_state.current_paper_id:
            st.error("Please upload a paper first!")
        else:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                message_placeholder.markdown("Thinking...")

                try:
                    payload = {
                        "paper_id": st.session_state.current_paper_id,
                        "session_id": st.session_state.session_id,
                        "question": prompt,
                        "top_k": 5
                    }
                    headers = {"Content-Type": "application/json"}
                    response = requests.post(
                        f"{api_base_url}/query", 
                        data=json.dumps(payload),
                        headers=headers
                    )

                    if response.status_code == 200:
                        data = response.json()
                        answer = data["response"]
                        message_placeholder.markdown(answer)
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                    else:
                        message_placeholder.error(f"Error {response.status_code}")
                except Exception as e:
                    message_placeholder.error(f"Connection Error: {e}")

# --- MAIN APP: ADMIN ROLE ---
elif user_role == "System Admin":
    st.title("🛡️ Admin Dashboard")
    col1, col2, col3 = st.columns(3)

    try:
        health_resp = requests.get(f"{api_base_url}/health", timeout=2)
        health_status = "Online" if health_resp.status_code == 200 else "Error"
    except:
        health_status = "Offline"

    col1.metric("System Status", health_status)
    col2.metric("Active Session", st.session_state.session_id[:8])
    col3.metric("Backend", "Cloud Run")

    st.json({
        "backend_url": api_base_url,
        "cached_paper_id": st.session_state.current_paper_id,
        "session_active": True
    })