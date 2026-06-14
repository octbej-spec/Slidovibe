import streamlit as st
import os
import re
import pandas as pd
from src.database import (
    init_db,
    insert_response,
    get_responses,
    count_responses_by_question,
    delete_all_responses,
    get_active_question_id,
    set_active_question_id,
    get_questions_db,
    save_questions_db,
    reset_questions_db
)
from src.wordcloud_utils import generate_wordcloud, FRENCH_STOP_WORDS
from src.export_utils import export_to_csv, export_to_excel

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Radar Ingénierie STM",
    page_icon="📡",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Initialisation de la base de données SQLite
init_db()

# Charger les questions de la base de données
QUESTIONS = get_questions_db()

# Injection CSS personnalisé pour le style STM (Bleu #005696, fond clair, boutons larges)
st.markdown("""
    <style>
    /* Style de la bannière d'en-tête principale */
    .stm-header {
        background-color: #005696;
        padding: 24px;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .stm-header h1 {
        color: white !important;
        margin: 0 !important;
        font-size: 2.2rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.5px;
    }
    .stm-header p {
        margin: 8px 0 0 0 !important;
        font-size: 1.1rem !important;
        opacity: 0.9;
    }
    
    /* Conteneur principal */
    .block-container {
        padding-top: 2rem !important;
    }
    
    /* Boutons de soumission larges */
    div.stButton > button:first-child {
        background-color: #005696;
        color: white;
        border: none;
        padding: 12px 24px;
        font-size: 16px;
        border-radius: 6px;
        width: 100%;
        transition: all 0.3s ease;
        font-weight: bold;
    }
    div.stButton > button:first-child:hover {
        background-color: #003d6b;
        color: white;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
    }
    
    /* Style de la question active */
    .question-card {
        background-color: #FFFFFF;
        border-left: 5px solid #005696;
        padding: 20px;
        border-radius: 4px 12px 12px 4px;
        margin-bottom: 25px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .question-card h3 {
        margin: 0;
        color: #1E293B;
    }
    </style>
""", unsafe_allow_html=True)

# Bannière d'en-tête STM
st.markdown("""
    <div class="stm-header">
        <h1>Radar Ingénierie STM</h1>
        <p>Sondage interactif d'équipe en direct</p>
    </div>
""", unsafe_allow_html=True)

# Sidebar : Sélection du mode
st.sidebar.image("https://www.stm.info/themes/custom/stm/logo.svg", width=120, output_format="PNG")
st.sidebar.markdown("---")
mode = st.sidebar.radio(
    "Navigation :",
    ["Participant 🙋‍♂️", "Animateur 🎙️"],
    index=0
)

# Option de rafraîchissement automatique uniquement en mode Animateur
live_update = False
if mode == "Animateur 🎙️":
    st.sidebar.markdown("---")
    live_update = st.sidebar.checkbox("Mise à jour en direct (2s) 🔄", value=True)

# ----------------- MODE PARTICIPANT -----------------
if mode == "Participant 🙋‍♂️":
    st.subheader("📍 Votre participation en temps réel")
    
    # Récupérer la question active globale en DB
    active_qid = get_active_question_id()
    active_q_text = QUESTIONS.get(active_qid, f"Question {active_qid}")
    
    # Initialiser l'état de soumission
    if "submitted_question_id" not in st.session_state:
        st.session_state.submitted_question_id = None
        
    # Si la question active globale change, on réinitialise l'état pour permettre une nouvelle saisie
    if st.session_state.submitted_question_id != active_qid:
        st.session_state.submitted_question_id = None
        
    # Si toutes les réponses ont été effacées en DB (réinitialisation),
    # on déverrouille l'écran pour permettre à nouveau la saisie.
    if get_responses(active_qid).empty:
        st.session_state.submitted_question_id = None
        
    # Affichage de la question active de façon élégante
    st.markdown(f"""
        <div class="question-card">
            <span style="font-size: 0.85rem; font-weight: bold; color: #005696; text-transform: uppercase; letter-spacing: 0.5px;">Question active</span>
            <h3 style="margin-top: 5px; font-size: 1.35rem;">{active_q_text}</h3>
        </div>
    """, unsafe_allow_html=True)
    
    # Si le participant a déjà soumis sa réponse pour cette question
    if st.session_state.submitted_question_id == active_qid:
        st.success("🎉 Réponse enregistrée ! Merci pour votre participation.")
        st.info("⌛ En attente de la prochaine question...")
        
        # Auto-refresh passif de 3s en attente du changement de question (évité en test unitaire)
        import sys
        is_testing = "streamlit.testing" in sys.modules
        if not is_testing:
            import time
            time.sleep(3)
            st.rerun()
    else:
        # Initialisation de la session state pour éviter les doubles clics rapides
        if "last_submitted" not in st.session_state:
            st.session_state.last_submitted = None

        # Formulaire de réponse (vide le champ après soumission)
        with st.form("participant_form", clear_on_submit=True):
            user_input = st.text_input(
                "Votre réponse (un mot, une courte phrase) :",
                placeholder="Tapez ici...",
                max_chars=100
            )
            submit_btn = st.form_submit_button("Envoyer ma réponse")
            
            if submit_btn:
                cleaned = user_input.strip()
                if not cleaned:
                    st.error("⚠️ La réponse ne peut pas être vide. Veuillez saisir du texte.")
                elif st.session_state.last_submitted == cleaned:
                    st.warning("⚠️ Vous venez déjà de soumettre cette réponse. Modifiez-la pour en envoyer une autre.")
                else:
                    # Tentative d'insertion en base de données
                    success = insert_response(active_qid, active_q_text, cleaned)
                    if success:
                        st.session_state.last_submitted = cleaned
                        st.session_state.submitted_question_id = active_qid
                        st.rerun() # Recharger immédiatement pour basculer sur l'écran "En attente"
                    else:
                        st.warning("⚠️ Cette réponse a été enregistrée récemment. Saisissez une idée différente.")

# ----------------- MODE ANIMATEUR -----------------
else:
    # Lecture sécurisée du mot de passe admin configuré
    admin_pwd = None
    try:
        admin_pwd = st.secrets.get("ADMIN_PASSWORD")
    except Exception:
        pass
        
    if not admin_pwd:
        admin_pwd = os.environ.get("ADMIN_PASSWORD")
    
    authenticated = True
    if admin_pwd:
        authenticated = False
        st.sidebar.subheader("🔒 Connexion requis")
        pwd_input = st.sidebar.text_input("Mot de passe Animateur :", type="password")
        if pwd_input == admin_pwd:
            authenticated = True
        elif pwd_input:
            st.sidebar.error("Mot de passe incorrect")
    else:
        st.sidebar.warning("⚠️ Aucun mot de passe admin configuré (ADMIN_PASSWORD). Accès libre en développement.")
        
    if not authenticated:
        st.info("Veuillez saisir le mot de passe administrateur dans le volet de gauche pour déverrouiller le Dashboard Animateur.")
    else:
        st.subheader("🎙️ Tableau de bord de l'animateur")
        
        # --- CONFIGURATION DYNAMIQUE DES QUESTIONS ---
        st.markdown("### ⚙️ Configuration des questions")
        
        # 1. Réinitialiser les questions par défaut
        # 2. Choisir le nombre de questions
        col_reset, col_num = st.columns([1, 1])
        with col_reset:
            st.write("Réinitialiser les questions :")
            if st.button("Réinitialiser par défaut 🔄", key="reset_questions_btn"):
                reset_questions_db()
                delete_all_responses() # Effacer également toutes les réponses !
                st.success("Questions réinitialisées et réponses effacées !")
                st.rerun()
                
        with col_num:
            current_questions = get_questions_db()
            num_q_current = len(current_questions)
            num_q_new = st.number_input(
                "Nombre de questions (1-10) :",
                min_value=1,
                max_value=10,
                value=num_q_current,
                step=1,
                key="num_questions_input"
            )
            
        # 3. Édition des questions
        st.write("Modifier le libellé des questions :")
        with st.form("edit_questions_form"):
            updated_questions = {}
            for idx in range(num_q_new):
                default_text = current_questions.get(idx, f"Question {idx}")
                updated_questions[idx] = st.text_input(
                    f"Question {idx} :",
                    value=default_text,
                    key=f"q_input_{idx}"
                )
            
            save_btn = st.form_submit_button("Enregistrer les questions 💾")
            if save_btn:
                empty_found = False
                for idx, text in updated_questions.items():
                    if not text.strip():
                        empty_found = True
                        st.error(f"La Question {idx} ne peut pas être vide.")
                        break
                
                if not empty_found:
                    save_questions_db(updated_questions)
                    st.success("Questions enregistrées avec succès !")
                    st.rerun()

        st.markdown("---")
        st.markdown("### 📢 Partager le sondage")
        
        # Obtenir l'IP locale pour préremplir l'adresse de partage
        import socket
        import urllib.parse
        def get_local_ip():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
                return ip
            except Exception:
                return "localhost"
                
        local_ip = get_local_ip()
        port_config = 8501
        try:
            import toml
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".streamlit", "config.toml")
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config_data = toml.load(f)
                    port_config = config_data.get("server", {}).get("port", 8501)
        except Exception:
            pass
            
        # Détection de l'environnement Streamlit Cloud (/mount/src/slidovibe)
        is_streamlit_cloud = "/mount/src" in os.path.abspath(__file__)
        
        if is_streamlit_cloud:
            default_url = "https://radar-ingenierie-stm.streamlit.app"
        else:
            default_url = f"http://{local_ip}:{port_config}"
        
        url_partage = st.text_input(
            "Adresse de l'application à partager aux participants :",
            value=default_url,
            help="Modifiez cette adresse si l'application est hébergée sur Streamlit Cloud ou un autre nom de domaine."
        )
        
        col_share_1, col_share_2 = st.columns([2, 1])
        with col_share_1:
            st.write("Copier le lien d'accès :")
            st.code(url_partage, language=None)
            st.caption("💡 Cliquez sur le bouton de copie en haut à droite du cadre ci-dessus.")
            
        with col_share_2:
            st.write("Code QR de participation :")
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(url_partage)}"
            st.image(qr_url, width=130, caption="Scanner pour répondre")

        st.markdown("---")
        st.markdown("### 📡 Contrôle du direct")
        
        # Charger les questions de la base de données
        QUESTIONS = get_questions_db()
        q_keys = list(QUESTIONS.keys())
        
        # 1. Gestion de la question active
        current_active_qid = get_active_question_id()
        if current_active_qid not in q_keys:
            current_active_qid = q_keys[0] if q_keys else 0
            set_active_question_id(current_active_qid)
        
        try:
            default_index = q_keys.index(current_active_qid)
        except ValueError:
            default_index = 0
            
        selected_qid = st.selectbox(
            "Définir la question active pour tous les participants :",
            q_keys,
            index=default_index,
            format_func=lambda x: f"Q{x} : {QUESTIONS[x]}"
        )
        
        # Si l'animateur change la question active, on met à jour la base de données
        if selected_qid != current_active_qid:
            set_active_question_id(selected_qid)
            st.success(f"La question active est maintenant la Question {selected_qid} !")
            st.rerun()
            
        # 2. Statistiques en temps réel
        counts = count_responses_by_question()
        active_q_count = counts.get(selected_qid, 0)
        total_count = sum(counts.values())
        
        st.markdown("### 📊 Statistiques rapides")
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="Réponses (Question active)", value=active_q_count)
        with col2:
            st.metric(label="Total des réponses récoltées", value=total_count)
            
        # Onglets d'analyse et de gestion
        tab_cloud, tab_table, tab_settings = st.tabs([
            "☁️ Nuage de mots & Mots fréquents", 
            "📋 Tableau des réponses", 
            "⚙️ Exporter & Réinitialiser"
        ])
        
        # Charger les réponses de la question sélectionnée
        df_active = get_responses(selected_qid)
        
        # Onglet 1 : Nuage de mots
        with tab_cloud:
            if df_active.empty:
                st.info("Aucune réponse pour le moment pour cette question. Invitez les participants à répondre !")
            else:
                st.subheader("Nuage de mots clés")
                fig = generate_wordcloud(df_active)
                if fig:
                    st.pyplot(fig)
                else:
                    st.warning("Impossible de générer le nuage de mots. (Aucun contenu textuel exploitable après filtrage)")
                
                # Top 5 des mots fréquents
                words = []
                for text in df_active['response_text'].dropna().astype(str):
                    # Trouver tous les mots en minuscules sans ponctuation
                    for word in re.findall(r'\b\w+\b', text.lower()):
                        if word not in FRENCH_STOP_WORDS and len(word) > 1:
                            words.append(word)
                
                if words:
                    st.markdown("---")
                    st.subheader("📈 Top 5 des mots les plus fréquents")
                    word_series = pd.Series(words)
                    top_words = word_series.value_counts().head(5).reset_index()
                    top_words.columns = ['Mot', 'Occurrences']
                    st.dataframe(top_words, use_container_width=True, hide_index=True)
            
            # Bouton de contrôle pour passer à la question suivante en direct
            st.markdown("---")
            col_next_1, col_next_2 = st.columns([2, 1])
            with col_next_2:
                if st.button("➡️ Question suivante", key="next_question_wordcloud_btn", use_container_width=True):
                    q_keys = list(QUESTIONS.keys())
                    if q_keys:
                        try:
                            curr_idx = q_keys.index(selected_qid)
                            next_idx = (curr_idx + 1) % len(q_keys)
                            next_qid = q_keys[next_idx]
                        except ValueError:
                            next_qid = q_keys[0]
                        set_active_question_id(next_qid)
                        st.rerun()
        
        # Onglet 2 : Tableau des réponses
        with tab_table:
            if df_active.empty:
                st.info("Aucune réponse enregistrée pour cette question.")
            else:
                st.subheader("Réponses brutes")
                # Formatage du dataframe pour affichage propre
                df_display = df_active[['response_text', 'created_at']].copy()
                df_display.columns = ["Texte de la réponse", "Reçu le (UTC)"]
                st.dataframe(df_display, use_container_width=True, hide_index=True)
                
        # Onglet 3 : Gestion & Exports
        with tab_settings:
            st.subheader("📥 Téléchargement des résultats")
            df_all = get_responses()
            
            if df_all.empty:
                st.info("Aucune donnée disponible pour l'export.")
            else:
                csv_data = export_to_csv(df_all)
                excel_data = export_to_excel(df_all)
                
                st.write("Télécharger les réponses de **toutes** les questions :")
                col_csv, col_xlsx = st.columns(2)
                with col_csv:
                    st.download_button(
                        label="📥 Exporter en CSV (compatible Excel)",
                        data=csv_data,
                        file_name="radar_ingenierie_stm_export.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                with col_xlsx:
                    st.download_button(
                        label="📥 Exporter en Excel",
                        data=excel_data,
                        file_name="radar_ingenierie_stm_export.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
            
            st.markdown("---")
            st.subheader("🚨 Zone de danger")
            st.write("Supprimer définitivement l'historique complet du sondage.")
            
            confirm_reset = st.checkbox("Je confirme vouloir supprimer TOUTES les réponses du sondage.")
            
            # Bouton de suppression qui n'est cliquable que si la checkbox de confirmation est cochée
            reset_button = st.button(
                "Réinitialiser toutes les réponses",
                type="secondary",
                disabled=not confirm_reset
            )
            
            if reset_button and confirm_reset:
                delete_all_responses()
                st.success("Toutes les réponses ont été effacées avec succès !")
                st.rerun()

        # Rerun toutes les 2 secondes pour la mise à jour en direct (si coché et pas en cours de test)
        import sys
        is_testing = "streamlit.testing" in sys.modules
        
        if live_update and not is_testing:
            import time
            time.sleep(2)
            st.rerun()
