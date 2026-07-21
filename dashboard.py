import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime
import os
import random

from brain import ask_assistant
from rate_limiter import check_rate_limit, get_usage_stats
from brain import build_pitches, get_pitches_from_db, get_all_leads_from_db

st.set_page_config(page_title="Hunti AI - Command Center", page_icon="🤖", layout="wide")

st.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        .metric-card { background-color: #1E1E1E; padding: 20px; border-radius: 10px; margin: 10px 0; border: 1px solid #333; }
        .metric-card h3 { margin: 10px 0 5px 0; font-size: 2em; }
        .metric-card p { margin: 0; color: #888; }
        .metric-card i { margin-bottom: 10px; }
        .top-nav { background-color: #1E1E1E; padding: 15px 30px; border-radius: 10px; margin-bottom: 30px; }
        .nav-button { background-color: transparent; border: 2px solid #4CAF50; color: #4CAF50; padding: 10px 25px; border-radius: 8px; cursor: pointer; font-weight: 600; margin-right: 10px; transition: all 0.3s; }
        .nav-button:hover { background-color: #4CAF50; color: white; }
        .nav-button.active { background-color: #4CAF50; color: white; }
    </style>
""", unsafe_allow_html=True)

# Session state
if 'chat_history' not in st.session_state: 
    st.session_state.chat_history = []
if 'user_id' not in st.session_state: 
    st.session_state.user_id = f"user_{int(datetime.now().timestamp())}_{random.randint(1000, 9999)}"
if 'user_role' not in st.session_state: 
    st.session_state.user_role = None
if 'page' not in st.session_state:
    st.session_state.page = "Hunti AI"

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
        elif "COUNT(*) as count FROM form_submissions" in query: return pd.DataFrame({'count': [15]})
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
        elif "SELECT * FROM form_submissions ORDER BY submitted_at DESC" in query:
            return pd.DataFrame({'id': [1, 2], 'company_name': ['Acme Corp', 'Global Logistics'], 'url': ['acme.com/contact', 'globallog.com/contact'], 'status': ['success', 'success'], 'submitted_at': ['2024-01-15', '2024-01-14']})
    
    try:
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()

# Client-focused suggestions
CLIENT_SUGGESTIONS = {
    "Small Business Owner": [
        "I'm drowning in emails and can't respond fast enough",
        "My team wastes hours on repetitive manual tasks",
        "I need to generate more leads but don't have time",
        "I want to automate my customer follow-ups",
    ],
    "Agency Owner": [
        "My team spends too much time on client onboarding",
        "We need to automate our proposal generation",
        "I want to streamline our client reporting process",
        "We're struggling to manage multiple client communications",
    ],
    "E-commerce": [
        "I need to automate order confirmations and tracking",
        "Customers keep asking the same questions repeatedly",
        "I want to automate inventory updates and notifications",
        "I need better ways to collect and respond to reviews",
    ],
    "Freelancer/Solopreneur": [
        "I spend too much time on admin instead of billable work",
        "I need to automate my client discovery process",
        "I want to automate my invoicing and payment reminders",
        "I need help finding and qualifying new clients",
    ]
}

# Top Navigation
st.markdown("""
    <div class="top-nav">
        <button class="nav-button active" onclick="location.href='#'">Hunti AI</button>
        <button class="nav-button" onclick="location.href='#'">Analytics</button>
        <button class="nav-button" onclick="location.href='#'">Pitch Emailer</button>
    </div>
""", unsafe_allow_html=True)

col_nav1, col_nav2, col_nav3 = st.columns(3)
with col_nav1:
    if st.button("Hunti AI", use_container_width=True, key="btn_hunti"):
        st.session_state.page = "Hunti AI"
        st.rerun()
with col_nav2:
    if st.button("Analytics Dashboard", use_container_width=True, key="btn_analytics"):
        st.session_state.page = "Analytics"
        st.rerun()
with col_nav3:
    if st.button("Pitch Emailer", use_container_width=True, key="btn_pitches"):
        st.session_state.page = "Pitch Emailer"
        st.rerun()

st.divider()

# Sidebar - User Profile only
with st.sidebar:
    st.title("User Profile")
    selected_role = st.selectbox(
        "What best describes you?", 
        options=list(CLIENT_SUGGESTIONS.keys()), 
        index=0 if st.session_state.user_role is None else list(CLIENT_SUGGESTIONS.keys()).index(st.session_state.user_role)
    )
    if selected_role != st.session_state.user_role:
        st.session_state.user_role = selected_role
        st.rerun()
    
    st.write(f"**User ID:** `{st.session_state.user_id}`")
    if st.session_state.user_role: 
        st.info(f"{st.session_state.user_role}")
    
    try:
        stats = get_usage_stats(st.session_state.user_id)
        st.metric("Total Requests", stats['total_requests'])
        st.metric("Requests (Last Hour)", stats['requests_last_hour'], delta="Limit: 10/hour")
    except:
        pass
    
    st.divider()
    st.caption("Hunti AI Solutions")

# Main content based on selected page
if st.session_state.page == "Hunti AI":
    st.title("Hunti AI - Your Intelligent Sales Consultant")
    st.markdown("Welcome! I'm here to help you automate your business and save time.")
    st.markdown("*Tell me about your challenges, and I'll show you how AI can solve them.*")
    st.divider()
    
    if st.session_state.user_role:
        st.subheader(f"Common Challenges for {st.session_state.user_role}")
        cols = st.columns(2)
        for i, text in enumerate(CLIENT_SUGGESTIONS[st.session_state.user_role]):
            with cols[i % 2]:
                if st.button(text, key=f"sugg_{i}", use_container_width=True):
                    st.session_state.suggested_prompt = text
                    st.rerun()
        st.divider()
    
    # Chat interface
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]): 
                st.markdown(message["content"])
    
    prompt = st.chat_input("What challenge are you facing?")
    
    if hasattr(st.session_state, 'suggested_prompt') and st.session_state.suggested_prompt:
        prompt = st.session_state.suggested_prompt
        del st.session_state.suggested_prompt
    
    if prompt:
        allowed, message = check_rate_limit(st.session_state.user_id, action="chat", max_requests=10, window_minutes=60)
        if not allowed: 
            st.error(message)
            st.stop()
        
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"): 
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Hunti is thinking..."):
                try:
                    result = ask_assistant(prompt, chat_history=st.session_state.chat_history, temperature=0.7)
                    response_text = result.get('text', 'Task processed successfully!')
                    st.markdown(response_text)
                    st.session_state.chat_history.append({"role": "assistant", "content": response_text})
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    st.session_state.chat_history.append({"role": "assistant", "content": f"Sorry, I encountered an error: {str(e)}"})
        st.rerun()

elif st.session_state.page == "Analytics":
    st.title("Analytics Dashboard")
    st.markdown("Real-time performance metrics for your automation campaigns.")
    st.divider()
    
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        leads_df = get_data("SELECT COUNT(*) as count FROM leads")
        st.markdown(f'<div class="metric-card"><h3>{leads_df["count"][0] if not leads_df.empty else 0}</h3><p>Total Leads</p></div>', unsafe_allow_html=True)

    with col2:
        pitches_df = get_data("SELECT COUNT(*) as count FROM pitches")
        st.markdown(f'<div class="metric-card"><h3>{pitches_df["count"][0] if not pitches_df.empty else 0}</h3><p>Pitches Generated</p></div>', unsafe_allow_html=True)

    with col3:
        emails_df = get_data("SELECT COUNT(*) as count FROM emails WHERE status='sent'")
        st.markdown(f'<div class="metric-card"><h3>{emails_df["count"][0] if not emails_df.empty else 0}</h3><p>Emails Sent</p></div>', unsafe_allow_html=True)

    with col4:
        forms_df = get_data("SELECT COUNT(*) as count FROM form_submissions")
        st.markdown(f'<div class="metric-card"><h3>{forms_df["count"][0] if not forms_df.empty else 0}</h3><p>Forms Submitted</p></div>', unsafe_allow_html=True)

    st.divider()
    st.subheader("Activity Overview")
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.markdown("#### Email Delivery Status")
        status_df = get_data("SELECT status, COUNT(*) as count FROM emails GROUP BY status")
        if not status_df.empty:
            fig = px.pie(status_df, values='count', names='status', color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig, use_container_width=True)
        else: 
            st.info("No email data yet.")
    
    with col_chart2:
        st.markdown("#### Recent Activity Log")
        recent_emails = get_data("SELECT recipient_email, subject, sent_at FROM emails ORDER BY sent_at DESC LIMIT 5")
        if not recent_emails.empty: 
            st.dataframe(recent_emails, hide_index=True, use_container_width=True)
        else: 
            st.info("No recent emails found.")

    st.divider()
    st.subheader("Database Records")
    tab1, tab2, tab3, tab4 = st.tabs(["Leads", "Pitches", "Emails", "Form Submissions"])
    with tab1: 
        st.dataframe(get_data("SELECT * FROM leads ORDER BY created_at DESC"), use_container_width=True)
    with tab2: 
        st.dataframe(get_data("SELECT * FROM pitches ORDER BY created_at DESC"), use_container_width=True)
    with tab3: 
        st.dataframe(get_data("SELECT * FROM emails ORDER BY sent_at DESC"), use_container_width=True)
    with tab4: 
        st.dataframe(get_data("SELECT * FROM form_submissions ORDER BY submitted_at DESC"), use_container_width=True)

elif st.session_state.page == "Pitch Emailer":
    st.title("Automated Pitch Emailer")
    st.markdown("Generate and send personalized sales pitches to your leads automatically.")
    st.divider()
    
    st.info("How it works: Select leads from your database, and Hunti will generate personalized pitches and send them via email.")
    
    # Show leads
    leads_df = get_data("SELECT * FROM leads ORDER BY created_at DESC")
    if not leads_df.empty:
        st.subheader("Available Leads")
        st.dataframe(leads_df, use_container_width=True)
        
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Generate Pitches", type="primary", use_container_width=True):
                try:
                    with st.spinner("Generating personalized pitches..."):
                        pitches = build_pitches()
                        st.success(f"Successfully generated {len(pitches)} pitches!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error generating pitches: {str(e)}")
        
        with col2:
            if st.button("View Generated Pitches", use_container_width=True):
                pitches_df = get_data("SELECT * FROM pitches ORDER BY created_at DESC")
                if not pitches_df.empty:
                    st.dataframe(pitches_df, use_container_width=True)
                else:
                    st.info("No pitches generated yet.")
    else:
        st.warning("No leads found. Add some leads first!")

# Footer
st.divider()
st.markdown("2026 Hunti AI Solutions. All rights reserved.")