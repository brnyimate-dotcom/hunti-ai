import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime

# --- Page Configuration ---
st.set_page_config(page_title="Hunti AI Analytics", page_icon="🤖", layout="wide")

# --- Database Connection ---
DB_NAME = "hunti.db"

def get_data(query):
    """Helper to run SQL queries and return a Pandas DataFrame."""
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