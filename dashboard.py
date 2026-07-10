import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime
import os
import hashlib
import random

# Import your modules
from brain import ask_assistant
from vision import capture_screen
from rate_limiter import check_rate_limit, get_usage_stats

# --- Page Configuration ---
st.set_page_config(page_title="Hunti AI Analytics", page_icon="🤖", layout="wide")

# --- Inject Font Awesome for professional icons ---
st.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        .metric-card {background-color: #1E1E1E; padding: 20px; border-radius: 10px; margin: 10px 0;}
        .suggestion-btn {width: 100%; text-align: left; padding: 15px; margin: 5px 0;}
    </style>
""", unsafe_allow_html=True)

# --- Session State ---
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

if 'user_id' not in st.session_state:
    st.session_state.user_id = f"user_{int(datetime.now().timestamp())}_{random.randint(1000, 9999)}"

if 'user_role' not in st.session_state:
    st.session_state.user_role = None

# --- Database Connection ---
DB_NAME = "hunti.db"

def get_data(query):
    """Helper to run SQL queries and return a Pandas DataFrame."""
    use_demo = False
    try:
        if not os.path.exists(DB_NAME):
            use_demo = True
        else:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM leads")
            if cursor.fetchone()[0] == 0:
                use_demo = True
            conn.close()
    except:
        use_demo = True
    
    if use_demo:
        if "COUNT(*) as count FROM leads" in query:
            return pd.DataFrame({'count': [47]})
        elif "COUNT(*) as count FROM pitches" in query:
            return pd.DataFrame({'count': [32]})
        elif "COUNT(*) as count FROM emails WHERE status='sent'" in query:
            return pd.DataFrame({'count': [28]})
        elif "status, COUNT(*) as count FROM emails GROUP BY status" in query:
            return pd.DataFrame({
                'status': ['sent', 'failed', 'pending'],
                'count': [28, 2, 2]
            })
        elif "recipient_email, subject, sent_at FROM emails ORDER BY sent_at DESC LIMIT 5" in query:
            return pd.DataFrame({
                'recipient_email': ['contact@acme.com', 'info@techsol.com', 'sales@globallog.com', 'admin@smartsys.com', 'hello@innovate.com'],
                'subject': ['AI Automation Partnership', 'Streamline Your Workflow', 'Custom AI Solution', 'Lead Generation Demo', 'Sales Automation Proposal'],
                'sent_at': ['2024-01-15 14:30:00', '2024-01-15 11:20:00', '2024-01-14 16:45:00', '2024-01-14 09:15:00', '2024-01-13 13:00:00']
            })
        elif "SELECT * FROM leads ORDER BY created_at DESC" in query:
            return pd.DataFrame({
                'id': [1, 2, 3, 4, 5],
                'company_name': ['Acme Corp', 'Tech Solutions', 'Global Logistics', 'Smart Systems', 'Innovate Ltd'],
                'website': ['acme.com', 'techsol.com', 'globallog.com', 'smartsys.com', 'innovate.com'],
                'phone': ['+1-555-0101', '+1-555-0102', '+1-555-0103', '+1-555-0104', '+1-555-0105'],
                'rating': [4.5, 3.8, 4.2, 4.9, 4.1],
                'created_at': ['2024-01-15', '2024-01-14', '2024-01-13', '2024-01-12', '2024-01-11']
            })
        elif "SELECT * FROM pitches ORDER BY created_at DESC" in query:
            return pd.DataFrame({
                'id': [1, 2, 3],
                'lead_id': [1, 2, 3],
                'pitch_text': ['Personalized AI automation pitch for Acme Corp...', 'Custom workflow solution for Tech Solutions...', 'Lead generation demo for Global Logistics...'],
                'created_at': ['2024-01-15', '2024-01-14', '2024-01-13']
            })
        elif "SELECT * FROM emails ORDER BY sent_at DESC" in query:
            return pd.DataFrame({
                'id': [1, 2, 3],
                'pitch_id': [1, 2, 3],
                'recipient_email': ['contact@acme.com', 'info@techsol.com', 'sales@globallog.com'],
                'subject': ['AI Automation Partnership', 'Streamline Your Workflow', 'Custom AI Solution'],
                'status': ['sent', 'sent', 'sent'],
                'sent_at': ['2024-01-15 14:30:00', '2024-01-15 11:20:00', '2024-01-14 16:45:00']
            })
    
    try:
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()

# Role-based suggestions with professional icons
ROLE_SUGGESTIONS = {
    "Freelancer/Solopreneur": [
        ("fa-briefcase", "Find 10 small businesses that need automation help"),
        ("fa-envelope", "Write a pitch offering my freelance automation services"),
        ("fa-chart-line", "Help me identify which businesses need my skills most"),
        ("fa-clock", "Automate my client outreach so I can focus on work"),
    ],
    "Small Business Owner": [
        ("fa-bullseye", "Find potential clients in my industry"),
        ("fa-envelope-open-text", "Create personalized pitches for local businesses"),
        ("fa-cogs", "Build an automation system for my sales team"),
        ("fa-chart-line", "Help me scale my business with AI tools"),
    ],
    "Agency Owner": [
        ("fa-building", "Find 20 mid-size companies needing automation consulting"),
        ("fa-lightbulb", "Write enterprise-level pitch for AI transformation services"),
        ("fa-database", "Build a complete CRM system for my agency"),
        ("fa-robot", "Automate lead generation and qualification process"),
    ],
    "Enterprise/Corporate": [
        ("fa-sitemap", "Design an enterprise-wide automation strategy"),
        ("fa-users", "Create a pilot program for department automation"),
        ("fa-calculator", "Build ROI analysis for AI implementation"),
        ("fa-graduation-cap", "Develop training plan for AI adoption"),
    ],
    "Developer/Tech": [
        ("fa-code", "Help me build custom automation tools for clients"),
        ("fa-plug", "Integrate AI APIs into existing workflows"),
        ("fa-cube", "Create a white-label automation solution"),
        ("fa-mobile-alt", "Build mobile-friendly lead capture system"),
    ]
}

ROLE_DESCRIPTIONS = {
    "Freelancer/Solopreneur": "Looking for quick wins and time-saving automation",
    "Small Business Owner": "Ready to scale but needs practical solutions",
    "Agency Owner": "Needs systems to serve multiple clients efficiently",
    "Enterprise/Corporate": "Requires strategic implementation and ROI proof",
    "Developer/Tech": "Wants to build or integrate automation tools"
}

# --- Sidebar: User Info & Rate Limit ---
with st.sidebar:
    st.markdown('<i class="fas fa-user-circle fa-2x"></i>', unsafe_allow_html=True)
    st.title("User Profile")
    
    selected_role = st.selectbox(
        "What best describes you?",
        options=["Freelancer/Solopreneur", "Small Business Owner", "Agency Owner", "Enterprise/Corporate", "Developer/Tech"],
        index=0 if st.session_state.user_role is None else list(ROLE_SUGGESTIONS.keys()).index(st.session_state.user_role)
    )
    
    if selected_role != st.session_state.user_role:
        st.session_state.user_role = selected_role
        st.rerun()
    
    st.write(f"**User ID:** `{st.session_state.user_id}`")
    
    if st.session_state.user_role:
        st.info(f"💡 {ROLE_DESCRIPTIONS[st.session_state.user_role]}")
    
    stats = get_usage_stats(st.session_state.user_id)
    st.metric("Total Requests", stats['total_requests'])
    st.metric("Requests (Last Hour)", stats['requests_last_hour'], delta=f"Limit: 10/hour")
    
    st.divider()
    st.caption("Hunti AI | Built with Python & Streamlit")

# --- Main UI ---
st.markdown('<i class="fas fa-robot fa-3x"></i>', unsafe_allow_html=True)
st.title("Hunti AI - Command Center")
st.markdown("Real-time analytics for your AI sales agent.")
st.divider()

tab_analytics, tab_chat = st.tabs(["Analytics Dashboard", "Chat with Hunti AI"])

with tab_analytics:
    col1, col2, col3 = st.columns(3)

    with col1:
        leads_df = get_data("SELECT COUNT(*) as count FROM leads")
        total_leads = leads_df['count'][0] if not leads_df.empty else 0
        st.markdown(f'<div class="metric-card"><i class="fas fa-database fa-2x" style="color: #4CAF50;"></i><h3>{total_leads}</h3><p>Total Leads Scraped</p></div>', unsafe_allow_html=True)

    with col2:
        pitches_df = get_data("SELECT COUNT(*) as count FROM pitches")
        total_pitches = pitches_df['count'][0] if not pitches_df.empty else 0
        st.markdown(f'<div class="metric-card"><i class="fas fa-file-alt fa-2x" style="color: #2196F3;"></i><h3>{total_pitches}</h3><p>Pitches Generated</p></div>', unsafe_allow_html=True)

    with col3:
        emails_df = get_data("SELECT COUNT(*) as count FROM emails WHERE status='sent'")
        total_emails = emails_df['count'][0] if not emails_df.empty else 0
        st.markdown(f'<div class="metric-card"><i class="fas fa-paper-plane fa-2x" style="color: #FF9800;"></i><h3>{total_emails}</h3><p>Emails Sent</p></div>', unsafe_allow_html=True)

    st.divider()
    st.subheader("Activity Overview")

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown("#### Email Delivery Status")
        status_df = get_data("SELECT status, COUNT(*) as count FROM emails GROUP BY status")
        if not status_df.empty:
            fig = px.pie(status_df, values='count', names='status', title='Email Status Breakdown', color_discrete_sequence=px.colors.sequential.RdBu)
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
    tab1, tab2, tab3 = st.tabs(["Leads", "Pitches", "Emails"])

    with tab1:
        st.dataframe(get_data("SELECT * FROM leads ORDER BY created_at DESC"), use_container_width=True)

    with tab2:
        st.dataframe(get_data("SELECT * FROM pitches ORDER BY created_at DESC"), use_container_width=True)

    with tab3:
        st.dataframe(get_data("SELECT * FROM emails ORDER BY sent_at DESC"), use_container_width=True)

with tab_chat:
    st.markdown('<i class="fas fa-comments fa-3x"></i>', unsafe_allow_html=True)
    st.title("Chat with Hunti AI")
    st.markdown("Ask Hunti to perform tasks, analyze screens, or automate workflows.")
    
    if st.session_state.user_role:
        st.subheader(f"Suggestions for {st.session_state.user_role}")
        
        cols = st.columns(2)
        for i, (icon, text) in enumerate(ROLE_SUGGESTIONS[st.session_state.user_role]):
            with cols[i % 2]:
                btn_html = f'<button class="suggestion-btn"><i class="fas {icon}"></i> {text}</button>'
                if st.button(btn_html, key=f"sugg_{i}"):
                    st.session_state.suggested_prompt = text
                    st.rerun()
        
        st.divider()
    
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    prompt = st.chat_input("What would you like Hunti to do?")
    
    if hasattr(st.session_state, 'suggested_prompt') and st.session_state.suggested_prompt:
        prompt = st.session_state.suggested_prompt
        del st.session_state.suggested_prompt
    
    if prompt:
        allowed, message = check_rate_limit(st.session_state.user_id, action="chat", max_requests=10, window_minutes=60)
        
        if not allowed:
            st.error(f"⚠️ {message}")
            st.stop()
        
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Hunti is thinking..."):
                try:
                    img_b64 = ""
                    result = ask_assistant(prompt, img_b64, temperature=0.7)
                    response_text = result.get('text', 'Task processed successfully!')
                    st.markdown(response_text)
                    
                    st.session_state.chat_history.append({
                        "role": "assistant", 
                        "content": response_text
                    })
                    
                    with st.expander("View Action Details"):
                        st.json(result)
                    
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": f"Sorry, I encountered an error: {str(e)}"
                    })
        
        st.rerun()