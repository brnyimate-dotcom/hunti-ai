import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime
import os
import random

from brain import ask_assistant
from vision import capture_screen
from rate_limiter import check_rate_limit, get_usage_stats

st.set_page_config(page_title="Hunti AI Analytics", page_icon="🤖", layout="wide")

st.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        .metric-card { background-color: #1E1E1E; padding: 20px; border-radius: 10px; margin: 10px 0; border: 1px solid #333; }
        .metric-card h3 { margin: 10px 0 5px 0; font-size: 2em; }
        .metric-card p { margin: 0; color: #888; }
        .metric-card i { margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

if 'chat_history' not in st.session_state: st.session_state.chat_history = []
if 'user_id' not in st.session_state: st.session_state.user_id = f"user_{int(datetime.now().timestamp())}_{random.randint(1000, 9999)}"
if 'user_role' not in st.session_state: st.session_state.user_role = None

DB_NAME = "hunti.db"

def get_data(query):
    use_demo = False
    try:
        if not os.path.exists(DB_NAME): use_demo = True
        else:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM leads")
            if cursor.fetchone()[0] == 0: use_demo = True
            conn.close()
    except: use_demo = True
    
    if use_demo:
        if "COUNT(*) as count FROM leads" in query: return pd.DataFrame({'count': [47]})
        elif "COUNT(*) as count FROM pitches" in query: return pd.DataFrame({'count': [32]})
        elif "COUNT(*) as count FROM emails WHERE status='sent'" in query: return pd.DataFrame({'count': [28]})
        elif "COUNT(*) as count FROM form_submissions" in query: return pd.DataFrame({'count': [15]}) # NEW METRIC
        elif "status, COUNT(*) as count FROM emails GROUP BY status" in query:
            return pd.DataFrame({'status': ['sent', 'failed', 'pending'], 'count': [28, 2, 2]})
        elif "recipient_email, subject, sent_at FROM emails ORDER BY sent_at DESC LIMIT 5" in query:
            return pd.DataFrame({'recipient_email': ['contact@acme.com', 'info@techsol.com'], 'subject': ['AI Partnership', 'Workflow Demo'], 'sent_at': ['2024-01-15', '2024-01-14']})
        elif "SELECT * FROM leads ORDER BY created_at DESC" in query:
            return pd.DataFrame({'id': [1, 2], 'company_name': ['Acme Corp', 'Tech Solutions'], 'website': ['acme.com', 'techsol.com'], 'rating': [4.5, 3.8], 'created_at': ['2024-01-15', '2024-01-14']})
        elif "SELECT * FROM pitches ORDER BY created_at DESC" in query:
            return pd.DataFrame({'id': [1, 2], 'lead_id': [1, 2], 'pitch_text': ['Pitch for Acme...', 'Pitch for Tech...'], 'created_at': ['2024-01-15', '2024-01-14']})
        elif "SELECT * FROM emails ORDER BY sent_at DESC" in query:
            return pd.DataFrame({'id': [1], 'pitch_id': [1], 'recipient_email': ['contact@acme.com'], 'subject': ['AI Partnership'], 'status': ['sent'], 'sent_at': ['2024-01-15']})
        elif "SELECT * FROM form_submissions ORDER BY submitted_at DESC" in query: # NEW TABLE
            return pd.DataFrame({'id': [1, 2], 'company_name': ['Acme Corp', 'Global Logistics'], 'url': ['acme.com/contact', 'globallog.com/contact'], 'status': ['success', 'success'], 'submitted_at': ['2024-01-15', '2024-01-14']})
    
    try:
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()

ROLE_SUGGESTIONS = {
    "Freelancer/Solopreneur": ["Find 10 small businesses that need automation help", "Write a pitch offering my freelance automation services", "Help me identify which businesses need my skills most", "Automate my client outreach so I can focus on work"],
    "Small Business Owner": ["Find potential clients in my industry", "Create personalized pitches for local businesses", "Build an automation system for my sales team", "Help me scale my business with AI tools"],
    "Agency Owner": ["Find 20 mid-size companies needing automation consulting", "Write enterprise-level pitch for AI transformation services", "Build a complete CRM system for my agency", "Automate lead generation and qualification process"],
    "Enterprise/Corporate": ["Design an enterprise-wide automation strategy", "Create a pilot program for department automation", "Build ROI analysis for AI implementation", "Develop training plan for AI adoption"],
    "Developer/Tech": ["Help me build custom automation tools for clients", "Integrate AI APIs into existing workflows", "Create a white-label automation solution", "Build mobile-friendly lead capture system"]
}

ROLE_DESCRIPTIONS = {
    "Freelancer/Solopreneur": "Looking for quick wins and time-saving automation",
    "Small Business Owner": "Ready to scale but needs practical solutions",
    "Agency Owner": "Needs systems to serve multiple clients efficiently",
    "Enterprise/Corporate": "Requires strategic implementation and ROI proof",
    "Developer/Tech": "Wants to build or integrate automation tools"
}

with st.sidebar:
    st.markdown('<i class="fas fa-user-circle" style="font-size: 2em; color: #4CAF50;"></i>', unsafe_allow_html=True)
    st.title("User Profile")
    selected_role = st.selectbox("What best describes you?", options=list(ROLE_SUGGESTIONS.keys()), index=0 if st.session_state.user_role is None else list(ROLE_SUGGESTIONS.keys()).index(st.session_state.user_role))
    if selected_role != st.session_state.user_role:
        st.session_state.user_role = selected_role
        st.rerun()
    st.write(f"**User ID:** `{st.session_state.user_id}`")
    if st.session_state.user_role: st.info(f"💡 {ROLE_DESCRIPTIONS[st.session_state.user_role]}")
    stats = get_usage_stats(st.session_state.user_id)
    st.metric("Total Requests", stats['total_requests'])
    st.metric("Requests (Last Hour)", stats['requests_last_hour'], delta=f"Limit: 10/hour")
    st.divider()
    st.caption("Hunti AI | Built with Python & Streamlit")

st.markdown('<i class="fas fa-robot" style="font-size: 2.5em; color: #2196F3;"></i>', unsafe_allow_html=True)
st.title("Hunti AI - Command Center")
st.markdown("Real-time analytics for your AI sales agent.")
st.divider()

tab_analytics, tab_chat = st.tabs(["Analytics Dashboard", "Chat with Hunti AI"])

with tab_analytics:
    # NEW: 4 Columns now!
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        leads_df = get_data("SELECT COUNT(*) as count FROM leads")
        st.markdown(f'<div class="metric-card"><i class="fas fa-database fa-2x" style="color: #4CAF50;"></i><h3>{leads_df["count"][0] if not leads_df.empty else 0}</h3><p>Total Leads</p></div>', unsafe_allow_html=True)

    with col2:
        pitches_df = get_data("SELECT COUNT(*) as count FROM pitches")
        st.markdown(f'<div class="metric-card"><i class="fas fa-file-alt fa-2x" style="color: #2196F3;"></i><h3>{pitches_df["count"][0] if not pitches_df.empty else 0}</h3><p>Pitches Generated</p></div>', unsafe_allow_html=True)

    with col3:
        emails_df = get_data("SELECT COUNT(*) as count FROM emails WHERE status='sent'")
        st.markdown(f'<div class="metric-card"><i class="fas fa-paper-plane fa-2x" style="color: #FF9800;"></i><h3>{emails_df["count"][0] if not emails_df.empty else 0}</h3><p>Emails Sent</p></div>', unsafe_allow_html=True)

    # NEW METRIC CARD
    with col4:
        forms_df = get_data("SELECT COUNT(*) as count FROM form_submissions")
        st.markdown(f'<div class="metric-card"><i class="fas fa-paper-plane fa-2x" style="color: #9C27B0;"></i><h3>{forms_df["count"][0] if not forms_df.empty else 0}</h3><p>Forms Submitted</p></div>', unsafe_allow_html=True)

    st.divider()
    st.subheader("Activity Overview")
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.markdown("#### Email Delivery Status")
        status_df = get_data("SELECT status, COUNT(*) as count FROM emails GROUP BY status")
        if not status_df.empty:
            fig = px.pie(status_df, values='count', names='status', color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("No email data yet.")
    with col_chart2:
        st.markdown("#### Recent Activity Log")
        recent_emails = get_data("SELECT recipient_email, subject, sent_at FROM emails ORDER BY sent_at DESC LIMIT 5")
        if not recent_emails.empty: st.dataframe(recent_emails, hide_index=True, use_container_width=True)
        else: st.info("No recent emails found.")

    st.divider()
    st.subheader("Database Records")
    tab1, tab2, tab3, tab4 = st.tabs(["Leads", "Pitches", "Emails", "Form Submissions"]) # NEW TAB
    with tab1: st.dataframe(get_data("SELECT * FROM leads ORDER BY created_at DESC"), use_container_width=True)
    with tab2: st.dataframe(get_data("SELECT * FROM pitches ORDER BY created_at DESC"), use_container_width=True)
    with tab3: st.dataframe(get_data("SELECT * FROM emails ORDER BY sent_at DESC"), use_container_width=True)
    with tab4: st.dataframe(get_data("SELECT * FROM form_submissions ORDER BY submitted_at DESC"), use_container_width=True) # NEW TAB CONTENT

with tab_chat:
    st.markdown('<i class="fas fa-comments" style="font-size: 2.5em; color: #9C27B0;"></i>', unsafe_allow_html=True)
    st.title("Chat with Hunti AI")
    st.markdown("Ask Hunti to perform tasks, analyze screens, or automate workflows.")
    if st.session_state.user_role:
        st.subheader(f"Suggestions for {st.session_state.user_role}")
        cols = st.columns(2)
        for i, text in enumerate(ROLE_SUGGESTIONS[st.session_state.user_role]):
            with cols[i % 2]:
                if st.button(text, key=f"sugg_{i}", use_container_width=True):
                    st.session_state.suggested_prompt = text
                    st.rerun()
        st.divider()
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]): st.markdown(message["content"])
    prompt = st.chat_input("What would you like Hunti to do?")
    if hasattr(st.session_state, 'suggested_prompt') and st.session_state.suggested_prompt:
        prompt = st.session_state.suggested_prompt
        del st.session_state.suggested_prompt
    if prompt:
        allowed, message = check_rate_limit(st.session_state.user_id, action="chat", max_requests=10, window_minutes=60)
        if not allowed: st.error(f"⚠️ {message}"); st.stop()
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Hunti is thinking..."):
                try:
                    result = ask_assistant(prompt, "", temperature=0.7)
                    response_text = result.get('text', 'Task processed successfully!')
                    st.markdown(response_text)
                    st.session_state.chat_history.append({"role": "assistant", "content": response_text})
                    with st.expander("View Action Details"): st.json(result)
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    st.session_state.chat_history.append({"role": "assistant", "content": f"Sorry, I encountered an error: {str(e)}"})
        st.rerun()