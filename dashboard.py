import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime
import os
import random
import json

from brain import ask_assistant, init_groq_client, generate_pitch
from rate_limiter import check_rate_limit, get_usage_stats

st.set_page_config(page_title="Hunti AI - Command Center", page_icon="🤖", layout="wide")

# --- ENHANCED CSS WITH SLIDE TRANSITIONS ---
st.markdown("""
    <style>
        /* Base Styles */
        .metric-card { background-color: #1E1E1E; padding: 20px; border-radius: 10px; margin: 10px 0; border: 1px solid #333; }
        .metric-card h3 { margin: 10px 0 5px 0; font-size: 2em; }
        .metric-card p { margin: 0; color: #888; }
        
        /* Fix button spacing in columns */
        div[data-testid="column"] button { width: 100%; }

        /* Page Transition Animations */
        @keyframes slideInRight {
            from { opacity: 0; transform: translateX(30px); }
            to { opacity: 1; transform: translateX(0); }
        }
        @keyframes slideInLeft {
            from { opacity: 0; transform: translateX(-30px); }
            to { opacity: 1; transform: translateX(0); }
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .page-content {
            animation: fadeIn 0.4s ease-out forwards;
        }

        /* Loading Overlay */
        .loading-overlay { 
            position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
            background-color: rgba(15, 15, 15, 0.95); 
            display: flex; justify-content: center; align-items: center; 
            z-index: 9999; 
        }
        .loading-spinner { 
            border: 4px solid #333; border-top: 4px solid #4CAF50; 
            border-radius: 50%; width: 60px; height: 60px; 
            animation: spin 1s linear infinite; 
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
""", unsafe_allow_html=True)

# --- FULL TRANSLATION DICTIONARY (11 LANGUAGES) ---
T = {
    "en": {
        "onboarding_title": "Welcome to Hunti AI Solutions", "onboarding_subtitle": "Let's personalize your automation dashboard in just a few seconds.",
        "q1_lang": "Select your preferred language", "q2_business": "What best describes your business?", "q3_team": "What's your team size?", "q4_goal": "What's your main automation goal?",
        "btn_start": "Generate My Dashboard",
        "lang_en": "English", "lang_hu": "Hungarian (Magyar)", "lang_es": "Spanish (Español)", "lang_fr": "French (Français)", "lang_de": "German (Deutsch)", "lang_it": "Italian (Italiano)", "lang_pt": "Portuguese (Português)", "lang_ru": "Russian (Русский)", "lang_zh": "Chinese (中文)", "lang_ja": "Japanese (日本語)", "lang_ar": "Arabic (العربية)",
        "biz_small": "Small Business Owner", "biz_agency": "Agency Owner", "biz_ecom": "E-commerce", "biz_freelance": "Freelancer / Solopreneur",
        "team_1": "Just me (Solo)", "team_2": "2-5 employees", "team_3": "6-20 employees", "team_4": "20+ employees",
        "goal_leads": "Generate more leads", "goal_support": "Improve customer support", "goal_admin": "Automate admin tasks", "goal_sales": "Streamline sales process",
        "nav_hunti": "Hunti AI", "nav_analytics": "Analytics Dashboard", "nav_pitches": "Pitch Emailer", "sidebar_title": "User Profile", "reset_prefs": "Reset Preferences",
        "total_req": "Total Requests", "req_hour": "Requests (Last Hour)",
        "hunti_title": "Hunti AI - Your Intelligent Sales Consultant", "hunti_welcome": "Welcome! I'm here to help you automate your business and save time.", "hunti_sub": "Tell me about your challenges, and I'll show you how AI can solve them.", "hunti_input": "What challenge are you facing?",
        "analytics_title": "Analytics Dashboard", "analytics_sub": "Real-time performance metrics for your automation campaigns.",
        "total_leads": "Total Leads", "pitches_gen": "Pitches Generated", "emails_sent": "Emails Sent", "forms_sub": "Forms Submitted", "activity_overview": "Activity Overview", "email_status": "Email Delivery Status", "recent_activity": "Recent Activity Log", "db_records": "Database Records",
        "pitch_title": "Automated Pitch Emailer", "pitch_sub": "Generate and send personalized sales pitches to your leads automatically.", "pitch_info": "How it works: Upload your leads, and Hunti will generate personalized AI-powered pitches for each one.",
        "avail_leads": "Available Leads", "btn_gen_pitch": "Generate Pitches", "btn_view_pitch": "View Generated Pitches", "success_gen": "Successfully generated pitches!", "no_leads": "No leads found. Upload a file first!", "no_pitches": "No pitches generated yet.",
        "footer": "2026 Hunti AI Solutions. All rights reserved.", "loading": "Loading...", "generating_dashboard": "Generating your personalized dashboard...", "generating": "Generating...",
        "suggestions": {
            "Small Business Owner": ["I'm drowning in emails", "My team wastes hours on manual tasks", "I need to generate more leads", "I want to automate customer follow-ups"],
            "Agency Owner": ["My team spends too much time on onboarding", "We need to automate proposals", "I want to streamline client reporting", "We struggle to manage client communications"],
            "E-commerce": ["I need to automate order confirmations", "Customers keep asking the same questions", "I want to automate inventory updates", "I need better ways to collect reviews"],
            "Freelancer / Solopreneur": ["I spend too much time on admin", "I need to automate client discovery", "I want to automate invoicing", "I need help finding new clients"]
        }
    },
    "hu": {
        "onboarding_title": "Üdvözöljük a Hunti AI Solutions-nél", "onboarding_subtitle": "Személyre szabjuk az irányítópultját néhány másodperc alatt.",
        "q1_lang": "Válassza ki a nyelvet", "q2_business": "Mi írja le legjobban a vállalkozását?", "q3_team": "Mekkora a csapatméret?", "q4_goal": "Mi a fő automatizálási célja?",
        "btn_start": "Irányítópult Generálása",
        "lang_en": "Angol (English)", "lang_hu": "Magyar", "lang_es": "Spanyol", "lang_fr": "Francia", "lang_de": "Német", "lang_it": "Olasz", "lang_pt": "Portugál", "lang_ru": "Orosz", "lang_zh": "Kínai", "lang_ja": "Japán", "lang_ar": "Arab",
        "biz_small": "Kisvállalkozás Tulajdonos", "biz_agency": "Ügynökség Tulajdonos", "biz_ecom": "E-kereskedelem", "biz_freelance": "Szabadúszó",
        "team_1": "Egyedül vagyok", "team_2": "2-5 alkalmazott", "team_3": "6-20 alkalmazott", "team_4": "20+ alkalmazott",
        "goal_leads": "Több lead generálása", "goal_support": "Ügyféltámogatás javítása", "goal_admin": "Admin feladatok automatizálása", "goal_sales": "Értékesítés egyszerűsítése",
        "nav_hunti": "Hunti AI", "nav_analytics": "Analitika", "nav_pitches": "Pitch Küldő", "sidebar_title": "Profil", "reset_prefs": "Beállítások visszaállítása",
        "total_req": "Összes kérés", "req_hour": "Kérések (óra)",
        "hunti_title": "Hunti AI - Intelligens Tanácsadó", "hunti_welcome": "Üdvözöljük! Segítek automatizálni a vállalkozását.", "hunti_sub": "Meséljen a kihívásairól, és megmutatom, hogyan oldhatja meg őket az AI.", "hunti_input": "Milyen kihívással néz szembe?",
        "analytics_title": "Analitikai Irányítópult", "analytics_sub": "Valós idejű teljesítménymutatók.",
        "total_leads": "Összes Lead", "pitches_gen": "Generált Pitch-ek", "emails_sent": "Elküldött Emailek", "forms_sub": "Kitöltött Űrlapok", "activity_overview": "Tevékenység", "email_status": "Email Státusz", "recent_activity": "Legutóbbi Aktivitás", "db_records": "Adatbázis",
        "pitch_title": "Automatizált Pitch Küldő", "pitch_sub": "Generáljon és küldjön pitch-eket automatikusan.", "pitch_info": "Hogyan működik: Töltse fel leadjeit, és a Hunti személyre szabott, AI-alapú pitch-eket generál mindegyikhez.",
        "avail_leads": "Elérhető Lead-ek", "btn_gen_pitch": "Pitch-ek Generálása", "btn_view_pitch": "Megtekintés", "success_gen": "Sikeresen generálva!", "no_leads": "Nincs lead! Töltsön fel egy fájlt!", "no_pitches": "Nincs pitch.",
        "footer": "2026 Hunti AI Solutions.", "loading": "Betöltés...", "generating_dashboard": "Irányítópult generálása...", "generating": "Generálás...",
        "suggestions": {
            "Kisvállalkozás Tulajdonos": ["Elnyomnak az emailek", "A csapatom órákat pazarol", "Több lead kell", "Automatizálni akarom a követést"],
            "Ügynökség Tulajdonos": ["Túl sok idő az onboarding", "Automatizálnunk kell az ajánlatokat", "Jelentések egyszerűsítése", "Kliens kommunikáció kezelése"],
            "E-kereskedelem": ["Rendelés visszaigazolás automatizálása", "Ismétlődő kérdések", "Készlet automatizálás", "Vélemények gyűjtése"],
            "Szabadúszó": ["Túl sok admin", "Kliens keresés automatizálása", "Számlázás automatizálása", "Új ügyfelek keresése"]
        }
    },
    "es": {
        "onboarding_title": "Bienvenido a Hunti AI Solutions", "onboarding_subtitle": "Personalicemos su panel en unos segundos.",
        "q1_lang": "Seleccione su idioma", "q2_business": "¿Qué describe mejor su negocio?", "q3_team": "¿Tamaño de su equipo?", "q4_goal": "¿Objetivo principal de automatización?",
        "btn_start": "Generar Mi Panel",
        "lang_en": "Inglés", "lang_hu": "Húngaro", "lang_es": "Español", "lang_fr": "Francés", "lang_de": "Alemán", "lang_it": "Italiano", "lang_pt": "Portugués", "lang_ru": "Ruso", "lang_zh": "Chino", "lang_ja": "Japonés", "lang_ar": "Árabe",
        "biz_small": "Pequeña Empresa", "biz_agency": "Agencia", "biz_ecom": "E-commerce", "biz_freelance": "Autónomo",
        "team_1": "Solo yo", "team_2": "2-5 empleados", "team_3": "6-20 empleados", "team_4": "20+ empleados",
        "goal_leads": "Generar más leads", "goal_support": "Mejorar soporte", "goal_admin": "Automatizar admin", "goal_sales": "Optimizar ventas",
        "nav_hunti": "Hunti AI", "nav_analytics": "Análisis", "nav_pitches": "Emailer", "sidebar_title": "Perfil", "reset_prefs": "Restablecer",
        "total_req": "Total Solicitudes", "req_hour": "Solicitudes (Hora)",
        "hunti_title": "Hunti AI - Consultor Inteligente", "hunti_welcome": "¡Bienvenido! Estoy aquí para ayudarle.", "hunti_sub": "Cuénteme sus desafíos.", "hunti_input": "¿Qué desafío enfrenta?",
        "analytics_title": "Panel de Análisis", "analytics_sub": "Métricas en tiempo real.",
        "total_leads": "Total Leads", "pitches_gen": "Propuestas", "emails_sent": "Emails", "forms_sub": "Formularios", "activity_overview": "Actividad", "email_status": "Estado Emails", "recent_activity": "Actividad Reciente", "db_records": "Registros",
        "pitch_title": "Emailer de Propuestas", "pitch_sub": "Genere y envíe propuestas automáticamente.", "pitch_info": "Cómo funciona: Suba sus leads y Hunti generará propuestas personalizadas con IA para cada uno.",
        "avail_leads": "Leads Disponibles", "btn_gen_pitch": "Generar", "btn_view_pitch": "Ver", "success_gen": "¡Generado!", "no_leads": "¡Sin leads! Suba un archivo primero.", "no_pitches": "Sin propuestas.",
        "footer": "2026 Hunti AI Solutions.", "loading": "Cargando...", "generating_dashboard": "Generando panel...", "generating": "Generando...",
        "suggestions": {
            "Pequeña Empresa": ["Me ahogo en emails", "Mi equipo pierde horas", "Necesito más leads", "Automatizar seguimiento"],
            "Agencia": ["Mucho tiempo en onboarding", "Automatizar propuestas", "Optimizar informes", "Gestionar comunicaciones"],
            "E-commerce": ["Automatizar confirmaciones", "Mismas preguntas", "Actualizar inventario", "Recopilar reseñas"],
            "Autónomo": ["Demasiada administración", "Automatizar descubrimiento", "Automatizar facturación", "Encontrar clientes"]
        }
    }
    # Note: Other languages (fr, de, it, pt, ru, zh, ja, ar) are kept identical to previous structure for brevity, 
    # but ensure you keep the full dictionary from your previous code here!
}

# --- SESSION STATE ---
if 'onboarding_complete' not in st.session_state: st.session_state.onboarding_complete = False
if 'language' not in st.session_state: st.session_state.language = 'en'
if 'business_type' not in st.session_state: st.session_state.business_type = 'Small Business Owner'
if 'team_size' not in st.session_state: st.session_state.team_size = 'Just me (Solo)'
if 'automation_goal' not in st.session_state: st.session_state.automation_goal = 'Generate more leads'
if 'chat_history' not in st.session_state: st.session_state.chat_history = []
if 'user_id' not in st.session_state: st.session_state.user_id = f"user_{int(datetime.now().timestamp())}_{random.randint(1000, 9999)}"
if 'page' not in st.session_state: st.session_state.page = "Hunti AI"
if 'dashboard_generating' not in st.session_state: st.session_state.dashboard_generating = False

DB_NAME = "hunti.db"

def t(key):
    """Safe translation helper"""
    keys = key.split('.')
    val = T.get(st.session_state.language, T["en"])
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k, key)
        else:
            return key
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
        elif "status, COUNT(*) as count FROM emails GROUP BY status" in query: return pd.DataFrame({'status': ['sent', 'failed', 'pending'], 'count': [28, 2, 2]})
        elif "recipient_email, subject, sent_at FROM emails ORDER BY sent_at DESC LIMIT 5" in query: return pd.DataFrame({'recipient_email': ['contact@acme.com', 'info@techsol.com'], 'subject': ['AI Partnership', 'Workflow Demo'], 'sent_at': ['2024-01-15', '2024-01-14']})
        elif "SELECT * FROM leads ORDER BY created_at DESC" in query: return pd.DataFrame({'id': [1, 2], 'company_name': ['Acme Corp', 'Tech Solutions'], 'website': ['acme.com', 'techsol.com'], 'rating': [4.5, 3.8], 'created_at': ['2024-01-15', '2024-01-14']})
        elif "SELECT * FROM pitches ORDER BY created_at DESC" in query: return pd.DataFrame({'id': [1, 2], 'lead_id': [1, 2], 'pitch_text': ['Pitch for Acme...', 'Pitch for Tech...'], 'created_at': ['2024-01-15', '2024-01-14']})
        elif "SELECT * FROM emails ORDER BY sent_at DESC" in query: return pd.DataFrame({'id': [1], 'pitch_id': [1], 'recipient_email': ['contact@acme.com'], 'subject': ['AI Partnership'], 'status': ['sent'], 'sent_at': ['2024-01-15']})
        elif "SELECT * FROM form_submissions ORDER BY submitted_at DESC" in query: return pd.DataFrame({'id': [1, 2], 'company_name': ['Acme Corp', 'Global Logistics'], 'url': ['acme.com/contact', 'globallog.com/contact'], 'status': ['success', 'success'], 'submitted_at': ['2024-01-15', '2024-01-14']})
    
    try:
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()

# --- DASHBOARD GENERATION LOADING SCREEN ---
if st.session_state.dashboard_generating:
    st.markdown("""
        <div class="loading-overlay">
            <div style="text-align: center;">
                <div class="loading-spinner"></div>
                <p style="color: white; margin-top: 20px; font-size: 20px; font-weight: 600;">""" + t("generating_dashboard") + """</p>
                <p style="color: #aaa; margin-top: 10px;">Setting up your personalized experience...</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    st.session_state.dashboard_generating = False
    st.rerun()

# --- ONBOARDING PAGE ---
if not st.session_state.onboarding_complete:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title(t("onboarding_title"))
        st.markdown(f"*{t('onboarding_subtitle')}*")
        st.divider()
        
        if 'temp_lang' not in st.session_state: st.session_state.temp_lang = 'en'
        if 'temp_business' not in st.session_state: st.session_state.temp_business = 'Small Business Owner'
        if 'temp_team' not in st.session_state: st.session_state.temp_team = 'Just me (Solo)'
        if 'temp_goal' not in st.session_state: st.session_state.temp_goal = 'Generate more leads'
        
        st.markdown(f"**{t('q1_lang')}**")
        lang_options = {"English": "en", "Magyar": "hu", "Español": "es", "Français": "fr", "Deutsch": "de", "Italiano": "it", "Português": "pt", "Русский": "ru", "中文": "zh", "日本語": "ja", "العربية": "ar"}
        
        selected_lang_name = st.selectbox("Language", list(lang_options.keys()), index=list(lang_options.keys()).index("Magyar") if st.session_state.temp_lang == 'hu' else list(lang_options.keys()).index("Español") if st.session_state.temp_lang == 'es' else 0, key="onboarding_lang", label_visibility="collapsed")
        st.session_state.temp_lang = lang_options[selected_lang_name]
        st.session_state.language = st.session_state.temp_lang
        
        st.markdown(f"**{t('q2_business')}**")
        biz_options_en = ["Small Business Owner", "Agency Owner", "E-commerce", "Freelancer / Solopreneur"]
        biz_options_hu = ["Kisvállalkozás Tulajdonos", "Ügynökség Tulajdonos", "E-kereskedelem", "Szabadúszó"]
        biz_options_es = ["Pequeña Empresa", "Agencia", "E-commerce", "Autónomo"]
        biz_options_fr = ["Petite Entreprise", "Agence", "E-commerce", "Indépendant"]
        biz_options_de = ["Kleinunternehmer", "Agentur", "E-Commerce", "Freiberufler"]
        biz_options_it = ["Piccola Impresa", "Agenzia", "E-commerce", "Freelance"]
        biz_options_pt = ["Pequena Empresa", "Agência", "E-commerce", "Autônomo"]
        biz_options_ru = ["Малый бизнес", "Агентство", "E-commerce", "Фрилансер"]
        biz_options_zh = ["小企业主", "代理机构", "电子商务", "自由职业者"]
        biz_options_ja = ["小規模事業", "エージェンシー", "Eコマース", "フリーランス"]
        biz_options_ar = ["عمل صغير", "وكالة", "تجارة إلكترونية", "مستقل"]
        
        lang_to_biz = {'hu': biz_options_hu, 'es': biz_options_es, 'fr': biz_options_fr, 'de': biz_options_de, 'it': biz_options_it, 'pt': biz_options_pt, 'ru': biz_options_ru, 'zh': biz_options_zh, 'ja': biz_options_ja, 'ar': biz_options_ar}
        biz_options = lang_to_biz.get(st.session_state.language, biz_options_en)
        
        selected_biz = st.selectbox("Business Type", biz_options, index=0, key="onboarding_biz", label_visibility="collapsed")
        st.session_state.temp_business = selected_biz
        
        st.markdown(f"**{t('q3_team')}**")
        team_options = [t("team_1"), t("team_2"), t("team_3"), t("team_4")]
        selected_team = st.selectbox("Team Size", team_options, index=0, key="onboarding_team", label_visibility="collapsed")
        st.session_state.temp_team = selected_team
        
        st.markdown(f"**{t('q4_goal')}**")
        goal_options = [t("goal_leads"), t("goal_support"), t("goal_admin"), t("goal_sales")]
        selected_goal = st.selectbox("Automation Goal", goal_options, index=0, key="onboarding_goal", label_visibility="collapsed")
        st.session_state.temp_goal = selected_goal
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button(t("btn_start"), type="primary", use_container_width=True, key="btn_onboard"):
            st.session_state.language = st.session_state.temp_lang
            st.session_state.business_type = st.session_state.temp_business
            st.session_state.team_size = st.session_state.temp_team
            st.session_state.automation_goal = st.session_state.temp_goal
            st.session_state.onboarding_complete = True
            st.session_state.dashboard_generating = True
            if 'temp_lang' in st.session_state: del st.session_state.temp_lang
            if 'temp_business' in st.session_state: del st.session_state.temp_business
            if 'temp_team' in st.session_state: del st.session_state.temp_team
            if 'temp_goal' in st.session_state: del st.session_state.temp_goal
            st.rerun()
    st.stop()

# --- RELIABLE NAVIGATION (Fixes Double-Click & Highlighting) ---
def set_page(page_name):
    st.session_state.page = page_name

col_nav1, col_nav2, col_nav3 = st.columns(3)

with col_nav1:
    is_active = st.session_state.page == "Hunti AI"
    st.button(
        t("nav_hunti"), 
        use_container_width=True, 
        type="primary" if is_active else "secondary",
        on_click=set_page, 
        args=("Hunti AI",)
    )

with col_nav2:
    is_active = st.session_state.page == "Analytics"
    st.button(
        t("nav_analytics"), 
        use_container_width=True, 
        type="primary" if is_active else "secondary",
        on_click=set_page, 
        args=("Analytics",)
    )

with col_nav3:
    is_active = st.session_state.page == "Pitch Emailer"
    st.button(
        t("nav_pitches"), 
        use_container_width=True, 
        type="primary" if is_active else "secondary",
        on_click=set_page, 
        args=("Pitch Emailer",)
    )

st.divider()

# --- MAIN CONTENT WRAPPER WITH ANIMATION ---
st.markdown('<div class="page-content">', unsafe_allow_html=True)

with st.sidebar:
    st.title(t("sidebar_title"))
    st.write(f"**Business Type:** {st.session_state.business_type}")
    st.write(f"**Team Size:** {st.session_state.team_size}")
    st.write(f"**Goal:** {st.session_state.automation_goal}")
    st.write(f"User ID: `{st.session_state.user_id}`")
    
    if st.button(t("reset_prefs"), use_container_width=True, key="btn_reset"):
        st.session_state.onboarding_complete = False
        st.session_state.chat_history = []
        st.session_state.language = 'en'
        st.session_state.business_type = 'Small Business Owner'
        st.session_state.team_size = 'Just me (Solo)'
        st.session_state.automation_goal = 'Generate more leads'
        st.session_state.page = "Hunti AI"
        st.rerun()
    
    st.divider()
    try:
        stats = get_usage_stats(st.session_state.user_id)
        st.metric(t("total_req"), stats['total_requests'])
        st.metric(t("req_hour"), stats['requests_last_hour'], delta="Limit: 10/hour")
    except: pass
    
    st.divider()
    st.caption("Hunti AI Solutions")

# --- PAGE CONTENT ---
if st.session_state.page == "Hunti AI":
    st.title(t("hunti_title"))
    st.markdown(t("hunti_welcome"))
    st.markdown(f"*{t('hunti_sub')}*")
    st.divider()
    
    if st.session_state.business_type:
        st.subheader(f"Common Challenges for {st.session_state.business_type}")
        cols = st.columns(2)
        
        suggestions = t(f"suggestions.{st.session_state.business_type}")
        if not isinstance(suggestions, list):
            suggestions = T["en"]["suggestions"].get(st.session_state.business_type, ["Challenge 1", "Challenge 2", "Challenge 3", "Challenge 4"])
            
        for i, text in enumerate(suggestions):
            with cols[i % 2]:
                if st.button(text, key=f"sugg_{i}", use_container_width=True):
                    st.session_state.suggested_prompt = text
                    st.rerun()
        st.divider()
    
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]): st.markdown(message["content"])
    
    prompt = st.chat_input(t("hunti_input"))
    
    if hasattr(st.session_state, 'suggested_prompt') and st.session_state.suggested_prompt:
        prompt = st.session_state.suggested_prompt
        del st.session_state.suggested_prompt
    
    if prompt:
        allowed, message = check_rate_limit(st.session_state.user_id, action="chat", max_requests=10, window_minutes=60)
        if not allowed: st.error(message); st.stop()
        
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
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
        else: st.info("No email data yet.")
    
    with col_chart2:
        st.markdown(f"#### {t('recent_activity')}")
        recent_emails = get_data("SELECT recipient_email, subject, sent_at FROM emails ORDER BY sent_at DESC LIMIT 5")
        if not recent_emails.empty: st.dataframe(recent_emails, hide_index=True, use_container_width=True)
        else: st.info("No recent emails found.")

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
    
    # Tutorial Section
    with st.expander("📖 How to Use - Click to Expand Tutorial", expanded=True):
        st.markdown(f"""
        ### Welcome to the Pitch Emailer!
        
        This tool generates personalized AI-powered sales pitches for your leads. Follow these steps:
        
        **Step 1: Upload Your Leads**
        - Upload a CSV or JSON file with your lead information
        - Required column: `company_name` (optional: `website`, `address`, `phone`, `rating`)
        - [Download Sample CSV](data:text/csv;base64,Y29tcGFueV9uYW1lLHdlYnNpdGUsYWRkcmVzcyxwaG9uZSxyYXRpbmcKQWNtZSBDb3JwLGFjbWUuY29tLCIxMjMgSW5ub3ZhdGlvbiBEciwgVGVjaCBDaXR5Iiw1NTUtMDEwMCw0LjUKVGVjaCBTb2x1dGlvbnMsdGVjaHNvbC5jb20sIjQ1NiBTaWxpY29uIEF2ZSwgU3RhcnR1cCBWYWxsZXkiLDU1NS0wMTAxLDMuOApHbG9iYWwgTG9naXN0aWNzLGdsb2JhbGxvZy5jb20sIjc4OSBTdXBwbHkgQ2hhaW4gQmx2ZCwgQ29tbWVyY2UgQ2l0eSIsNTU1LTAxMDIsNC4yCg==) to get started
        
        **Step 2: Generate Pitches**
        - Click "Generate Pitches" to create personalized AI-powered sales emails
        - Each pitch is customized based on the company's website and industry
        
        **Step 3: View & Use**
        - Review the generated pitches
        - Copy them to use in your email campaigns
        - All pitches are saved for this session
        """)
    
    st.divider()
    
    # File Upload Section
    uploaded_file = st.file_uploader(
        "Upload your leads file (CSV or JSON)",
        type=["csv", "json"],
        help="Upload a CSV or JSON file with your lead information"
    )
    
    if uploaded_file is not None:
        try:
            # Read the uploaded file
            if uploaded_file.name.endswith('.csv'):
                leads_df = pd.read_csv(uploaded_file)
            else:
                leads_df = pd.read_json(uploaded_file)
            
            # Validate required columns
            if 'company_name' not in leads_df.columns:
                st.error("❌ Error: File must contain a 'company_name' column")
                st.stop()
            
            # Add missing optional columns with defaults
            if 'website' not in leads_df.columns:
                leads_df['website'] = ''
            if 'address' not in leads_df.columns:
                leads_df['address'] = ''
            if 'phone' not in leads_df.columns:
                leads_df['phone'] = ''
            if 'rating' not in leads_df.columns:
                leads_df['rating'] = 0.0
            
            st.success(f"✅ Loaded {len(leads_df)} leads successfully!")
            
            # Display uploaded leads
            st.subheader(t("avail_leads"))
            st.dataframe(leads_df, use_container_width=True)
            
            st.divider()
            
            # Initialize session state for generated pitches
            if 'uploaded_pitches' not in st.session_state:
                st.session_state.uploaded_pitches = []
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button(t("btn_gen_pitch"), type="primary", use_container_width=True, key="btn_generate_pitches"):
                    with st.spinner(t("generating")):
                        try:
                            # Convert dataframe to list of dicts
                            leads_list = leads_df.to_dict('records')
                            
                            # Generate pitches using brain.py
                            client = init_groq_client()
                            
                            pitches = []
                            for lead in leads_list:
                                try:
                                    pitch_text = generate_pitch(client, lead)
                                    pitches.append({
                                        "company": lead.get('company_name', 'Unknown'),
                                        "pitch": pitch_text
                                    })
                                except Exception as e:
                                    st.warning(f"⚠️ Could not generate pitch for {lead.get('company_name', 'Unknown')}: {str(e)}")
                            
                            st.session_state.uploaded_pitches = pitches
                            st.success(f"✅ {t('success_gen')} ({len(pitches)})")
                            st.balloons()
                        except Exception as e:
                            st.error(f"Error generating pitches: {str(e)}")
            
            with col2:
                if st.button(t("btn_view_pitch"), use_container_width=True, key="btn_view_pitches"):
                    if st.session_state.uploaded_pitches:
                        st.subheader("Generated Pitches")
                        for item in st.session_state.uploaded_pitches:
                            st.markdown(f"**{item['company']}**")
                            st.text_area(
                                "Pitch", 
                                item['pitch'], 
                                height=200, 
                                key=f"pitch_{item['company']}", 
                                disabled=True,
                                label_visibility="collapsed"
                            )
                            st.divider()
                        
                        # Download button
                        pitches_json = json.dumps(st.session_state.uploaded_pitches, indent=2)
                        st.download_button(
                            label="📥 Download Pitches as JSON",
                            data=pitches_json,
                            file_name="generated_pitches.json",
                            mime="application/json",
                            use_container_width=True
                        )
                    else:
                        st.info("💡 Click 'Generate Pitches' to create personalized pitches for your uploaded leads.")
        except Exception as e:
            st.error(f"❌ Error reading file: {str(e)}")
            st.info("💡 Make sure your file is a valid CSV or JSON format")
    else:
        # Show sample when no file uploaded
        st.info("📄 **No file uploaded yet.** Upload a CSV or JSON file above to get started, or download the sample file to see the expected format.")
        
        # Show sample structure
        st.subheader("Expected File Format")
        st.markdown("""
        Your file should include at minimum:
        - **company_name** (required)
        - **website** (recommended)
        
        Optional columns:
        - address
        - phone
        - rating
        """)
        
        sample_df = pd.DataFrame({
            'company_name': ['Acme Corp', 'Tech Solutions'],
            'website': ['acme.com', 'techsol.com'],
            'address': ['123 Innovation Dr', '456 Silicon Ave'],
            'phone': ['555-0100', '555-0101'],
            'rating': [4.5, 3.8]
        })
        st.dataframe(sample_df, use_container_width=True)

st.markdown('</div>', unsafe_allow_html=True)

st.divider()
st.markdown(t("footer"))