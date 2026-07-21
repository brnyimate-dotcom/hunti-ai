import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime
import os
import random
import time

from brain import ask_assistant, build_pitches, get_pitches_from_db
from rate_limiter import check_rate_limit, get_usage_stats

st.set_page_config(page_title="Hunti AI - Command Center", page_icon="🤖", layout="wide")

# --- CSS FOR LOADING OVERLAY ---
st.markdown("""
    <style>
        .metric-card { background-color: #1E1E1E; padding: 20px; border-radius: 10px; margin: 10px 0; border: 1px solid #333; }
        .metric-card h3 { margin: 10px 0 5px 0; font-size: 2em; }
        .metric-card p { margin: 0; color: #888; }
        .stButton>button { transition: all 0.2s; }
        .stButton>button:active { transform: scale(0.98); }
        
        /* Loading overlay styles */
        .loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.8);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
        }
        .loading-spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #4CAF50;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
""", unsafe_allow_html=True)

# --- TRANSLATION DICTIONARY ---
T = {
    "en": {
        "onboarding_title": "Welcome to Hunti AI Solutions",
        "onboarding_subtitle": "Let's personalize your automation dashboard in just a few seconds.",
        "select_lang": "Select your preferred language",
        "select_business": "What best describes your business?",
        "btn_start": "Generate My Dashboard",
        "lang_en": "English",
        "lang_hu": "Hungarian (Magyar)",
        "biz_small": "Small Business Owner",
        "biz_agency": "Agency Owner",
        "biz_ecom": "E-commerce",
        "biz_freelance": "Freelancer / Solopreneur",
        "nav_hunti": "Hunti AI",
        "nav_analytics": "Analytics Dashboard",
        "nav_pitches": "Pitch Emailer",
        "sidebar_title": "User Profile",
        "reset_prefs": "Reset Preferences",
        "total_req": "Total Requests",
        "req_hour": "Requests (Last Hour)",
        "hunti_title": "Hunti AI - Your Intelligent Sales Consultant",
        "hunti_welcome": "Welcome! I'm here to help you automate your business and save time.",
        "hunti_sub": "Tell me about your challenges, and I'll show you how AI can solve them.",
        "hunti_input": "What challenge are you facing?",
        "analytics_title": "Analytics Dashboard",
        "analytics_sub": "Real-time performance metrics for your automation campaigns.",
        "total_leads": "Total Leads",
        "pitches_gen": "Pitches Generated",
        "emails_sent": "Emails Sent",
        "forms_sub": "Forms Submitted",
        "activity_overview": "Activity Overview",
        "email_status": "Email Delivery Status",
        "recent_activity": "Recent Activity Log",
        "db_records": "Database Records",
        "pitch_title": "Automated Pitch Emailer",
        "pitch_sub": "Generate and send personalized sales pitches to your leads automatically.",
        "pitch_info": "How it works: Select leads from your database, and Hunti will generate personalized pitches and send them via email.",
        "avail_leads": "Available Leads",
        "btn_gen_pitch": "Generate Pitches",
        "btn_view_pitch": "View Generated Pitches",
        "success_gen": "Successfully generated pitches!",
        "no_leads": "No leads found. Add some leads first!",
        "no_pitches": "No pitches generated yet. Click 'Generate Pitches' to create them.",
        "footer": "2026 Hunti AI Solutions. All rights reserved.",
        "loading": "Loading...",
        "generating": "Generating...",
        "suggestions": {
            "Small Business Owner": [
                "I'm drowning in emails and can't respond fast enough",
                "My team wastes hours on repetitive manual tasks",
                "I need to generate more leads but don't have time",
                "I want to automate my customer follow-ups"
            ],
            "Agency Owner": [
                "My team spends too much time on client onboarding",
                "We need to automate our proposal generation",
                "I want to streamline our client reporting process",
                "We're struggling to manage multiple client communications"
            ],
            "E-commerce": [
                "I need to automate order confirmations and tracking",
                "Customers keep asking the same questions repeatedly",
                "I want to automate inventory updates and notifications",
                "I need better ways to collect and respond to reviews"
            ],
            "Freelancer / Solopreneur": [
                "I spend too much time on admin instead of billable work",
                "I need to automate my client discovery process",
                "I want to automate my invoicing and payment reminders",
                "I need help finding and qualifying new clients"
            ]
        }
    },
    "hu": {
        "onboarding_title": "Üdvözöljük a Hunti AI Solutions-nél",
        "onboarding_subtitle": "Személyre szabjuk az automatizálási irányítópultját néhány másodperc alatt.",
        "select_lang": "Válassza ki a preferált nyelvet",
        "select_business": "Mi írja le legjobban a vállalkozását?",
        "btn_start": "Irányítópult Generálása",
        "lang_en": "Angol (English)",
        "lang_hu": "Magyar",
        "biz_small": "Kisvállalkozás Tulajdonos",
        "biz_agency": "Ügynökség Tulajdonos",
        "biz_ecom": "E-kereskedelem",
        "biz_freelance": "Szabadúszó / Egyéni Vállalkozó",
        "nav_hunti": "Hunti AI",
        "nav_analytics": "Analitikai Irányítópult",
        "nav_pitches": "Automatizált Pitch Küldő",
        "sidebar_title": "Felhasználói Profil",
        "reset_prefs": "Beállítások Visszaállítása",
        "total_req": "Összes Kérés",
        "req_hour": "Kérések (Utolsó Óra)",
        "hunti_title": "Hunti AI - Az Ön Intelligens Értékesítési Tanácsadója",
        "hunti_welcome": "Üdvözöljük! Segítek automatizálni a vállalkozását és időt spórolni.",
        "hunti_sub": "Meséljen a kihívásairól, és megmutatom, hogyan oldhatja meg őket az AI.",
        "hunti_input": "Milyen kihívással néz szembe?",
        "analytics_title": "Analitikai Irányítópult",
        "analytics_sub": "Valós idejű teljesítménymutatók az automatizálási kampányaihoz.",
        "total_leads": "Összes Lead",
        "pitches_gen": "Generált Pitch-ek",
        "emails_sent": "Elküldött Emailek",
        "forms_sub": "Kitöltött Űrlapok",
        "activity_overview": "Tevékenység Áttekintése",
        "email_status": "Email Kézbesítési Státusz",
        "recent_activity": "Legutóbbi Tevékenységi Napló",
        "db_records": "Adatbázis Rekordok",
        "pitch_title": "Automatizált Pitch Küldő",
        "pitch_sub": "Generáljon és küldjön személyre szabott értékesítési pitch-eket automatikusan.",
        "pitch_info": "Hogyan működik: Válasszon lead-eket az adatbázisból, és a Hunti személyre szabott pitch-eket generál és küld el emailben.",
        "avail_leads": "Elérhető Lead-ek",
        "btn_gen_pitch": "Pitch-ek Generálása",
        "btn_view_pitch": "Generált Pitch-ek Megtekintése",
        "success_gen": "Sikeresen generálva!",
        "no_leads": "Nincs találat. Először adjon hozzá lead-eket!",
        "no_pitches": "Még nincs generálva pitch. Kattintson a 'Pitch-ek Generálása' gombra.",
        "footer": "2026 Hunti AI Solutions. Minden jog fenntartva.",
        "loading": "Betöltés...",
        "generating": "Generálás...",
        "suggestions": {
            "Kisvállalkozás Tulajdonos": [
                "Elnyomnak az emailek, nem tudunk elég gyorsan válaszolni",
                "A csapatom órákat pazarol ismétlődő manuális feladatokra",
                "Több lead-re van szükségem, de nincs rá időm",
                "Automatizálni szeretném az ügyfélkövetéseket"
            ],
            "Ügynökség Tulajdonos": [
                "A csapatom túl sok időt tölt az ügyfélfelvétellel",
                "Automatizálnunk kell az ajánlatkérés-generálást",
                "Szeretném egyszerűsíteni az ügyféljelentési folyamatot",
                "Küzdünk a több ügyfél kommunikációjának kezelésével"
            ],
            "E-kereskedelem": [
                "Automatizálnom kell a rendelés visszaigazolásokat és nyomkövetést",
                "Az ügyfelek folyamatosan ugyanazokat a kérdéseket teszik fel",
                "Szeretném automatizálni a készletfrissítéseket és értesítéseket",
                "Jobb módszereket keresek a vélemények gyűjtésére és kezelésére"
            ],
            "Szabadúszó / Egyéni Vállalkozó": [
                "Túl sok időt töltök adminisztrációval a számlázható munka helyett",
                "Automatizálnom kell az ügyfélfelderítési folyamatot",
                "Szeretném automatizálni a számlázást és a fizetési emlékeztetőket",
                "Segítségre van szükségem új ügyfelek megtalálásában és minősítésében"
            ]
        }
    }
}

# --- SESSION STATE INITIALIZATION ---
if 'onboarding_complete' not in st.session_state:
    st.session_state.onboarding_complete = False
if 'language' not in st.session_state:
    st.session_state.language = 'en'
if 'business_type' not in st.session_state:
    st.session_state.business_type = 'Small Business Owner'
if 'chat_history' not in st.session_state: 
    st.session_state.chat_history = []
if 'user_id' not in st.session_state: 
    st.session_state.user_id = f"user_{int(datetime.now().timestamp())}_{random.randint(1000, 9999)}"
if 'page' not in st.session_state:
    st.session_state.page = "Hunti AI"
if 'target_page' not in st.session_state:
    st.session_state.target_page = None

DB_NAME = "hunti.db"

def t(key):
    """Helper function to get translation"""
    keys = key.split('.')
    val = T[st.session_state.language]
    for k in keys:
        val = val.get(k, key)
    return val

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

# --- ONBOARDING PAGE ---
if not st.session_state.onboarding_complete:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title(t("onboarding_title"))
        st.markdown(f"*{t('onboarding_subtitle')}*")
        st.divider()
        
        if 'temp_lang' not in st.session_state:
            st.session_state.temp_lang = 'en'
        if 'temp_business' not in st.session_state:
            st.session_state.temp_business = 'Small Business Owner'
        
        lang_options = {"English": "en", "Magyar": "hu"}
        selected_lang_name = st.selectbox(
            t("select_lang"), 
            list(lang_options.keys()), 
            index=1 if st.session_state.temp_lang == 'hu' else 0,
            key="onboarding_lang"
        )
        st.session_state.temp_lang = lang_options[selected_lang_name]
        st.session_state.language = st.session_state.temp_lang
        
        biz_options_en = ["Small Business Owner", "Agency Owner", "E-commerce", "Freelancer / Solopreneur"]
        biz_options_hu = ["Kisvállalkozás Tulajdonos", "Ügynökség Tulajdonos", "E-kereskedelem", "Szabadúszó / Egyéni Vállalkozó"]
        
        biz_options = biz_options_hu if st.session_state.language == 'hu' else biz_options_en
        
        selected_biz = st.selectbox(
            t("select_business"), 
            biz_options, 
            index=0,
            key="onboarding_biz"
        )
        st.session_state.temp_business = selected_biz
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button(t("btn_start"), type="primary", use_container_width=True, key="btn_onboard"):
            st.session_state.language = st.session_state.temp_lang
            st.session_state.business_type = st.session_state.temp_business
            st.session_state.onboarding_complete = True
            if 'temp_lang' in st.session_state:
                del st.session_state.temp_lang
            if 'temp_business' in st.session_state:
                del st.session_state.temp_business
            st.rerun()
    st.stop()

# --- PAGE TRANSITION HANDLER ---
if st.session_state.target_page and st.session_state.target_page != st.session_state.page:
    # Show loading overlay
    st.markdown("""
        <div class="loading-overlay">
            <div>
                <div class="loading-spinner"></div>
                <p style="color: white; margin-top: 20px; font-size: 18px;">""" + t("loading") + """</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Small delay to show loading
    time.sleep(0.5)
    
    # Update to target page
    st.session_state.page = st.session_state.target_page
    st.session_state.target_page = None
    st.rerun()

# --- MAIN APP ---
def navigate_to_page(page_name):
    """Set target page for smooth transition"""
    st.session_state.target_page = page_name

# Top Navigation
col_nav1, col_nav2, col_nav3 = st.columns(3)
with col_nav1:
    if st.button(t("nav_hunti"), use_container_width=True, key="btn_hunti"):
        navigate_to_page("Hunti AI")
with col_nav2:
    if st.button(t("nav_analytics"), use_container_width=True, key="btn_analytics"):
        navigate_to_page("Analytics")
with col_nav3:
    if st.button(t("nav_pitches"), use_container_width=True, key="btn_pitches"):
        navigate_to_page("Pitch Emailer")

st.divider()

# Sidebar
with st.sidebar:
    st.title(t("sidebar_title"))
    st.write(f"**Business Type:** {st.session_state.business_type}")
    st.write(f"User ID: `{st.session_state.user_id}`")
    
    if st.button(t("reset_prefs"), use_container_width=True, key="btn_reset"):
        st.session_state.onboarding_complete = False
        st.session_state.chat_history = []
        st.session_state.language = 'en'
        st.session_state.business_type = 'Small Business Owner'
        st.rerun()
    
    st.divider()
    try:
        stats = get_usage_stats(st.session_state.user_id)
        st.metric(t("total_req"), stats['total_requests'])
        st.metric(t("req_hour"), stats['requests_last_hour'], delta="Limit: 10/hour")
    except:
        pass
    
    st.divider()
    st.caption("Hunti AI Solutions")

# Main content based on selected page
if st.session_state.page == "Hunti AI":
    st.title(t("hunti_title"))
    st.markdown(t("hunti_welcome"))
    st.markdown(f"*{t('hunti_sub')}*")
    st.divider()
    
    if st.session_state.business_type:
        st.subheader(f"Common Challenges for {st.session_state.business_type}")
        cols = st.columns(2)
        suggestions = t(f"suggestions.{st.session_state.business_type}")
        for i, text in enumerate(suggestions):
            with cols[i % 2]:
                if st.button(text, key=f"sugg_{i}", use_container_width=True):
                    st.session_state.suggested_prompt = text
                    st.rerun()
        st.divider()
    
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]): 
                st.markdown(message["content"])
    
    prompt = st.chat_input(t("hunti_input"))
    
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
    st.title(t("analytics_title"))
    st.markdown(t("analytics_sub"))
    st.divider()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        leads_df = get_data("SELECT COUNT(*) as count FROM leads")
        st.markdown(f'<div class="metric-card"><h3>{leads_df["count"][0] if not leads_df.empty else 0}</h3><p>{t("total_leads")}</p></div>', unsafe_allow_html=True)
    with col2:
        pitches_df = get_data("SELECT COUNT(*) as count FROM pitches")
        st.markdown(f'<div class="metric-card"><h3>{pitches_df["count"][0] if not pitches_df.empty else 0}</h3><p>{t("pitches_gen")}</p></div>', unsafe_allow_html=True)
    with col3:
        emails_df = get_data("SELECT COUNT(*) as count FROM emails WHERE status='sent'")
        st.markdown(f'<div class="metric-card"><h3>{emails_df["count"][0] if not emails_df.empty else 0}</h3><p>{t("emails_sent")}</p></div>', unsafe_allow_html=True)
    with col4:
        forms_df = get_data("SELECT COUNT(*) as count FROM form_submissions")
        st.markdown(f'<div class="metric-card"><h3>{forms_df["count"][0] if not forms_df.empty else 0}</h3><p>{t("forms_sub")}</p></div>', unsafe_allow_html=True)

    st.divider()
    st.subheader(t("activity_overview"))
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.markdown(f"#### {t('email_status')}")
        status_df = get_data("SELECT status, COUNT(*) as count FROM emails GROUP BY status")
        if not status_df.empty:
            fig = px.pie(status_df, values='count', names='status', color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig, use_container_width=True)
        else: 
            st.info("No email data yet.")
    
    with col_chart2:
        st.markdown(f"#### {t('recent_activity')}")
        recent_emails = get_data("SELECT recipient_email, subject, sent_at FROM emails ORDER BY sent_at DESC LIMIT 5")
        if not recent_emails.empty: 
            st.dataframe(recent_emails, hide_index=True, use_container_width=True)
        else: 
            st.info("No recent emails found.")

    st.divider()
    st.subheader(t("db_records"))
    tab1, tab2, tab3, tab4 = st.tabs([t("total_leads"), t("pitches_gen"), t("emails_sent"), t("forms_sub")])
    with tab1: st.dataframe(get_data("SELECT * FROM leads ORDER BY created_at DESC"), use_container_width=True)
    with tab2: st.dataframe(get_data("SELECT * FROM pitches ORDER BY created_at DESC"), use_container_width=True)
    with tab3: st.dataframe(get_data("SELECT * FROM emails ORDER BY sent_at DESC"), use_container_width=True)
    with tab4: st.dataframe(get_data("SELECT * FROM form_submissions ORDER BY submitted_at DESC"), use_container_width=True)

elif st.session_state.page == "Pitch Emailer":
    st.title(t("pitch_title"))
    st.markdown(t("pitch_sub"))
    st.divider()
    
    st.info(t("pitch_info"))
    
    leads_df = get_data("SELECT * FROM leads ORDER BY created_at DESC")
    if not leads_df.empty:
        st.subheader(t("avail_leads"))
        st.dataframe(leads_df, use_container_width=True)
        
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            if st.button(t("btn_gen_pitch"), type="primary", use_container_width=True, key="btn_generate_pitches"):
                try:
                    with st.spinner(t("generating")):
                        if os.path.exists(DB_NAME):
                            pitches = build_pitches()
                            st.success(f"{t('success_gen')} ({len(pitches)})")
                        else:
                            st.success(f"{t('success_gen')} (Demo Mode)")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        
        with col2:
            if st.button(t("btn_view_pitch"), use_container_width=True, key="btn_view_pitches"):
                pitches_df = get_data("SELECT * FROM pitches ORDER BY created_at DESC")
                if not pitches_df.empty:
                    st.dataframe(pitches_df, use_container_width=True)
                else:
                    st.info(t("no_pitches"))
    else:
        st.warning(t("no_leads"))

st.divider()
st.markdown(t("footer"))