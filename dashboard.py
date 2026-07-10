import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime
import os

# --- Page Configuration ---
st.set_page_config(page_title="Hunti AI Analytics", page_icon="🤖", layout="wide")

# --- Database Connection ---
DB_NAME = "hunti.db"

def get_data(query):
    """Helper to run SQL queries and return a Pandas DataFrame."""
    # Check if we should use demo data (when DB doesn't exist or is empty)
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
    
    # Return demo data for portfolio display
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
    
    # Real database connection
    try:
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()

# --- UI Header ---
st.title("🤖 Hunti AI - Command Center")
st.markdown("Real-time analytics for your AI sales agent.")
st.divider()

# --- Top Metrics ---
col1, col2, col3 = st.columns(3)

with col1:
    leads_df = get_data("SELECT COUNT(*) as count FROM leads")
    total_leads = leads_df['count'][0] if not leads_df.empty else 0
    st.metric("Total Leads Scraped", total_leads)

with col2:
    pitches_df = get_data("SELECT COUNT(*) as count FROM pitches")
    total_pitches = pitches_df['count'][0] if not pitches_df.empty else 0
    st.metric("Pitches Generated", total_pitches)

with col3:
    emails_df = get_data("SELECT COUNT(*) as count FROM emails WHERE status='sent'")
    total_emails = emails_df['count'][0] if not emails_df.empty else 0
    st.metric("Emails Sent", total_emails)

st.divider()

# --- Charts Section ---
st.subheader("Activity Overview")

col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.markdown("**Email Delivery Status**")
    status_df = get_data("SELECT status, COUNT(*) as count FROM emails GROUP BY status")
    if not status_df.empty:
        fig = px.pie(status_df, values='count', names='status', title='Email Status Breakdown', color_discrete_sequence=px.colors.sequential.RdBu)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No email data yet. Send a pitch to see this chart!")

with col_chart2:
    st.markdown("**Recent Activity Log**")
    recent_emails = get_data("SELECT recipient_email, subject, sent_at FROM emails ORDER BY sent_at DESC LIMIT 5")
    if not recent_emails.empty:
        st.dataframe(recent_emails, hide_index=True, use_container_width=True)
    else:
        st.info("No recent emails found.")

st.divider()

# --- Data Tables ---
st.subheader("Database Records")

tab1, tab2, tab3 = st.tabs(["Leads", "Pitches", "Emails"])

with tab1:
    st.dataframe(get_data("SELECT * FROM leads ORDER BY created_at DESC"), use_container_width=True)

with tab2:
    st.dataframe(get_data("SELECT * FROM pitches ORDER BY created_at DESC"), use_container_width=True)

with tab3:
    st.dataframe(get_data("SELECT * FROM emails ORDER BY sent_at DESC"), use_container_width=True)

# --- Footer ---
st.divider()
st.caption("🚀 Hunti AI - Built with Python, Streamlit, and Groq AI | [Live Demo](https://hunti-ai.streamlit.app)")