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

st.set_page_config(page_title="Hunti AI - Command Center", page_icon="", layout="wide")

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
            background-color: rgba(0, 0, 0, 0.9);
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
        "q1_lang": "Select your preferred language",
        "q2_business": "What best describes your business?",
        "q3_team": "What's your team size?",
        "q4_goal": "What's your main automation goal?",
        "btn_start": "Generate My Dashboard",
        "lang_en": "English",
        "lang_hu": "Hungarian (Magyar)",
        "lang_es": "Spanish (Español)",
        "lang_fr": "French (Français)",
        "lang_de": "German (Deutsch)",
        "lang_it": "Italian (Italiano)",
        "lang_pt": "Portuguese (Português)",
        "lang_ru": "Russian (Русский)",
        "lang_zh": "Chinese (中文)",
        "lang_ja": "Japanese (日本語)",
        "lang_ar": "Arabic (العربية)",
        "biz_small": "Small Business Owner",
        "biz_agency": "Agency Owner",
        "biz_ecom": "E-commerce",
        "biz_freelance": "Freelancer / Solopreneur",
        "team_1": "Just me (Solo)",
        "team_2": "2-5 employees",
        "team_3": "6-20 employees",
        "team_4": "20+ employees",
        "goal_leads": "Generate more leads",
        "goal_support": "Improve customer support",
        "goal_admin": "Automate admin tasks",
        "goal_sales": "Streamline sales process",
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
        "generating_dashboard": "Generating your personalized dashboard...",
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
        "q1_lang": "Válassza ki a preferált nyelvet",
        "q2_business": "Mi írja le legjobban a vállalkozását?",
        "q3_team": "Mekkora a csapatméret?",
        "q4_goal": "Mi a fő automatizálási célja?",
        "btn_start": "Irányítópult Generálása",
        "lang_en": "Angol (English)",
        "lang_hu": "Magyar",
        "lang_es": "Spanyol (Español)",
        "lang_fr": "Francia (Français)",
        "lang_de": "Német (Deutsch)",
        "lang_it": "Olasz (Italiano)",
        "lang_pt": "Portugál (Português)",
        "lang_ru": "Orosz (Русский)",
        "lang_zh": "Kínai (中文)",
        "lang_ja": "Japán (日本語)",
        "lang_ar": "Arab (العربية)",
        "biz_small": "Kisvállalkozás Tulajdonos",
        "biz_agency": "Ügynökség Tulajdonos",
        "biz_ecom": "E-kereskedelem",
        "biz_freelance": "Szabadúszó / Egyéni Vállalkozó",
        "team_1": "Egyedül vagyok (Solo)",
        "team_2": "2-5 alkalmazott",
        "team_3": "6-20 alkalmazott",
        "team_4": "20+ alkalmazott",
        "goal_leads": "Több lead generálása",
        "goal_support": "Ügyféltámogatás javítása",
        "goal_admin": "Adminisztratív feladatok automatizálása",
        "goal_sales": "Értékesítési folyamat egyszerűsítése",
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
        "generating_dashboard": "Az Ön személyre szabott irányítópultjának generálása...",
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
    },
    "es": {
        "onboarding_title": "Bienvenido a Hunti AI Solutions",
        "onboarding_subtitle": "Personalicemos su panel de automatización en unos segundos.",
        "q1_lang": "Seleccione su idioma preferido",
        "q2_business": "¿Qué describe mejor su negocio?",
        "q3_team": "¿Cuál es el tamaño de su equipo?",
        "q4_goal": "¿Cuál es su principal objetivo de automatización?",
        "btn_start": "Generar Mi Panel",
        "lang_en": "Inglés (English)",
        "lang_hu": "Húngaro (Magyar)",
        "lang_es": "Español",
        "lang_fr": "Francés (Français)",
        "lang_de": "Alemán (Deutsch)",
        "lang_it": "Italiano",
        "lang_pt": "Portugués (Português)",
        "lang_ru": "Ruso (Русский)",
        "lang_zh": "Chino (中文)",
        "lang_ja": "Japonés (日本語)",
        "lang_ar": "Árabe (العربية)",
        "biz_small": "Propietario de Pequeña Empresa",
        "biz_agency": "Propietario de Agencia",
        "biz_ecom": "Comercio Electrónico",
        "biz_freelance": "Autónomo / Emprendedor",
        "team_1": "Solo yo (Individual)",
        "team_2": "2-5 empleados",
        "team_3": "6-20 empleados",
        "team_4": "20+ empleados",
        "goal_leads": "Generar más leads",
        "goal_support": "Mejorar el soporte al cliente",
        "goal_admin": "Automatizar tareas administrativas",
        "goal_sales": "Optimizar el proceso de ventas",
        "nav_hunti": "Hunti AI",
        "nav_analytics": "Panel de Análisis",
        "nav_pitches": "Emailer de Propuestas",
        "sidebar_title": "Perfil de Usuario",
        "reset_prefs": "Restablecer Preferencias",
        "total_req": "Total de Solicitudes",
        "req_hour": "Solicitudes (Última Hora)",
        "hunti_title": "Hunti AI - Su Consultor de Ventas Inteligente",
        "hunti_welcome": "¡Bienvenido! Estoy aquí para ayudarle a automatizar su negocio y ahorrar tiempo.",
        "hunti_sub": "Cuénteme sus desafíos y le mostraré cómo la IA puede resolverlos.",
        "hunti_input": "¿Qué desafío enfrenta?",
        "analytics_title": "Panel de Análisis",
        "analytics_sub": "Métricas de rendimiento en tiempo real para sus campañas de automatización.",
        "total_leads": "Total de Leads",
        "pitches_gen": "Propuestas Generadas",
        "emails_sent": "Emails Enviados",
        "forms_sub": "Formularios Enviados",
        "activity_overview": "Resumen de Actividad",
        "email_status": "Estado de Entrega de Emails",
        "recent_activity": "Registro de Actividad Reciente",
        "db_records": "Registros de Base de Datos",
        "pitch_title": "Emailer Automatizado de Propuestas",
        "pitch_sub": "Genere y envíe propuestas de ventas personalizadas a sus leads automáticamente.",
        "pitch_info": "Cómo funciona: Seleccione leads de su base de datos y Hunti generará propuestas personalizadas y las enviará por email.",
        "avail_leads": "Leads Disponibles",
        "btn_gen_pitch": "Generar Propuestas",
        "btn_view_pitch": "Ver Propuestas Generadas",
        "success_gen": "¡Propuestas generadas exitosamente!",
        "no_leads": "¡No se encontraron leads. ¡Agregue algunos primero!",
        "no_pitches": "Aún no se han generado propuestas. Haga clic en 'Generar Propuestas' para crearlas.",
        "footer": "2026 Hunti AI Solutions. Todos los derechos reservados.",
        "loading": "Cargando...",
        "generating_dashboard": "Generando su panel personalizado...",
        "generating": "Generando...",
        "suggestions": {
            "Propietario de Pequeña Empresa": [
                "Me estoy ahogando en emails y no puedo responder lo suficientemente rápido",
                "Mi equipo pierde horas en tareas manuales repetitivas",
                "Necesito generar más leads pero no tengo tiempo",
                "Quiero automatizar el seguimiento de mis clientes"
            ],
            "Propietario de Agencia": [
                "Mi equipo pasa demasiado tiempo en la incorporación de clientes",
                "Necesitamos automatizar la generación de propuestas",
                "Quiero optimizar nuestro proceso de informes de clientes",
                "Estamos luchando por gestionar múltiples comunicaciones con clientes"
            ],
            "Comercio Electrónico": [
                "Necesito automatizar las confirmaciones de pedidos y el seguimiento",
                "Los clientes hacen repetidamente las mismas preguntas",
                "Quiero automatizar las actualizaciones de inventario y notificaciones",
                "Necesito mejores formas de recopilar y responder a las reseñas"
            ],
            "Autónomo / Emprendedor": [
                "Paso demasiado tiempo en administración en lugar de trabajo facturable",
                "Necesito automatizar mi proceso de descubrimiento de clientes",
                "Quiero automatizar mi facturación y recordatorios de pago",
                "Necesito ayuda para encontrar y calificar nuevos clientes"
            ]
        }
    },
    "fr": {
        "onboarding_title": "Bienvenue chez Hunti AI Solutions",
        "onboarding_subtitle": "Personnalisons votre tableau de bord d'automatisation en quelques secondes.",
        "q1_lang": "Sélectionnez votre langue préférée",
        "q2_business": "Qu'est-ce qui décrit le mieux votre entreprise?",
        "q3_team": "Quelle est la taille de votre équipe?",
        "q4_goal": "Quel est votre principal objectif d'automatisation?",
        "btn_start": "Générer Mon Tableau de Bord",
        "lang_en": "Anglais (English)",
        "lang_hu": "Hongrois (Magyar)",
        "lang_es": "Espagnol (Español)",
        "lang_fr": "Français",
        "lang_de": "Allemand (Deutsch)",
        "lang_it": "Italien (Italiano)",
        "lang_pt": "Portugais (Português)",
        "lang_ru": "Russe (Русский)",
        "lang_zh": "Chinois (中文)",
        "lang_ja": "Japonais (日本語)",
        "lang_ar": "Arabe (العربية)",
        "biz_small": "Propriétaire de Petite Entreprise",
        "biz_agency": "Propriétaire d'Agence",
        "biz_ecom": "Commerce Électronique",
        "biz_freelance": "Indépendant / Auto-entrepreneur",
        "team_1": "Seul (Solo)",
        "team_2": "2-5 employés",
        "team_3": "6-20 employés",
        "team_4": "20+ employés",
        "goal_leads": "Générer plus de leads",
        "goal_support": "Améliorer le support client",
        "goal_admin": "Automatiser les tâches administratives",
        "goal_sales": "Optimiser le processus de vente",
        "nav_hunti": "Hunti AI",
        "nav_analytics": "Tableau de Bord Analytique",
        "nav_pitches": "Emailer de Propositions",
        "sidebar_title": "Profil Utilisateur",
        "reset_prefs": "Réinitialiser les Préférences",
        "total_req": "Total des Demandes",
        "req_hour": "Demandes (Dernière Heure)",
        "hunti_title": "Hunti AI - Votre Consultant Commercial Intelligent",
        "hunti_welcome": "Bienvenue! Je suis là pour vous aider à automatiser votre entreprise et gagner du temps.",
        "hunti_sub": "Parlez-moi de vos défis et je vous montrerai comment l'IA peut les résoudre.",
        "hunti_input": "Quel défi rencontrez-vous?",
        "analytics_title": "Tableau de Bord Analytique",
        "analytics_sub": "Métriques de performance en temps réel pour vos campagnes d'automatisation.",
        "total_leads": "Total des Leads",
        "pitches_gen": "Propositions Générées",
        "emails_sent": "Emails Envoyés",
        "forms_sub": "Formulaires Soumis",
        "activity_overview": "Aperçu de l'Activité",
        "email_status": "Statut de Livraison des Emails",
        "recent_activity": "Journal d'Activité Récente",
        "db_records": "Enregistrements de Base de Données",
        "pitch_title": "Emailer Automatisé de Propositions",
        "pitch_sub": "Générez et envoyez des propositions de ventes personnalisées à vos leads automatiquement.",
        "pitch_info": "Comment ça marche: Sélectionnez des leads de votre base de données et Hunti générera des propositions personnalisées et les enverra par email.",
        "avail_leads": "Leads Disponibles",
        "btn_gen_pitch": "Générer des Propositions",
        "btn_view_pitch": "Voir les Propositions Générées",
        "success_gen": "Propositions générées avec succès!",
        "no_leads": "Aucun lead trouvé. Ajoutez d'abord des leads!",
        "no_pitches": "Aucune proposition générée. Cliquez sur 'Générer des Propositions' pour les créer.",
        "footer": "2026 Hunti AI Solutions. Tous droits réservés.",
        "loading": "Chargement...",
        "generating_dashboard": "Génération de votre tableau de bord personnalisé...",
        "generating": "Génération...",
        "suggestions": {
            "Propriétaire de Petite Entreprise": [
                "Je suis submergé d'emails et ne peux pas répondre assez vite",
                "Mon équipe perd des heures sur des tâches manuelles répétitives",
                "J'ai besoin de générer plus de leads mais je n'ai pas le temps",
                "Je veux automatiser le suivi de mes clients"
            ],
            "Propriétaire d'Agence": [
                "Mon équipe passe trop de temps sur l'intégration des clients",
                "Nous devons automatiser la génération de propositions",
                "Je veux optimiser notre processus de rapport client",
                "Nous luttons pour gérer plusieurs communications clients"
            ],
            "Commerce Électronique": [
                "J'ai besoin d'automatiser les confirmations de commande et le suivi",
                "Les clients posent répétitivement les mêmes questions",
                "Je veux automatiser les mises à jour d'inventaire et notifications",
                "J'ai besoin de meilleures façons de collecter et répondre aux avis"
            ],
            "Indépendant / Auto-entrepreneur": [
                "Je passe trop de temps sur l'administration au lieu du travail facturable",
                "J'ai besoin d'automatiser mon processus de découverte de clients",
                "Je veux automatiser ma facturation et rappels de paiement",
                "J'ai besoin d'aide pour trouver et qualifier de nouveaux clients"
            ]
        }
    },
    "de": {
        "onboarding_title": "Willkommen bei Hunti AI Solutions",
        "onboarding_subtitle": "Lassen Sie uns Ihr Automatisierungs-Dashboard in wenigen Sekunden personalisieren.",
        "q1_lang": "Wählen Sie Ihre bevorzugte Sprache",
        "q2_business": "Was beschreibt Ihr Unternehmen am besten?",
        "q3_team": "Wie groß ist Ihr Team?",
        "q4_goal": "Was ist Ihr Hauptziel für Automatisierung?",
        "btn_start": "Mein Dashboard Generieren",
        "lang_en": "Englisch (English)",
        "lang_hu": "Ungarisch (Magyar)",
        "lang_es": "Spanisch (Español)",
        "lang_fr": "Französisch (Français)",
        "lang_de": "Deutsch",
        "lang_it": "Italienisch (Italiano)",
        "lang_pt": "Portugiesisch (Português)",
        "lang_ru": "Russisch (Русский)",
        "lang_zh": "Chinesisch (中文)",
        "lang_ja": "Japanisch (日本語)",
        "lang_ar": "Arabisch (العربية)",
        "biz_small": "Kleinunternehmer",
        "biz_agency": "Agenturinhaber",
        "biz_ecom": "E-Commerce",
        "biz_freelance": "Freiberufler / Solo-Unternehmer",
        "team_1": "Nur ich (Solo)",
        "team_2": "2-5 Mitarbeiter",
        "team_3": "6-20 Mitarbeiter",
        "team_4": "20+ Mitarbeiter",
        "goal_leads": "Mehr Leads generieren",
        "goal_support": "Kundensupport verbessern",
        "goal_admin": "Administrative Aufgaben automatisieren",
        "goal_sales": "Verkaufsprozess optimieren",
        "nav_hunti": "Hunti AI",
        "nav_analytics": "Analyse-Dashboard",
        "nav_pitches": "Angebots-E-Mail",
        "sidebar_title": "Benutzerprofil",
        "reset_prefs": "Einstellungen Zurücksetzen",
        "total_req": "Gesamte Anfragen",
        "req_hour": "Anfragen (Letzte Stunde)",
        "hunti_title": "Hunti AI - Ihr Intelligenter Verkaufsberater",
        "hunti_welcome": "Willkommen! Ich bin hier, um Ihnen zu helfen, Ihr Unternehmen zu automatisieren und Zeit zu sparen.",
        "hunti_sub": "Erzählen Sie mir von Ihren Herausforderungen und ich zeige Ihnen, wie KI sie lösen kann.",
        "hunti_input": "Welche Herausforderung haben Sie?",
        "analytics_title": "Analyse-Dashboard",
        "analytics_sub": "Echtzeit-Leistungsmetriken für Ihre Automatisierungskampagnen.",
        "total_leads": "Gesamte Leads",
        "pitches_gen": "Generierte Angebote",
        "emails_sent": "Gesendete E-Mails",
        "forms_sub": "Eingereichte Formulare",
        "activity_overview": "Aktivitätsübersicht",
        "email_status": "E-Mail-Zustellstatus",
        "recent_activity": "Letzte Aktivitätsprotokoll",
        "db_records": "Datenbankeinträge",
        "pitch_title": "Automatisierter Angebots-E-Mail",
        "pitch_sub": "Generieren und senden Sie personalisierte Verkaufsangebote automatisch an Ihre Leads.",
        "pitch_info": "So funktioniert's: Wählen Sie Leads aus Ihrer Datenbank aus und Hunti generiert personalisierte Angebote und sendet sie per E-Mail.",
        "avail_leads": "Verfügbare Leads",
        "btn_gen_pitch": "Angebote Generieren",
        "btn_view_pitch": "Generierte Angebote Anzeigen",
        "success_gen": "Angebote erfolgreich generiert!",
        "no_leads": "Keine Leads gefunden. Fügen Sie zuerst Leads hinzu!",
        "no_pitches": "Noch keine Angebote generiert. Klicken Sie auf 'Angebote Generieren' um sie zu erstellen.",
        "footer": "2026 Hunti AI Solutions. Alle Rechte vorbehalten.",
        "loading": "Wird geladen...",
        "generating_dashboard": "Ihr personalisiertes Dashboard wird generiert...",
        "generating": "Generieren...",
        "suggestions": {
            "Kleinunternehmer": [
                "Ich ertrinke in E-Mails und kann nicht schnell genug antworten",
                "Mein Team verschwendet Stunden mit repetitiven manuellen Aufgaben",
                "Ich muss mehr Leads generieren, habe aber keine Zeit",
                "Ich möchte meine Kundenbetreuung automatisieren"
            ],
            "Agenturinhaber": [
                "Mein Team verbringt zu viel Zeit mit Kunden-Onboarding",
                "Wir müssen die Angebotserstellung automatisieren",
                "Ich möchte unseren Kundenberichtsprozess optimieren",
                "Wir kämpfen damit, mehrere Kundenkommunikationen zu verwalten"
            ],
            "E-Commerce": [
                "Ich muss Bestellbestätigungen und Tracking automatisieren",
                "Kunden stellen wiederholt dieselben Fragen",
                "Ich möchte Bestandsaktualisierungen und Benachrichtigungen automatisieren",
                "Ich brauche bessere Möglichkeiten, Bewertungen zu sammeln und zu beantworten"
            ],
            "Freiberufler / Solo-Unternehmer": [
                "Ich verbringe zu viel Zeit mit Verwaltung statt abrechenbarer Arbeit",
                "Ich muss meinen Kundenfindungsprozess automatisieren",
                "Ich möchte meine Rechnungsstellung und Zahlungserinnerungen automatisieren",
                "Ich brauche Hilfe beim Finden und Qualifizieren neuer Kunden"
            ]
        }
    },
    "it": {
        "onboarding_title": "Benvenuto in Hunti AI Solutions",
        "onboarding_subtitle": "Personalizziamo la tua dashboard di automazione in pochi secondi.",
        "q1_lang": "Seleziona la tua lingua preferita",
        "q2_business": "Cosa descrive meglio la tua attività?",
        "q3_team": "Qual è la dimensione del tuo team?",
        "q4_goal": "Qual è il tuo principale obiettivo di automazione?",
        "btn_start": "Genera la Mia Dashboard",
        "lang_en": "Inglese (English)",
        "lang_hu": "Ungherese (Magyar)",
        "lang_es": "Spagnolo (Español)",
        "lang_fr": "Francese (Français)",
        "lang_de": "Tedesco (Deutsch)",
        "lang_it": "Italiano",
        "lang_pt": "Portoghese (Português)",
        "lang_ru": "Russo (Русский)",
        "lang_zh": "Cinese (中文)",
        "lang_ja": "Giapponese (日本語)",
        "lang_ar": "Arabo (العربية)",
        "biz_small": "Proprietario di Piccola Impresa",
        "biz_agency": "Proprietario di Agenzia",
        "biz_ecom": "E-commerce",
        "biz_freelance": "Freelance / Imprenditore Solitario",
        "team_1": "Solo io (Solista)",
        "team_2": "2-5 dipendenti",
        "team_3": "6-20 dipendenti",
        "team_4": "20+ dipendenti",
        "goal_leads": "Generare più lead",
        "goal_support": "Migliorare il supporto clienti",
        "goal_admin": "Automatizzare compiti amministrativi",
        "goal_sales": "Ottimizzare il processo di vendita",
        "nav_hunti": "Hunti AI",
        "nav_analytics": "Dashboard Analitica",
        "nav_pitches": "Email di Proposte",
        "sidebar_title": "Profilo Utente",
        "reset_prefs": "Reimposta Preferenze",
        "total_req": "Totale Richieste",
        "req_hour": "Richieste (Ultima Ora)",
        "hunti_title": "Hunti AI - Il Tuo Consulente di Vendita Intelligente",
        "hunti_welcome": "Benvenuto! Sono qui per aiutarti ad automatizzare la tua attività e risparmiare tempo.",
        "hunti_sub": "Parlami delle tue sfide e ti mostrerò come l'IA può risolverle.",
        "hunti_input": "Quale sfida stai affrontando?",
        "analytics_title": "Dashboard Analitica",
        "analytics_sub": "Metriche di prestazione in tempo reale per le tue campagne di automazione.",
        "total_leads": "Totale Lead",
        "pitches_gen": "Proposte Generate",
        "emails_sent": "Email Inviate",
        "forms_sub": "Moduli Inviati",
        "activity_overview": "Panoramica Attività",
        "email_status": "Stato Consegna Email",
        "recent_activity": "Registro Attività Recente",
        "db_records": "Record Database",
        "pitch_title": "Email di Proposte Automatizzata",
        "pitch_sub": "Genera e invia proposte di vendita personalizzate ai tuoi lead automaticamente.",
        "pitch_info": "Come funziona: Seleziona i lead dal tuo database e Hunti genererà proposte personalizzate e le invierà via email.",
        "avail_leads": "Lead Disponibili",
        "btn_gen_pitch": "Genera Proposte",
        "btn_view_pitch": "Visualizza Proposte Generate",
        "success_gen": "Proposte generate con successo!",
        "no_leads": "Nessun lead trovato. Aggiungi prima dei lead!",
        "no_pitches": "Nessuna proposta generata. Clicca su 'Genera Proposte' per crearle.",
        "footer": "2026 Hunti AI Solutions. Tutti i diritti riservati.",
        "loading": "Caricamento...",
        "generating_dashboard": "Generazione della tua dashboard personalizzata...",
        "generating": "Generazione...",
        "suggestions": {
            "Proprietario di Piccola Impresa": [
                "Sono sommerso da email e non riesco a rispondere abbastanza velocemente",
                "Il mio team perde ore in compiti manuali ripetitivi",
                "Ho bisogno di generare più lead ma non ho tempo",
                "Voglio automatizzare il follow-up dei miei clienti"
            ],
            "Proprietario di Agenzia": [
                "Il mio team passa troppo tempo nell'onboarding dei clienti",
                "Dobbiamo automatizzare la generazione di proposte",
                "Voglio ottimizzare il nostro processo di reportistica clienti",
                "Faticiamo a gestire più comunicazioni con i clienti"
            ],
            "E-commerce": [
                "Ho bisogno di automatizzare conferme ordini e tracciamento",
                "I clienti fanno ripetutamente le stesse domande",
                "Voglio automatizzare aggiornamenti inventario e notifiche",
                "Ho bisogno di modi migliori per raccogliere e rispondere alle recensioni"
            ],
            "Freelance / Imprenditore Solitario": [
                "Passo troppo tempo nell'amministrazione invece del lavoro fatturabile",
                "Ho bisogno di automatizzare il mio processo di scoperta clienti",
                "Voglio automatizzare la mia fatturazione e promemoria di pagamento",
                "Ho bisogno di aiuto per trovare e qualificare nuovi clienti"
            ]
        }
    },
    "pt": {
        "onboarding_title": "Bem-vindo à Hunti AI Solutions",
        "onboarding_subtitle": "Vamos personalizar seu painel de automação em poucos segundos.",
        "q1_lang": "Selecione seu idioma preferido",
        "q2_business": "O que melhor descreve seu negócio?",
        "q3_team": "Qual é o tamanho da sua equipe?",
        "q4_goal": "Qual é seu principal objetivo de automação?",
        "btn_start": "Gerar Meu Painel",
        "lang_en": "Inglês (English)",
        "lang_hu": "Húngaro (Magyar)",
        "lang_es": "Espanhol (Español)",
        "lang_fr": "Francês (Français)",
        "lang_de": "Alemão (Deutsch)",
        "lang_it": "Italiano",
        "lang_pt": "Português",
        "lang_ru": "Russo (Русский)",
        "lang_zh": "Chinês (中文)",
        "lang_ja": "Japonês (日本語)",
        "lang_ar": "Árabe (العربية)",
        "biz_small": "Proprietário de Pequena Empresa",
        "biz_agency": "Proprietário de Agência",
        "biz_ecom": "Comércio Eletrônico",
        "biz_freelance": "Autônomo / Empreendedor Individual",
        "team_1": "Apenas eu (Solo)",
        "team_2": "2-5 funcionários",
        "team_3": "6-20 funcionários",
        "team_4": "20+ funcionários",
        "goal_leads": "Gerar mais leads",
        "goal_support": "Melhorar o suporte ao cliente",
        "goal_admin": "Automatizar tarefas administrativas",
        "goal_sales": "Otimizar o processo de vendas",
        "nav_hunti": "Hunti AI",
        "nav_analytics": "Painel de Análise",
        "nav_pitches": "Email de Propostas",
        "sidebar_title": "Perfil do Usuário",
        "reset_prefs": "Redefinir Preferências",
        "total_req": "Total de Solicitações",
        "req_hour": "Solicitações (Última Hora)",
        "hunti_title": "Hunti AI - Seu Consultor de Vendas Inteligente",
        "hunti_welcome": "Bem-vindo! Estou aqui para ajudá-lo a automatizar seu negócio e economizar tempo.",
        "hunti_sub": "Conte-me sobre seus desafios e eu mostrarei como a IA pode resolvê-los.",
        "hunti_input": "Qual desafio você está enfrentando?",
        "analytics_title": "Painel de Análise",
        "analytics_sub": "Métricas de desempenho em tempo real para suas campanhas de automação.",
        "total_leads": "Total de Leads",
        "pitches_gen": "Propostas Geradas",
        "emails_sent": "Emails Enviados",
        "forms_sub": "Formulários Enviados",
        "activity_overview": "Visão Geral da Atividade",
        "email_status": "Status de Entrega de Emails",
        "recent_activity": "Registro de Atividade Recente",
        "db_records": "Registros do Banco de Dados",
        "pitch_title": "Email de Propostas Automatizado",
        "pitch_sub": "Gere e envie propostas de vendas personalizadas para seus leads automaticamente.",
        "pitch_info": "Como funciona: Selecione leads do seu banco de dados e o Hunti gerará propostas personalizadas e as enviará por email.",
        "avail_leads": "Leads Disponíveis",
        "btn_gen_pitch": "Gerar Propostas",
        "btn_view_pitch": "Ver Propostas Geradas",
        "success_gen": "Propostas geradas com sucesso!",
        "no_leads": "Nenhum lead encontrado. Adicione alguns leads primeiro!",
        "no_pitches": "Nenhuma proposta gerada ainda. Clique em 'Gerar Propostas' para criá-las.",
        "footer": "2026 Hunti AI Solutions. Todos os direitos reservados.",
        "loading": "Carregando...",
        "generating_dashboard": "Gerando seu painel personalizado...",
        "generating": "Gerando...",
        "suggestions": {
            "Proprietário de Pequena Empresa": [
                "Estou afogado em emails e não consigo responder rápido o suficiente",
                "Minha equipe perde horas em tarefas manuais repetitivas",
                "Preciso gerar mais leads mas não tenho tempo",
                "Quero automatizar o acompanhamento dos meus clientes"
            ],
            "Proprietário de Agência": [
                "Minha equipe passa muito tempo no onboarding de clientes",
                "Precisamos automatizar a geração de propostas",
                "Quero otimizar nosso processo de relatórios de clientes",
                "Estamos lutando para gerenciar múltiplas comunicações com clientes"
            ],
            "Comércio Eletrônico": [
                "Preciso automatizar confirmações de pedidos e rastreamento",
                "Os clientes fazem repetidamente as mesmas perguntas",
                "Quero automatizar atualizações de inventário e notificações",
                "Preciso de melhores formas de coletar e responder a avaliações"
            ],
            "Autônomo / Empreendedor Individual": [
                "Passo muito tempo em administração em vez de trabalho faturável",
                "Preciso automatizar meu processo de descoberta de clientes",
                "Quero automatizar minha faturamento e lembretes de pagamento",
                "Preciso de ajuda para encontrar e qualificar novos clientes"
            ]
        }
    },
    "ru": {
        "onboarding_title": "Добро пожаловать в Hunti AI Solutions",
        "onboarding_subtitle": "Давайте персонализируем вашу панель автоматизации за несколько секунд.",
        "q1_lang": "Выберите предпочтительный язык",
        "q2_business": "Что лучше всего описывает ваш бизнес?",
        "q3_team": "Какой размер вашей команды?",
        "q4_goal": "Какова ваша главная цель автоматизации?",
        "btn_start": "Сгенерировать Мою Панель",
        "lang_en": "Английский (English)",
        "lang_hu": "Венгерский (Magyar)",
        "lang_es": "Испанский (Español)",
        "lang_fr": "Французский (Français)",
        "lang_de": "Немецкий (Deutsch)",
        "lang_it": "Итальянский (Italiano)",
        "lang_pt": "Португальский (Português)",
        "lang_ru": "Русский",
        "lang_zh": "Китайский (中文)",
        "lang_ja": "Японский (日本語)",
        "lang_ar": "Арабский (العربية)",
        "biz_small": "Владелец малого бизнеса",
        "biz_agency": "Владелец агентства",
        "biz_ecom": "Электронная коммерция",
        "biz_freelance": "Фрилансер / Индивидуальный предприниматель",
        "team_1": "Только я (Соло)",
        "team_2": "2-5 сотрудников",
        "team_3": "6-20 сотрудников",
        "team_4": "20+ сотрудников",
        "goal_leads": "Генерировать больше лидов",
        "goal_support": "Улучшить поддержку клиентов",
        "goal_admin": "Автоматизировать административные задачи",
        "goal_sales": "Оптимизировать процесс продаж",
        "nav_hunti": "Hunti AI",
        "nav_analytics": "Панель аналитики",
        "nav_pitches": "Email предложений",
        "sidebar_title": "Профиль пользователя",
        "reset_prefs": "Сбросить настройки",
        "total_req": "Всего запросов",
        "req_hour": "Запросы (последний час)",
        "hunti_title": "Hunti AI - Ваш интеллектуальный консультант по продажам",
        "hunti_welcome": "Добро пожаловать! Я здесь, чтобы помочь вам автоматизировать ваш бизнес и сэкономить время.",
        "hunti_sub": "Расскажите мне о ваших проблемах, и я покажу, как ИИ может их решить.",
        "hunti_input": "С какой проблемой вы столкнулись?",
        "analytics_title": "Панель аналитики",
        "analytics_sub": "Метрики производительности в реальном времени для ваших кампаний автоматизации.",
        "total_leads": "Всего лидов",
        "pitches_gen": "Сгенерированные предложения",
        "emails_sent": "Отправленные email",
        "forms_sub": "Отправленные формы",
        "activity_overview": "Обзор активности",
        "email_status": "Статус доставки email",
        "recent_activity": "Журнал последней активности",
        "db_records": "Записи базы данных",
        "pitch_title": "Автоматизированный email предложений",
        "pitch_sub": "Генерируйте и отправляйте персонализированные предложения о продажах вашим лидам автоматически.",
        "pitch_info": "Как это работает: Выберите лиды из вашей базы данных, и Hunti сгенерирует персонализированные предложения и отправит их по email.",
        "avail_leads": "Доступные лиды",
        "btn_gen_pitch": "Сгенерировать предложения",
        "btn_view_pitch": "Просмотреть сгенерированные предложения",
        "success_gen": "Предложения успешно сгенерированы!",
        "no_leads": "Лиды не найдены. Сначала добавьте лиды!",
        "no_pitches": "Предложения еще не сгенерированы. Нажмите 'Сгенерировать предложения' для их создания.",
        "footer": "2026 Hunti AI Solutions. Все права защищены.",
        "loading": "Загрузка...",
        "generating_dashboard": "Генерация вашей персонализированной панели...",
        "generating": "Генерация...",
        "suggestions": {
            "Владелец малого бизнеса": [
                "Я тону в email и не могу отвечать достаточно быстро",
                "Моя команда тратит часы на повторяющиеся ручные задачи",
                "Мне нужно генерировать больше лидов, но у меня нет времени",
                "Я хочу автоматизировать последующую работу с клиентами"
            ],
            "Владелец агентства": [
                "Моя команда тратит слишком много времени на онбординг клиентов",
                "Нам нужно автоматизировать генерацию предложений",
                "Я хочу оптимизировать наш процесс отчетности для клиентов",
                "Мы боремся с управлением множественных коммуникаций с клиентами"
            ],
            "Электронная коммерция": [
                "Мне нужно автоматизировать подтверждения заказов и отслеживание",
                "Клиенты постоянно задают одни и те же вопросы",
                "Я хочу автоматизировать обновления инвентаря и уведомления",
                "Мне нужны лучшие способы сбора и ответа на отзывы"
            ],
            "Фрилансер / Индивидуальный предприниматель": [
                "Я трачу слишком много времени на администрирование вместо оплачиваемой работы",
                "Мне нужно автоматизировать мой процесс поиска клиентов",
                "Я хочу автоматизировать мой биллинг и напоминания об оплате",
                "Мне нужна помощь в поиске и квалификации новых клиентов"
            ]
        }
    },
    "zh": {
        "onboarding_title": "欢迎使用 Hunti AI Solutions",
        "onboarding_subtitle": "让我们在几秒钟内个性化您的自动化仪表板。",
        "q1_lang": "选择您的首选语言",
        "q2_business": "什么最能描述您的业务?",
        "q3_team": "您的团队规模是多少?",
        "q4_goal": "您的主要自动化目标是什么?",
        "btn_start": "生成我的仪表板",
        "lang_en": "英语 (English)",
        "lang_hu": "匈牙利语 (Magyar)",
        "lang_es": "西班牙语 (Español)",
        "lang_fr": "法语 (Français)",
        "lang_de": "德语 (Deutsch)",
        "lang_it": "意大利语 (Italiano)",
        "lang_pt": "葡萄牙语 (Português)",
        "lang_ru": "俄语 (Русский)",
        "lang_zh": "中文",
        "lang_ja": "日语 (日本語)",
        "lang_ar": "阿拉伯语 (العربية)",
        "biz_small": "小企业主",
        "biz_agency": "代理机构所有者",
        "biz_ecom": "电子商务",
        "biz_freelance": "自由职业者/个体经营者",
        "team_1": "只有我(单人)",
        "team_2": "2-5名员工",
        "team_3": "6-20名员工",
        "team_4": "20名以上员工",
        "goal_leads": "生成更多潜在客户",
        "goal_support": "改善客户支持",
        "goal_admin": "自动化行政任务",
        "goal_sales": "优化销售流程",
        "nav_hunti": "Hunti AI",
        "nav_analytics": "分析仪表板",
        "nav_pitches": "提案邮件",
        "sidebar_title": "用户资料",
        "reset_prefs": "重置偏好设置",
        "total_req": "总请求数",
        "req_hour": "请求(最近一小时)",
        "hunti_title": "Hunti AI - 您的智能销售顾问",
        "hunti_welcome": "欢迎!我在这里帮助您自动化业务并节省时间。",
        "hunti_sub": "告诉我您面临的挑战,我会向您展示AI如何解决它们。",
        "hunti_input": "您面临什么挑战?",
        "analytics_title": "分析仪表板",
        "analytics_sub": "您的自动化活动的实时性能指标。",
        "total_leads": "总潜在客户",
        "pitches_gen": "生成的提案",
        "emails_sent": "已发送邮件",
        "forms_sub": "已提交表单",
        "activity_overview": "活动概览",
        "email_status": "邮件投递状态",
        "recent_activity": "最近活动日志",
        "db_records": "数据库记录",
        "pitch_title": "自动化提案邮件",
        "pitch_sub": "自动生成并向您的潜在客户发送个性化销售提案。",
        "pitch_info": "工作原理:从您的数据库中选择潜在客户,Hunti将生成个性化提案并通过电子邮件发送。",
        "avail_leads": "可用潜在客户",
        "btn_gen_pitch": "生成提案",
        "btn_view_pitch": "查看生成的提案",
        "success_gen": "提案生成成功!",
        "no_leads": "未找到潜在客户。请先添加一些潜在客户!",
        "no_pitches": "尚未生成提案。点击'生成提案'来创建它们。",
        "footer": "2026 Hunti AI Solutions. 保留所有权利。",
        "loading": "加载中...",
        "generating_dashboard": "正在生成您的个性化仪表板...",
        "generating": "生成中...",
        "suggestions": {
            "小企业主": [
                "我淹没在邮件中,无法足够快地回复",
                "我的团队在重复性手动任务上浪费时间",
                "我需要生成更多潜在客户但没有时间",
                "我想自动化我的客户跟进"
            ],
            "代理机构所有者": [
                "我的团队在客户入职上花费太多时间",
                "我们需要自动化提案生成",
                "我想优化我们的客户报告流程",
                "我们在管理多个客户沟通方面遇到困难"
            ],
            "电子商务": [
                "我需要自动化订单确认和跟踪",
                "客户反复询问相同的问题",
                "我想自动化库存更新和通知",
                "我需要更好的方式来收集和回复评论"
            ],
            "自由职业者/个体经营者": [
                "我花太多时间在行政工作上而不是计费工作",
                "我需要自动化我的客户发现流程",
                "我想自动化我的计费和付款提醒",
                "我需要帮助寻找和筛选新客户"
            ]
        }
    },
    "ja": {
        "onboarding_title": "Hunti AI Solutionsへようこそ",
        "onboarding_subtitle": "数秒で自動化ダッシュボードをパーソナライズしましょう。",
        "q1_lang": "希望する言語を選択してください",
        "q2_business": "あなたのビジネスを最もよく表すものは?",
        "q3_team": "チームの規模は?",
        "q4_goal": "主な自動化の目標は何ですか?",
        "btn_start": "ダッシュボードを生成",
        "lang_en": "英語 (English)",
        "lang_hu": "ハンガリー語 (Magyar)",
        "lang_es": "スペイン語 (Español)",
        "lang_fr": "フランス語 (Français)",
        "lang_de": "ドイツ語 (Deutsch)",
        "lang_it": "イタリア語 (Italiano)",
        "lang_pt": "ポルトガル語 (Português)",
        "lang_ru": "ロシア語 (Русский)",
        "lang_zh": "中国語 (中文)",
        "lang_ja": "日本語",
        "lang_ar": "アラビア語 (العربية)",
        "biz_small": "小規模事業者",
        "biz_agency": "エージェンシーオーナー",
        "biz_ecom": "Eコマース",
        "biz_freelance": "フリーランス/個人事業主",
        "team_1": "一人だけ(ソロ)",
        "team_2": "2-5人の従業員",
        "team_3": "6-20人の従業員",
        "team_4": "20人以上の従業員",
        "goal_leads": "より多くのリードを生成",
        "goal_support": "カスタマーサポートを改善",
        "goal_admin": "管理業務を自動化",
        "goal_sales": "販売プロセスを効率化",
        "nav_hunti": "Hunti AI",
        "nav_analytics": "分析ダッシュボード",
        "nav_pitches": "提案メール",
        "sidebar_title": "ユーザープロフィール",
        "reset_prefs": "設定をリセット",
        "total_req": "総リクエスト数",
        "req_hour": "リクエスト(直近1時間)",
        "hunti_title": "Hunti AI - あなたのインテリジェントな営業コンサルタント",
        "hunti_welcome": "ようこそ!ビジネスの自動化と時間節約をお手伝いします。",
        "hunti_sub": "課題について教えてください。AIがどのように解決するかをお見せします。",
        "hunti_input": "どのような課題に直面していますか?",
        "analytics_title": "分析ダッシュボード",
        "analytics_sub": "自動化キャンペーンのリアルタイムパフォーマンス指標。",
        "total_leads": "総リード数",
        "pitches_gen": "生成された提案",
        "emails_sent": "送信済みメール",
        "forms_sub": "送信済みフォーム",
        "activity_overview": "活動概要",
        "email_status": "メール配信状況",
        "recent_activity": "最近の活動ログ",
        "db_records": "データベースレコード",
        "pitch_title": "自動化提案メール",
        "pitch_sub": "リードにパーソナライズされた営業提案を自動的に生成して送信します。",
        "pitch_info": "仕組み:データベースからリードを選択すると、Huntiがパーソナライズされた提案を生成し、メールで送信します。",
        "avail_leads": "利用可能なリード",
        "btn_gen_pitch": "提案を生成",
        "btn_view_pitch": "生成された提案を表示",
        "success_gen": "提案が正常に生成されました!",
        "no_leads": "リードが見つかりません。まずリードを追加してください!",
        "no_pitches": "まだ提案が生成されていません。'提案を生成'をクリックして作成してください。",
        "footer": "2026 Hunti AI Solutions. 全著作権所有。",
        "loading": "読み込み中...",
        "generating_dashboard": "パーソナライズされたダッシュボードを生成中...",
        "generating": "生成中...",
        "suggestions": {
            "小規模事業者": [
                "メールが溢れていて十分に速く返信できない",
                "チームが反復的な手作業に時間を浪費している",
                "より多くのリードを生成する必要があるが時間がない",
                "顧客フォローアップを自動化したい"
            ],
            "エージェンシーオーナー": [
                "チームが顧客オンボーディングに時間をかけすぎている",
                "提案生成を自動化する必要がある",
                "顧客報告プロセスを効率化したい",
                "複数の顧客コミュニケーションの管理に苦労している"
            ],
            "Eコマース": [
                "注文確認と追跡を自動化する必要がある",
                "顧客が繰り返し同じ質問をする",
                "在庫更新と通知を自動化したい",
                "レビューを収集して返信するより良い方法が必要"
            ],
            "フリーランス/個人事業主": [
                "請求可能な仕事ではなく管理業務に時間をかけすぎている",
                "顧客発見プロセスを自動化する必要がある",
                "請求と支払いリマインダーを自動化したい",
                "新しい顧客を見つけて資格を得るのに助けが必要"
            ]
        }
    },
    "ar": {
        "onboarding_title": "مرحبًا بك في Hunti AI Solutions",
        "onboarding_subtitle": "دعنا نخصص لوحة التحكم الخاصة بالأتمتة في بضع ثوانٍ.",
        "q1_lang": "اختر لغتك المفضلة",
        "q2_business": "ما الذي يصف عملك بشكل أفضل؟",
        "q3_team": "ما هو حجم فريقك؟",
        "q4_goal": "ما هو هدفك الرئيسي من الأتمتة؟",
        "btn_start": "إنشاء لوحة التحكم الخاصة بي",
        "lang_en": "الإنجليزية (English)",
        "lang_hu": "المجرية (Magyar)",
        "lang_es": "الإسبانية (Español)",
        "lang_fr": "الفرنسية (Français)",
        "lang_de": "الألمانية (Deutsch)",
        "lang_it": "الإيطالية (Italiano)",
        "lang_pt": "البرتغالية (Português)",
        "lang_ru": "الروسية (Русский)",
        "lang_zh": "الصينية (中文)",
        "lang_ja": "اليابانية (日本語)",
        "lang_ar": "العربية",
        "biz_small": "صاحب عمل صغير",
        "biz_agency": "صاحب وكالة",
        "biz_ecom": "التجارة الإلكترونية",
        "biz_freelance": "مستقل / صاحب عمل فردي",
        "team_1": "وحدي فقط (فرد)",
        "team_2": "2-5 موظفين",
        "team_3": "6-20 موظف",
        "team_4": "20+ موظف",
        "goal_leads": "توليد المزيد من العملاء المحتملين",
        "goal_support": "تحسين دعم العملاء",
        "goal_admin": "أتمتة المهام الإدارية",
        "goal_sales": "تبسيط عملية المبيعات",
        "nav_hunti": "Hunti AI",
        "nav_analytics": "لوحة التحليلات",
        "nav_pitches": "البريد الإلكتروني للعروض",
        "sidebar_title": "ملف المستخدم",
        "reset_prefs": "إعادة تعيين التفضيلات",
        "total_req": "إجمالي الطلبات",
        "req_hour": "الطلبات (آخر ساعة)",
        "hunti_title": "Hunti AI - مستشار المبيعات الذكي الخاص بك",
        "hunti_welcome": "مرحبًا! أنا هنا لمساعدتك في أتمتة عملك وتوفير الوقت.",
        "hunti_sub": "أخبرني عن تحدياتك وسأريك كيف يمكن للذكاء الاصطناعي حلها.",
        "hunti_input": "ما التحدي الذي تواجهه؟",
        "analytics_title": "لوحة التحليلات",
        "analytics_sub": "مقاييس الأداء في الوقت الفعلي لحملات الأتمتة الخاصة بك.",
        "total_leads": "إجمالي العملاء المحتملين",
        "pitches_gen": "العروض المُنشأة",
        "emails_sent": "البريد الإلكتروني المرسل",
        "forms_sub": "النماذج المرسلة",
        "activity_overview": "نظرة عامة على النشاط",
        "email_status": "حالة تسليم البريد الإلكتروني",
        "recent_activity": "سجل النشاط الأخير",
        "db_records": "سجلات قاعدة البيانات",
        "pitch_title": "البريد الإلكتروني للعروض التلقائي",
        "pitch_sub": "قم بإنشاء وإرسال عروض مبيعات مخصصة لعملائك المحتملين تلقائيًا.",
        "pitch_info": "كيف يعمل: اختر العملاء المحتملين من قاعدة البيانات الخاصة بك، وسيقوم Hunti بإنشاء عروض مخصصة وإرسالها عبر البريد الإلكتروني.",
        "avail_leads": "العملاء المحتملين المتاحين",
        "btn_gen_pitch": "إنشاء العروض",
        "btn_view_pitch": "عرض العروض المُنشأة",
        "success_gen": "تم إنشاء العروض بنجاح!",
        "no_leads": "لم يتم العثور على عملاء محتملين. أضف بعض العملاء المحتملين أولاً!",
        "no_pitches": "لم يتم إنشاء عروض بعد. انقر على 'إنشاء العروض' لإنشائها.",
        "footer": "2026 Hunti AI Solutions. جميع الحقوق محفوظة.",
        "loading": "جاري التحميل...",
        "generating_dashboard": "جاري إنشاء لوحة التحكم المخصصة الخاصة بك...",
        "generating": "جاري الإنشاء...",
        "suggestions": {
            "صاحب عمل صغير": [
                "أنا غارق في رسائل البريد الإلكتروني ولا أستطيع الرد بسرعة كافية",
                "فريقي يضيع ساعات في المهام اليدوية المتكررة",
                "أحتاج إلى توليد المزيد من العملاء المحتملين لكن ليس لدي وقت",
                "أريد أتمتة متابعة عملائي"
            ],
            "صاحب وكالة": [
                "فريقي يقضي الكثير من الوقت في دمج العملاء",
                "نحتاج إلى أتمتة إنشاء العروض",
                "أريد تبسيط عملية إعداد تقارير العملاء",
                "نحن نكافح من أجل إدارة اتصالات متعددة مع العملاء"
            ],
            "التجارة الإلكترونية": [
                "أحتاج إلى أتمتة تأكيدات الطلبات والتتبع",
                "العملاء يطرحون نفس الأسئلة بشكل متكرر",
                "أريد أتمتة تحديثات المخزون والإشعارات",
                "أحتاج إلى طرق أفضل لجمع والرد على التقييمات"
            ],
            "مستقل / صاحب عمل فردي": [
                "أقضي الكثير من الوقت في الإدارة بدلاً من العمل القابل للفوترة",
                "أحتاج إلى أتمتة عملية اكتشاف العملاء",
                "أريد أتمتة الفواتير وتذكيرات الدفع",
                "أحتاج إلى مساعدة في العثور على وتأهيل عملاء جدد"
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
if 'team_size' not in st.session_state:
    st.session_state.team_size = 'Just me (Solo)'
if 'automation_goal' not in st.session_state:
    st.session_state.automation_goal = 'Generate more leads'
if 'chat_history' not in st.session_state: 
    st.session_state.chat_history = []
if 'user_id' not in st.session_state: 
    st.session_state.user_id = f"user_{int(datetime.now().timestamp())}_{random.randint(1000, 9999)}"
if 'page' not in st.session_state:
    st.session_state.page = "Hunti AI"
if 'target_page' not in st.session_state:
    st.session_state.target_page = None
if 'dashboard_generating' not in st.session_state:
    st.session_state.dashboard_generating = False

DB_NAME = "hunti.db"

def t(key):
    """Helper function to get translation"""
    keys = key.split('.')
    val = T.get(st.session_state.language, T["en"])
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
    time.sleep(2)  # Show loading for 2 seconds
    st.session_state.dashboard_generating = False
    st.rerun()

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
        if 'temp_team' not in st.session_state:
            st.session_state.temp_team = 'Just me (Solo)'
        if 'temp_goal' not in st.session_state:
            st.session_state.temp_goal = 'Generate more leads'
        
        # Language selection - REMOVED SEARCH FIELD
        st.markdown(f"**{t('q1_lang')}**")
        lang_options = {
            "English": "en",
            "Magyar": "hu",
            "Español": "es",
            "Français": "fr",
            "Deutsch": "de",
            "Italiano": "it",
            "Português": "pt",
            "Русский": "ru",
            "中文": "zh",
            "日本語": "ja",
            "العربية": "ar"
        }
        
        selected_lang_name = st.selectbox(
            "Language",
            list(lang_options.keys()),
            index=list(lang_options.keys()).index("Magyar") if st.session_state.temp_lang == 'hu' else 
                   list(lang_options.keys()).index("Español") if st.session_state.temp_lang == 'es' else 0,
            key="onboarding_lang",
            label_visibility="collapsed"
        )
        st.session_state.temp_lang = lang_options[selected_lang_name]
        st.session_state.language = st.session_state.temp_lang
        
        # Question 2: Business Type
        st.markdown(f"**{t('q2_business')}**")
        biz_options_en = ["Small Business Owner", "Agency Owner", "E-commerce", "Freelancer / Solopreneur"]
        biz_options_hu = ["Kisvállalkozás Tulajdonos", "Ügynökség Tulajdonos", "E-kereskedelem", "Szabadúszó / Egyéni Vállalkozó"]
        biz_options_es = ["Propietario de Pequeña Empresa", "Propietario de Agencia", "Comercio Electrónico", "Autónomo / Emprendedor"]
        biz_options_fr = ["Propriétaire de Petite Entreprise", "Propriétaire d'Agence", "Commerce Électronique", "Indépendant / Auto-entrepreneur"]
        biz_options_de = ["Kleinunternehmer", "Agenturinhaber", "E-Commerce", "Freiberufler / Solo-Unternehmer"]
        biz_options_it = ["Proprietario di Piccola Impresa", "Proprietario di Agenzia", "E-commerce", "Freelance / Imprenditore Solitario"]
        biz_options_pt = ["Proprietário de Pequena Empresa", "Proprietário de Agência", "Comércio Eletrônico", "Autônomo / Empreendedor Individual"]
        biz_options_ru = ["Владелец малого бизнеса", "Владелец агентства", "Электронная коммерция", "Фрилансер / Индивидуальный предприниматель"]
        biz_options_zh = ["小企业主", "代理机构所有者", "电子商务", "自由职业者/个体经营者"]
        biz_options_ja = ["小規模事業者", "エージェンシーオーナー", "Eコマース", "フリーランス/個人事業主"]
        biz_options_ar = ["صاحب عمل صغير", "صاحب وكالة", "التجارة الإلكترونية", "مستقل / صاحب عمل فردي"]
        
        if st.session_state.language == 'hu':
            biz_options = biz_options_hu
        elif st.session_state.language == 'es':
            biz_options = biz_options_es
        elif st.session_state.language == 'fr':
            biz_options = biz_options_fr
        elif st.session_state.language == 'de':
            biz_options = biz_options_de
        elif st.session_state.language == 'it':
            biz_options = biz_options_it
        elif st.session_state.language == 'pt':
            biz_options = biz_options_pt
        elif st.session_state.language == 'ru':
            biz_options = biz_options_ru
        elif st.session_state.language == 'zh':
            biz_options = biz_options_zh
        elif st.session_state.language == 'ja':
            biz_options = biz_options_ja
        elif st.session_state.language == 'ar':
            biz_options = biz_options_ar
        else:
            biz_options = biz_options_en
        
        selected_biz = st.selectbox(
            "Business Type",
            biz_options,
            index=0,
            key="onboarding_biz",
            label_visibility="collapsed"
        )
        st.session_state.temp_business = selected_biz
        
        # Question 3: Team Size
        st.markdown(f"**{t('q3_team')}**")
        team_options = [t("team_1"), t("team_2"), t("team_3"), t("team_4")]
        selected_team = st.selectbox(
            "Team Size",
            team_options,
            index=0,
            key="onboarding_team",
            label_visibility="collapsed"
        )
        st.session_state.temp_team = selected_team
        
        # Question 4: Automation Goal
        st.markdown(f"**{t('q4_goal')}**")
        goal_options = [t("goal_leads"), t("goal_support"), t("goal_admin"), t("goal_sales")]
        selected_goal = st.selectbox(
            "Automation Goal",
            goal_options,
            index=0,
            key="onboarding_goal",
            label_visibility="collapsed"
        )
        st.session_state.temp_goal = selected_goal
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button(t("btn_start"), type="primary", use_container_width=True, key="btn_onboard"):
            st.session_state.language = st.session_state.temp_lang
            st.session_state.business_type = st.session_state.temp_business
            st.session_state.team_size = st.session_state.temp_team
            st.session_state.automation_goal = st.session_state.temp_goal
            st.session_state.onboarding_complete = True
            st.session_state.dashboard_generating = True
            if 'temp_lang' in st.session_state:
                del st.session_state.temp_lang
            if 'temp_business' in st.session_state:
                del st.session_state.temp_business
            if 'temp_team' in st.session_state:
                del st.session_state.temp_team
            if 'temp_goal' in st.session_state:
                del st.session_state.temp_goal
            st.rerun()
    st.stop()

# --- PAGE TRANSITION HANDLER ---
if st.session_state.target_page and st.session_state.target_page != st.session_state.page:
    st.markdown("""
        <div class="loading-overlay">
            <div>
                <div class="loading-spinner"></div>
                <p style="color: white; margin-top: 20px; font-size: 18px;">""" + t("loading") + """</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    time.sleep(0.5)
    st.session_state.page = st.session_state.target_page
    st.session_state.target_page = None
    st.rerun()

# --- MAIN APP ---
def navigate_to_page(page_name):
    st.session_state.target_page = page_name
    st.rerun()

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