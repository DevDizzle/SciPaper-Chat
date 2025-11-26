import streamlit as st
import requests
import uuid
import json
import pandas as pd
from datetime import datetime

# --- CONFIGURATION ---
# Try to get the URL from Streamlit Secrets, otherwise default to your specific Cloud Run URL
DEFAULT_API_URL = "https://scipaper-analyzer-550651297425.us-central1.run.app"

if "api_url" in st.secrets:
    API_URL = st.secrets["api_url"]
else:
    API_URL = DEFAULT_API_URL

st.set_page_config(page_title="SciPaper Chat", layout="wide")

# --- STATE MANAGEMENT ---
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "user" not in st.session_state:
    st.session_state.user = None # Tracks logged in user
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_paper_id" not in st.session_state:
    st.session_state.current_paper_id = None
if "current_summary" not in st.session_state:
    st.session_state.current_summary = None

# --- AUTH / LOGIN SCREEN ---
def login_screen():
    st.title("🔐 System Login")
    
    tab1, tab2 = st.tabs(["Login", "Register New User"])
    
    with tab1:
        username_login = st.text_input("Username")
        # In a real app, you'd check passwords. For demo, we just simulate login.
        if st.button("Enter System"):
            if username_login == "admin":
                 st.session_state.user = {"username": "admin", "role": "admin"}
                 st.rerun()
            elif username_login:
                 st.session_state.user = {"username": username_login, "role": "student"}
                 st.rerun()
                 
    with tab2:
        st.caption("Demonstrates the 'Create New User' use case.")
        new_username = st.text_input("New Username")
        new_role = st.selectbox("Role", ["student", "researcher", "admin"])
        
        if st.button("Create Account"):
            try:
                payload = {"username": new_username, "role": new_role}
                resp = requests.post(f"{API_URL}/users", json=payload)
                if resp.status_code == 200:
                    st.success(f"User '{new_username}' created! Please log in.")
                else:
                    st.error("User already exists or connection failed.")
            except Exception as e:
                st.error(f"Error: {e}")

# --- STUDENT UI ---
def student_view():
    st.sidebar.title(f"👤 {st.session_state.user['username']}")
    st.sidebar.caption("Role: Student / Researcher")
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()

    st.title("📄 Scientific Paper Analyzer")
    
    # 1. Upload Section
    with st.expander("📤 Upload Paper", expanded=(st.session_state.current_paper_id is None)):
        uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])
        if uploaded_file and st.button("Analyze Paper"):
            with st.spinner("Ingesting & Vectorizing..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
                    # Pass paper_id in query if you want specific IDs, or let backend generate
                    response = requests.post(f"{API_URL}/upload", files=files)
                    
                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.current_paper_id = data["paper_id"]
                        st.session_state.current_summary = data["summary"]
                        st.success("Analysis Complete")
                    else:
                        st.error(f"Error: {response.text}")
                except Exception as e:
                    st.error(f"Connection Error: {e}")

    # 2. Summary Section
    if st.session_state.current_summary:
        st.info(f"**Summary:** {st.session_state.current_summary}")

    # 3. Q&A Section
    st.divider()
    st.subheader("💬 Q&A")
    
    # Display History
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Input
    if prompt := st.chat_input("Ask a question about the paper..."):
        if not st.session_state.current_paper_id:
            st.error("Please upload a paper first.")
            return

        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("Thinking...")
            try:
                payload = {
                    "paper_id": st.session_state.current_paper_id,
                    "session_id": st.session_state.session_id,
                    "question": prompt
                }
                resp = requests.post(f"{API_URL}/query", json=payload)
                if resp.status_code == 200:
                    answer = resp.json()["response"]
                    placeholder.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                else:
                    placeholder.error("Failed to get response.")
            except Exception as e:
                placeholder.error(f"Error: {e}")

# --- ADMIN UI ---
def admin_view():
    st.sidebar.title("🛡️ Admin Portal")
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()

    st.title("System Dashboard")
    
    # 1. System Health
    try:
        health = requests.get(f"{API_URL}/health").json()
        status_color = "green"
    except:
        status_color = "red"
        
    st.markdown(f"**System Status:** :{status_color}[Online]" if status_color == "green" else "**System Status:** :red[Offline]")

    # 2. User Statistics (The Requirement: "User list... must automatically get updated")
    st.subheader("👥 User Registry")
    
    if st.button("Refresh Data"):
        st.rerun()

    try:
        resp = requests.get(f"{API_URL}/users")
        if resp.status_code == 200:
            data = resp.json()
            users = data.get("users", [])
            count = data.get("count", 0)
            
            col1, col2 = st.columns(2)
            col1.metric("Total Registered Users", count)
            col2.metric("Active Session Nodes", "Cloud Run (Autoscaled)")
            
            if users:
                df = pd.DataFrame(users)
                # Convert timestamp if it exists
                if "joined_at" in df.columns:
                    df["joined_at"] = pd.to_datetime(df["joined_at"])
                st.dataframe(df, use_container_width=True)
            else:
                st.warning("No users found in registry.")
        else:
            st.error("Failed to fetch user list.")
    except Exception as e:
        st.error(f"Connection refused: {e}")

# --- MAIN CONTROLLER ---
if st.session_state.user is None:
    login_screen()
else:
    if st.session_state.user["role"] == "admin":
        admin_view()
    else:
        student_view()
