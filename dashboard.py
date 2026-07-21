import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime
import os
import random

from brain import ask_assistant, build_pitches, get_pitches_from_db
from rate_limiter import check_rate_limit, get_usage_stats

st.set_page_config(page_title="Hunti AI - Command Center", page_icon="🤖", layout="wide")

# --- CSS ---
st.markdown("""
    <style>
        .metric-card { background-color: #1E1E1E; padding: 20px; border-radius: 10px; margin: 10px 0; border: 1px solid #333; }
        .metric-card h3 { margin: 10px 0 5px 0; font-size: 2em; }
        .metric-card p { margin: 0; color: #888; }
        .stButton>button { transition: all 0.2s; }
        .stButton>button:active { transform: scale(0.98); }
        .loading-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0, 0, 0, 0.9); display: flex; justify-content: center; align-items: center; z-index: 9999; }
        .loading-spinner { border: 4px solid #f3f3f3; border-top: 4px solid #4CAF50; border-radius: 50%; width: 60px; height: 60px; animation: spin 1s linear infinite; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
""", unsafe_allow_html=True)

# --- FULL TRANSLATION DICTIONARY ---
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
        "pitch_title": "Automated Pitch Emailer", "pitch_sub": "Generate and send personalized sales pitches to your leads automatically.", "pitch_info": "How it works: Select leads from your database, and Hunti will generate personalized pitches and send them via email.",
        "avail_leads": "Available Leads", "btn_gen_pitch": "Generate Pitches", "btn_view_pitch": "View Generated Pitches", "success_gen": "Successfully generated pitches!", "no_leads": "No leads found. Add some leads first!", "no_pitches": "No pitches generated yet.",
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
        "pitch_title": "Automatizált Pitch Küldő", "pitch_sub": "Generáljon és küldjön pitch-eket automatikusan.", "pitch_info": "Válasszon lead-eket, és a Hunti elküldi a pitch-eket.",
        "avail_leads": "Elérhető Lead-ek", "btn_gen_pitch": "Pitch-ek Generálása", "btn_view_pitch": "Megtekintés", "success_gen": "Sikeresen generálva!", "no_leads": "Nincs lead!", "no_pitches": "Nincs pitch.",
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
        "pitch_title": "Emailer de Propuestas", "pitch_sub": "Genere y envíe propuestas automáticamente.", "pitch_info": "Seleccione leads y Hunti enviará las propuestas.",
        "avail_leads": "Leads Disponibles", "btn_gen_pitch": "Generar", "btn_view_pitch": "Ver", "success_gen": "¡Generado!", "no_leads": "¡Sin leads!", "no_pitches": "Sin propuestas.",
        "footer": "2026 Hunti AI Solutions.", "loading": "Cargando...", "generating_dashboard": "Generando panel...", "generating": "Generando...",
        "suggestions": {
            "Pequeña Empresa": ["Me ahogo en emails", "Mi equipo pierde horas", "Necesito más leads", "Automatizar seguimiento"],
            "Agencia": ["Mucho tiempo en onboarding", "Automatizar propuestas", "Optimizar informes", "Gestionar comunicaciones"],
            "E-commerce": ["Automatizar confirmaciones", "Mismas preguntas", "Actualizar inventario", "Recopilar reseñas"],
            "Autónomo": ["Demasiada administración", "Automatizar descubrimiento", "Automatizar facturación", "Encontrar clientes"]
        }
    },
    "fr": {
        "onboarding_title": "Bienvenue chez Hunti AI Solutions", "onboarding_subtitle": "Personnalisons votre tableau de bord.",
        "q1_lang": "Sélectionnez votre langue", "q2_business": "Qu'est-ce qui décrit votre entreprise?", "q3_team": "Taille de l'équipe?", "q4_goal": "Objectif d'automatisation?",
        "btn_start": "Générer Mon Tableau",
        "lang_en": "Anglais", "lang_hu": "Hongrois", "lang_es": "Espagnol", "lang_fr": "Français", "lang_de": "Allemand", "lang_it": "Italien", "lang_pt": "Portugais", "lang_ru": "Russe", "lang_zh": "Chinois", "lang_ja": "Japonais", "lang_ar": "Arabe",
        "biz_small": "Petite Entreprise", "biz_agency": "Agence", "biz_ecom": "E-commerce", "biz_freelance": "Indépendant",
        "team_1": "Seul", "team_2": "2-5 employés", "team_3": "6-20 employés", "team_4": "20+ employés",
        "goal_leads": "Générer des leads", "goal_support": "Améliorer le support", "goal_admin": "Automatiser l'admin", "goal_sales": "Optimiser les ventes",
        "nav_hunti": "Hunti AI", "nav_analytics": "Analytique", "nav_pitches": "Emailer", "sidebar_title": "Profil", "reset_prefs": "Réinitialiser",
        "total_req": "Total Demandes", "req_hour": "Demandes (Heure)",
        "hunti_title": "Hunti AI - Consultant Intelligent", "hunti_welcome": "Bienvenue! Je suis là pour aider.", "hunti_sub": "Parlez-moi de vos défis.", "hunti_input": "Quel défi rencontrez-vous?",
        "analytics_title": "Tableau Analytique", "analytics_sub": "Métriques en temps réel.",
        "total_leads": "Total Leads", "pitches_gen": "Propositions", "emails_sent": "Emails", "forms_sub": "Formulaires", "activity_overview": "Activité", "email_status": "Statut Emails", "recent_activity": "Activité Récente", "db_records": "Enregistrements",
        "pitch_title": "Emailer de Propositions", "pitch_sub": "Générez et envoyez automatiquement.", "pitch_info": "Sélectionnez les leads et Hunti enverra.",
        "avail_leads": "Leads Disponibles", "btn_gen_pitch": "Générer", "btn_view_pitch": "Voir", "success_gen": "Généré!", "no_leads": "Pas de leads!", "no_pitches": "Pas de propositions.",
        "footer": "2026 Hunti AI Solutions.", "loading": "Chargement...", "generating_dashboard": "Génération...", "generating": "Génération...",
        "suggestions": {
            "Petite Entreprise": ["Je suis submergé d'emails", "Mon équipe perd des heures", "J'ai besoin de leads", "Automatiser le suivi"],
            "Agence": ["Trop de temps en onboarding", "Automatiser les propositions", "Optimiser les rapports", "Gérer les communications"],
            "E-commerce": ["Automatiser les confirmations", "Mêmes questions", "Mettre à jour l'inventaire", "Collecter les avis"],
            "Indépendant": ["Trop d'administration", "Automatiser la découverte", "Automatiser la facturation", "Trouver des clients"]
        }
    },
    "de": {
        "onboarding_title": "Willkommen bei Hunti AI Solutions", "onboarding_subtitle": "Lassen Sie uns Ihr Dashboard personalisieren.",
        "q1_lang": "Wählen Sie Ihre Sprache", "q2_business": "Was beschreibt Ihr Unternehmen?", "q3_team": "Teamgröße?", "q4_goal": "Automatisierungsziel?",
        "btn_start": "Dashboard Generieren",
        "lang_en": "Englisch", "lang_hu": "Ungarisch", "lang_es": "Spanisch", "lang_fr": "Französisch", "lang_de": "Deutsch", "lang_it": "Italienisch", "lang_pt": "Portugiesisch", "lang_ru": "Russisch", "lang_zh": "Chinesisch", "lang_ja": "Japanisch", "lang_ar": "Arabisch",
        "biz_small": "Kleinunternehmer", "biz_agency": "Agentur", "biz_ecom": "E-Commerce", "biz_freelance": "Freiberufler",
        "team_1": "Nur ich", "team_2": "2-5 Mitarbeiter", "team_3": "6-20 Mitarbeiter", "team_4": "20+ Mitarbeiter",
        "goal_leads": "Mehr Leads", "goal_support": "Support verbessern", "goal_admin": "Admin automatisieren", "goal_sales": "Verkäufe optimieren",
        "nav_hunti": "Hunti AI", "nav_analytics": "Analytik", "nav_pitches": "Emailer", "sidebar_title": "Profil", "reset_prefs": "Zurücksetzen",
        "total_req": "Gesamt Anfragen", "req_hour": "Anfragen (Stunde)",
        "hunti_title": "Hunti AI - Intelligenter Berater", "hunti_welcome": "Willkommen! Ich bin hier um zu helfen.", "hunti_sub": "Erzählen Sie mir von Ihren Herausforderungen.", "hunti_input": "Welche Herausforderung haben Sie?",
        "analytics_title": "Analyse-Dashboard", "analytics_sub": "Echtzeit-Metriken.",
        "total_leads": "Gesamt Leads", "pitches_gen": "Angebote", "emails_sent": "Emails", "forms_sub": "Formulare", "activity_overview": "Aktivität", "email_status": "Email Status", "recent_activity": "Letzte Aktivität", "db_records": "Datenbank",
        "pitch_title": "Automatisierter Emailer", "pitch_sub": "Generieren und senden Sie automatisch.", "pitch_info": "Wählen Sie Leads und Hunti sendet.",
        "avail_leads": "Verfügbare Leads", "btn_gen_pitch": "Generieren", "btn_view_pitch": "Ansehen", "success_gen": "Generiert!", "no_leads": "Keine Leads!", "no_pitches": "Keine Angebote.",
        "footer": "2026 Hunti AI Solutions.", "loading": "Laden...", "generating_dashboard": "Generierung...", "generating": "Generieren...",
        "suggestions": {
            "Kleinunternehmer": ["Ich ertrinke in Emails", "Team verschwendet Stunden", "Ich brauche Leads", "Follow-up automatisieren"],
            "Agentur": ["Zu viel Onboarding-Zeit", "Angebote automatisieren", "Berichte optimieren", "Kommunikation managen"],
            "E-Commerce": ["Bestellungen automatisieren", "Gleiche Fragen", "Inventar aktualisieren", "Bewertungen sammeln"],
            "Freiberufler": ["Zu viel Verwaltung", "Kundenfindung automatisieren", "Rechnung automatisieren", "Kunden finden"]
        }
    },
    "it": {
        "onboarding_title": "Benvenuto in Hunti AI Solutions", "onboarding_subtitle": "Personalizziamo la tua dashboard.",
        "q1_lang": "Seleziona la lingua", "q2_business": "Cosa descrive la tua attività?", "q3_team": "Dimensione del team?", "q4_goal": "Obiettivo automazione?",
        "btn_start": "Genera Dashboard",
        "lang_en": "Inglese", "lang_hu": "Ungherese", "lang_es": "Spagnolo", "lang_fr": "Francese", "lang_de": "Tedesco", "lang_it": "Italiano", "lang_pt": "Portoghese", "lang_ru": "Russo", "lang_zh": "Cinese", "lang_ja": "Giapponese", "lang_ar": "Arabo",
        "biz_small": "Piccola Impresa", "biz_agency": "Agenzia", "biz_ecom": "E-commerce", "biz_freelance": "Freelance",
        "team_1": "Solo io", "team_2": "2-5 dipendenti", "team_3": "6-20 dipendenti", "team_4": "20+ dipendenti",
        "goal_leads": "Più lead", "goal_support": "Migliorare supporto", "goal_admin": "Automatizzare admin", "goal_sales": "Ottimizzare vendite",
        "nav_hunti": "Hunti AI", "nav_analytics": "Analitica", "nav_pitches": "Emailer", "sidebar_title": "Profilo", "reset_prefs": "Reimposta",
        "total_req": "Totale Richieste", "req_hour": "Richieste (Ora)",
        "hunti_title": "Hunti AI - Consulente Intelligente", "hunti_welcome": "Benvenuto! Sono qui per aiutare.", "hunti_sub": "Parlami delle tue sfide.", "hunti_input": "Quale sfida stai affrontando?",
        "analytics_title": "Dashboard Analitica", "analytics_sub": "Metriche in tempo reale.",
        "total_leads": "Totale Lead", "pitches_gen": "Proposte", "emails_sent": "Email", "forms_sub": "Moduli", "activity_overview": "Attività", "email_status": "Stato Email", "recent_activity": "Attività Recente", "db_records": "Database",
        "pitch_title": "Emailer Automatico", "pitch_sub": "Genera e invia automaticamente.", "pitch_info": "Seleziona i lead e Hunti invierà.",
        "avail_leads": "Lead Disponibili", "btn_gen_pitch": "Genera", "btn_view_pitch": "Vedi", "success_gen": "Generato!", "no_leads": "Nessun lead!", "no_pitches": "Nessuna proposta.",
        "footer": "2026 Hunti AI Solutions.", "loading": "Caricamento...", "generating_dashboard": "Generazione...", "generating": "Generando...",
        "suggestions": {
            "Piccola Impresa": ["Sono sommerso da email", "Il team perde ore", "Ho bisogno di lead", "Automatizzare il follow-up"],
            "Agenzia": ["Troppo tempo in onboarding", "Automatizzare proposte", "Ottimizzare report", "Gestire comunicazioni"],
            "E-commerce": ["Automatizzare ordini", "Stesse domande", "Aggiornare inventario", "Raccogliere recensioni"],
            "Freelance": ["Troppa amministrazione", "Automatizzare scoperta", "Automatizzare fatture", "Trovare clienti"]
        }
    },
    "pt": {
        "onboarding_title": "Bem-vindo à Hunti AI Solutions", "onboarding_subtitle": "Vamos personalizar seu painel.",
        "q1_lang": "Selecione o idioma", "q2_business": "O que descreve seu negócio?", "q3_team": "Tamanho da equipe?", "q4_goal": "Objetivo de automação?",
        "btn_start": "Gerar Painel",
        "lang_en": "Inglês", "lang_hu": "Húngaro", "lang_es": "Espanhol", "lang_fr": "Francês", "lang_de": "Alemão", "lang_it": "Italiano", "lang_pt": "Português", "lang_ru": "Russo", "lang_zh": "Chinês", "lang_ja": "Japonês", "lang_ar": "Árabe",
        "biz_small": "Pequena Empresa", "biz_agency": "Agência", "biz_ecom": "E-commerce", "biz_freelance": "Autônomo",
        "team_1": "Só eu", "team_2": "2-5 funcionários", "team_3": "6-20 funcionários", "team_4": "20+ funcionários",
        "goal_leads": "Mais leads", "goal_support": "Melhorar suporte", "goal_admin": "Automatizar admin", "goal_sales": "Otimizar vendas",
        "nav_hunti": "Hunti AI", "nav_analytics": "Análise", "nav_pitches": "Emailer", "sidebar_title": "Perfil", "reset_prefs": "Redefinir",
        "total_req": "Total Solicitações", "req_hour": "Solicitações (Hora)",
        "hunti_title": "Hunti AI - Consultor Inteligente", "hunti_welcome": "Bem-vindo! Estou aqui para ajudar.", "hunti_sub": "Conte-me sobre seus desafios.", "hunti_input": "Qual desafio você enfrenta?",
        "analytics_title": "Painel de Análise", "analytics_sub": "Métricas em tempo real.",
        "total_leads": "Total Leads", "pitches_gen": "Propostas", "emails_sent": "Emails", "forms_sub": "Formulários", "activity_overview": "Atividade", "email_status": "Status Emails", "recent_activity": "Atividade Recente", "db_records": "Banco de Dados",
        "pitch_title": "Emailer Automático", "pitch_sub": "Gere e envie automaticamente.", "pitch_info": "Selecione leads e o Hunti enviará.",
        "avail_leads": "Leads Disponíveis", "btn_gen_pitch": "Gerar", "btn_view_pitch": "Ver", "success_gen": "Gerado!", "no_leads": "Sem leads!", "no_pitches": "Sem propostas.",
        "footer": "2026 Hunti AI Solutions.", "loading": "Carregando...", "generating_dashboard": "Gerando...", "generating": "Gerando...",
        "suggestions": {
            "Pequena Empresa": ["Estou afogado em emails", "Equipe perde horas", "Preciso de leads", "Automatizar acompanhamento"],
            "Agência": ["Muito tempo em onboarding", "Automatizar propostas", "Otimizar relatórios", "Gerenciar comunicações"],
            "E-commerce": ["Automatizar pedidos", "Mesmas perguntas", "Atualizar inventário", "Coletar avaliações"],
            "Autônomo": ["Muita administração", "Automatizar descoberta", "Automatizar faturamento", "Encontrar clientes"]
        }
    },
    "ru": {
        "onboarding_title": "Добро пожаловать в Hunti AI Solutions", "onboarding_subtitle": "Давайте персонализируем вашу панель.",
        "q1_lang": "Выберите язык", "q2_business": "Что описывает ваш бизнес?", "q3_team": "Размер команды?", "q4_goal": "Цель автоматизации?",
        "btn_start": "Создать Панель",
        "lang_en": "Английский", "lang_hu": "Венгерский", "lang_es": "Испанский", "lang_fr": "Французский", "lang_de": "Немецкий", "lang_it": "Итальянский", "lang_pt": "Португальский", "lang_ru": "Русский", "lang_zh": "Китайский", "lang_ja": "Японский", "lang_ar": "Арабский",
        "biz_small": "Малый бизнес", "biz_agency": "Агентство", "biz_ecom": "E-commerce", "biz_freelance": "Фрилансер",
        "team_1": "Только я", "team_2": "2-5 сотрудников", "team_3": "6-20 сотрудников", "team_4": "20+ сотрудников",
        "goal_leads": "Больше лидов", "goal_support": "Улучшить поддержку", "goal_admin": "Автоматизировать админ", "goal_sales": "Оптимизировать продажи",
        "nav_hunti": "Hunti AI", "nav_analytics": "Аналитика", "nav_pitches": "Emailer", "sidebar_title": "Профиль", "reset_prefs": "Сбросить",
        "total_req": "Всего запросов", "req_hour": "Запросы (час)",
        "hunti_title": "Hunti AI - Умный Консультант", "hunti_welcome": "Добро пожаловать! Я здесь, чтобы помочь.", "hunti_sub": "Расскажите о ваших проблемах.", "hunti_input": "С какой проблемой вы столкнулись?",
        "analytics_title": "Панель Аналитики", "analytics_sub": "Метрики в реальном времени.",
        "total_leads": "Всего лидов", "pitches_gen": "Предложения", "emails_sent": "Emails", "forms_sub": "Формы", "activity_overview": "Активность", "email_status": "Статус Email", "recent_activity": "Последняя Активность", "db_records": "База Данных",
        "pitch_title": "Автоматический Emailer", "pitch_sub": "Генерируйте и отправляйте автоматически.", "pitch_info": "Выберите лидов, и Hunti отправит.",
        "avail_leads": "Доступные лиды", "btn_gen_pitch": "Создать", "btn_view_pitch": "Смотреть", "success_gen": "Создано!", "no_leads": "Нет лидов!", "no_pitches": "Нет предложений.",
        "footer": "2026 Hunti AI Solutions.", "loading": "Загрузка...", "generating_dashboard": "Генерация...", "generating": "Генерация...",
        "suggestions": {
            "Малый бизнес": ["Я тону в письмах", "Команда тратит часы", "Мне нужны лиды", "Автоматизировать follow-up"],
            "Агентство": ["Много времени на онбординг", "Автоматизировать предложения", "Оптимизировать отчеты", "Управлять коммуникациями"],
            "E-commerce": ["Автоматизировать заказы", "Те же вопросы", "Обновлять инвентарь", "Собирать отзывы"],
            "Фрилансер": ["Много администрирования", "Автоматизировать поиск", "Автоматизировать счета", "Находить клиентов"]
        }
    },
    "zh": {
        "onboarding_title": "欢迎使用 Hunti AI Solutions", "onboarding_subtitle": "让我们个性化您的仪表板。",
        "q1_lang": "选择语言", "q2_business": "什么最能描述您的业务?", "q3_team": "团队规模?", "q4_goal": "自动化目标?",
        "btn_start": "生成仪表板",
        "lang_en": "英语", "lang_hu": "匈牙利语", "lang_es": "西班牙语", "lang_fr": "法语", "lang_de": "德语", "lang_it": "意大利语", "lang_pt": "葡萄牙语", "lang_ru": "俄语", "lang_zh": "中文", "lang_ja": "日语", "lang_ar": "阿拉伯语",
        "biz_small": "小企业主", "biz_agency": "代理机构", "biz_ecom": "电子商务", "biz_freelance": "自由职业者",
        "team_1": "只有我", "team_2": "2-5名员工", "team_3": "6-20名员工", "team_4": "20名以上员工",
        "goal_leads": "更多潜在客户", "goal_support": "改善支持", "goal_admin": "自动化行政", "goal_sales": "优化销售",
        "nav_hunti": "Hunti AI", "nav_analytics": "分析", "nav_pitches": "邮件发送器", "sidebar_title": "个人资料", "reset_prefs": "重置",
        "total_req": "总请求", "req_hour": "请求(小时)",
        "hunti_title": "Hunti AI - 智能顾问", "hunti_welcome": "欢迎!我来帮助您。", "hunti_sub": "告诉我您的挑战。", "hunti_input": "您面临什么挑战?",
        "analytics_title": "分析仪表板", "analytics_sub": "实时指标。",
        "total_leads": "总潜在客户", "pitches_gen": "提案", "emails_sent": "邮件", "forms_sub": "表单", "activity_overview": "活动", "email_status": "邮件状态", "recent_activity": "最近活动", "db_records": "数据库",
        "pitch_title": "自动邮件发送器", "pitch_sub": "自动生成并发送。", "pitch_info": "选择潜在客户,Hunti将发送。",
        "avail_leads": "可用潜在客户", "btn_gen_pitch": "生成", "btn_view_pitch": "查看", "success_gen": "已生成!", "no_leads": "无潜在客户!", "no_pitches": "无提案。",
        "footer": "2026 Hunti AI Solutions.", "loading": "加载中...", "generating_dashboard": "生成中...", "generating": "生成中...",
        "suggestions": {
            "小企业主": ["我淹没在邮件中", "团队浪费时间", "我需要潜在客户", "自动化跟进"],
            "代理机构": ["入职时间太多", "自动化提案", "优化报告", "管理沟通"],
            "电子商务": ["自动化订单", "相同问题", "更新库存", "收集评论"],
            "自由职业者": ["太多行政工作", "自动化发现", "自动化账单", "寻找客户"]
        }
    },
    "ja": {
        "onboarding_title": "Hunti AI Solutionsへようこそ", "onboarding_subtitle": "ダッシュボードをパーソナライズしましょう。",
        "q1_lang": "言語を選択", "q2_business": "ビジネスを説明するものは?", "q3_team": "チーム規模?", "q4_goal": "自動化の目標?",
        "btn_start": "ダッシュボードを生成",
        "lang_en": "英語", "lang_hu": "ハンガリー語", "lang_es": "スペイン語", "lang_fr": "フランス語", "lang_de": "ドイツ語", "lang_it": "イタリア語", "lang_pt": "ポルトガル語", "lang_ru": "ロシア語", "lang_zh": "中国語", "lang_ja": "日本語", "lang_ar": "アラビア語",
        "biz_small": "小規模事業", "biz_agency": "エージェンシー", "biz_ecom": "Eコマース", "biz_freelance": "フリーランス",
        "team_1": "一人", "team_2": "2-5人", "team_3": "6-20人", "team_4": "20人以上",
        "goal_leads": "リードを増やす", "goal_support": "サポート改善", "goal_admin": "管理自動化", "goal_sales": "販売最適化",
        "nav_hunti": "Hunti AI", "nav_analytics": "分析", "nav_pitches": "メール送信", "sidebar_title": "プロフィール", "reset_prefs": "リセット",
        "total_req": "総リクエスト", "req_hour": "リクエスト(時間)",
        "hunti_title": "Hunti AI - インテリジェントコンサルタント", "hunti_welcome": "ようこそ!お手伝いします。", "hunti_sub": "課題について教えてください。", "hunti_input": "どのような課題がありますか?",
        "analytics_title": "分析ダッシュボード", "analytics_sub": "リアルタイム指標。",
        "total_leads": "総リード", "pitches_gen": "提案", "emails_sent": "メール", "forms_sub": "フォーム", "activity_overview": "活動", "email_status": "メール状態", "recent_activity": "最近の活動", "db_records": "データベース",
        "pitch_title": "自動メール送信", "pitch_sub": "自動的に生成して送信。", "pitch_info": "リードを選択するとHuntiが送信。",
        "avail_leads": "利用可能なリード", "btn_gen_pitch": "生成", "btn_view_pitch": "表示", "success_gen": "生成完了!", "no_leads": "リードなし!", "no_pitches": "提案なし。",
        "footer": "2026 Hunti AI Solutions.", "loading": "読み込み中...", "generating_dashboard": "生成中...", "generating": "生成中...",
        "suggestions": {
            "小規模事業": ["メールが溢れている", "チームが時間を浪費", "リードが必要", "フォローアップ自動化"],
            "エージェンシー": ["オンボーディングに時間", "提案自動化", "レポート最適化", "コミュニケーション管理"],
            "Eコマース": ["注文自動化", "同じ質問", "在庫更新", "レビュー収集"],
            "フリーランス": ["管理業務が多い", "発見自動化", "請求自動化", "顧客を見つける"]
        }
    },
    "ar": {
        "onboarding_title": "مرحبًا بك في Hunti AI Solutions", "onboarding_subtitle": "دعنا نخصص لوحة التحكم.",
        "q1_lang": "اختر اللغة", "q2_business": "ما يصف عملك?", "q3_team": "حجم الفريق?", "q4_goal": "هدف الأتمتة?",
        "btn_start": "إنشاء لوحة التحكم",
        "lang_en": "الإنجليزية", "lang_hu": "المجرية", "lang_es": "الإسبانية", "lang_fr": "الفرنسية", "lang_de": "الألمانية", "lang_it": "الإيطالية", "lang_pt": "البرتغالية", "lang_ru": "الروسية", "lang_zh": "الصينية", "lang_ja": "اليابانية", "lang_ar": "العربية",
        "biz_small": "عمل صغير", "biz_agency": "وكالة", "biz_ecom": "تجارة إلكترونية", "biz_freelance": "مستقل",
        "team_1": "وحدي", "team_2": "2-5 موظفين", "team_3": "6-20 موظف", "team_4": "20+ موظف",
        "goal_leads": "المزيد من العملاء", "goal_support": "تحسين الدعم", "goal_admin": "أتمتة الإدارة", "goal_sales": "تحسين المبيعات",
        "nav_hunti": "Hunti AI", "nav_analytics": "التحليلات", "nav_pitches": "البريد", "sidebar_title": "الملف الشخصي", "reset_prefs": "إعادة تعيين",
        "total_req": "إجمالي الطلبات", "req_hour": "الطلبات (ساعة)",
        "hunti_title": "Hunti AI - مستشار ذكي", "hunti_welcome": "مرحبًا! أنا هنا للمساعدة.", "hunti_sub": "أخبرني عن تحدياتك.", "hunti_input": "ما التحدي الذي تواجهه?",
        "analytics_title": "لوحة التحليلات", "analytics_sub": "مقاييس الوقت الفعلي.",
        "total_leads": "إجمالي العملاء", "pitches_gen": "العروض", "emails_sent": "البريد", "forms_sub": "النماذج", "activity_overview": "النشاط", "email_status": "حالة البريد", "recent_activity": "النشاط الأخير", "db_records": "قاعدة البيانات",
        "pitch_title": "البريد التلقائي", "pitch_sub": "إنشاء وإرسال تلقائي.", "pitch_info": "اختر العملاء وسيقوم Hunti بالإرسال.",
        "avail_leads": "العملاء المتاحين", "btn_gen_pitch": "إنشاء", "btn_view_pitch": "عرض", "success_gen": "تم الإنشاء!", "no_leads": "لا عملاء!", "no_pitches": "لا عروض.",
        "footer": "2026 Hunti AI Solutions.", "loading": "تحميل...", "generating_dashboard": "إنشاء...", "generating": "إنشاء...",
        "suggestions": {
            "عمل صغير": ["أنا غارق في الرسائل", "الفريق يضيع ساعات", "أحتاج عملاء", "أتمتة المتابعة"],
            "وكالة": ["وقت كثير في الانضمام", "أتمتة العروض", "تحسين التقارير", "إدارة الاتصالات"],
            "تجارة إلكترونية": ["أتمتة الطلبات", "نفس الأسئلة", "تحديث المخزون", "جمع التقييمات"],
            "مستقل": ["كثير من الإدارة", "أتمتة الاكتشاف", "أتمتة الفواتير", "إيجاد عملاء"]
        }
    }
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
if 'target_page' not in st.session_state: st.session_state.target_page = None
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

# --- PAGE TRANSITION ---
if st.session_state.target_page and st.session_state.target_page != st.session_state.page:
    st.markdown("""
        <div class="loading-overlay">
            <div>
                <div class="loading-spinner"></div>
                <p style="color: white; margin-top: 20px; font-size: 18px;">""" + t("loading") + """</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    st.session_state.page = st.session_state.target_page
    st.session_state.target_page = None
    st.rerun()

# --- MAIN APP ---
def navigate_to_page(page_name):
    st.session_state.target_page = page_name

col_nav1, col_nav2, col_nav3 = st.columns(3)
with col_nav1:
    if st.button(t("nav_hunti"), use_container_width=True, key="btn_hunti"): navigate_to_page("Hunti AI")
with col_nav2:
    if st.button(t("nav_analytics"), use_container_width=True, key="btn_analytics"): navigate_to_page("Analytics")
with col_nav3:
    if st.button(t("nav_pitches"), use_container_width=True, key="btn_pitches"): navigate_to_page("Pitch Emailer")

st.divider()

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
        st.rerun()
    
    st.divider()
    try:
        stats = get_usage_stats(st.session_state.user_id)
        st.metric(t("total_req"), stats['total_requests'])
        st.metric(t("req_hour"), stats['requests_last_hour'], delta="Limit: 10/hour")
    except: pass
    
    st.divider()
    st.caption("Hunti AI Solutions")

if st.session_state.page == "Hunti AI":
    st.title(t("hunti_title"))
    st.markdown(t("hunti_welcome"))
    st.markdown(f"*{t('hunti_sub')}*")
    st.divider()
    
    if st.session_state.business_type:
        st.subheader(f"Common Challenges for {st.session_state.business_type}")
        cols = st.columns(2)
        
        # Safe suggestions lookup
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
                if not pitches_df.empty: st.dataframe(pitches_df, use_container_width=True)
                else: st.info(t("no_pitches"))
    else:
        st.warning(t("no_leads"))

st.divider()
st.markdown(t("footer"))