import os
import sqlite3
import datetime
import json
import pandas as pd

# Chemin absolu de la base de données
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DB_DIR, "sondage.db")

def get_connection():
    """Retourne une connexion à la base de données SQLite."""
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    """Initialise la base de données et crée les tables si nécessaires."""
    # S'assurer que le dossier data/ existe
    os.makedirs(DB_DIR, exist_ok=True)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Table des réponses du sondage
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            response_text TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    
    # Table des questions du sondage
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY,
            question_text TEXT NOT NULL
        )
    """)
    
    # Table de configuration (pour stocker la question active globale)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    
    # Table des modèles de questionnaires sauvegardés (templates)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL UNIQUE,
            data_json TEXT NOT NULL
        )
    """)
    
    # Insérer la question active par défaut (0) si elle n'existe pas
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('active_question_id', '0')")
    
    # Insérer les questions par défaut si la table questions est vide
    cursor.execute("SELECT COUNT(*) FROM questions")
    if cursor.fetchone()[0] == 0:
        from src.questions import QUESTIONS
        for q_id, q_text in QUESTIONS.items():
            cursor.execute("INSERT INTO questions (id, question_text) VALUES (?, ?)", (q_id, q_text))
            
    conn.commit()
    conn.close()

def insert_response(question_id: int, question_text: str, response_text: str) -> bool:
    """
    Insère une réponse dans la base de données.
    Retourne True si l'insertion a réussi, False si c'est un doublon récent (anti-double-clic).
    """
    cleaned_response = response_text.strip()
    if not cleaned_response:
        return False
        
    conn = get_connection()
    cursor = conn.cursor()
    
    # Prévention des doublons exacts accidentels (mêmes réponses soumises dans les 3 dernières secondes)
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    three_seconds_ago = (now_utc - datetime.timedelta(seconds=3)).isoformat()
    
    cursor.execute("""
        SELECT COUNT(*) FROM responses
        WHERE question_id = ? 
          AND LOWER(response_text) = LOWER(?)
          AND created_at > ?
    """, (question_id, cleaned_response, three_seconds_ago))
    
    count = cursor.fetchone()[0]
    if count > 0:
        conn.close()
        return False  # Bloqué car suspecté d'être un double-clic accidentel
        
    # Insertion
    cursor.execute("""
        INSERT INTO responses (question_id, question_text, response_text, created_at)
        VALUES (?, ?, ?, ?)
    """, (question_id, question_text, cleaned_response, now_utc.isoformat()))
    
    conn.commit()
    conn.close()
    return True

def get_responses(question_id: int = None) -> pd.DataFrame:
    """
    Récupère les réponses sous forme de DataFrame Pandas.
    Si question_id est spécifié, filtre sur cette question.
    """
    conn = get_connection()
    if question_id is not None:
        query = "SELECT id, question_id, question_text, response_text, created_at FROM responses WHERE question_id = ? ORDER BY id DESC"
        df = pd.read_sql_query(query, conn, params=(question_id,))
    else:
        query = "SELECT id, question_id, question_text, response_text, created_at FROM responses ORDER BY id DESC"
        df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def count_responses_by_question() -> dict:
    """
    Compte le nombre de réponses pour chaque question.
    Retourne un dictionnaire {question_id: count}.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT question_id, COUNT(*) FROM responses GROUP BY question_id")
    counts = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return counts

def delete_all_responses():
    """Vide complètement la table des réponses."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM responses")
    conn.commit()
    conn.close()

def get_active_question_id() -> int:
    """Récupère l'identifiant de la question active globale."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'active_question_id'")
    row = cursor.fetchone()
    conn.close()
    if row:
        return int(row[0])
    return 0

def set_active_question_id(question_id: int):
    """Met à jour l'identifiant de la question active globale."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('active_question_id', ?)", (str(question_id),))
    conn.commit()
    conn.close()

def get_questions_db() -> dict:
    """Récupère toutes les questions de la base de données sous forme de dictionnaire {id: text}."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, question_text FROM questions ORDER BY id ASC")
    questions = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    
    # Si la base est vide pour une raison quelconque, réinitialiser
    if not questions:
        init_db()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, question_text FROM questions ORDER BY id ASC")
        questions = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        
    return questions

def save_questions_db(questions_dict: dict):
    """
    Sauvegarde l'ensemble des questions dans la base de données.
    Supprime les questions de l'ancienne liste qui ne sont plus présentes (si le nombre a été réduit).
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Supprimer les questions qui ne font pas partie du dictionnaire de mise à jour
    current_ids = list(questions_dict.keys())
    if current_ids:
        placeholders = ",".join("?" for _ in current_ids)
        cursor.execute(f"DELETE FROM questions WHERE id NOT IN ({placeholders})", current_ids)
    else:
        cursor.execute("DELETE FROM questions")
        
    # 2. Insérer ou remplacer les nouvelles questions
    for q_id, q_text in questions_dict.items():
        cursor.execute("""
            INSERT OR REPLACE INTO questions (id, question_text)
            VALUES (?, ?)
        """, (q_id, q_text.strip()))
        
    conn.commit()
    conn.close()

def reset_questions_db():
    """Réinitialise les questions de la base de données avec les valeurs par défaut."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM questions")
    conn.commit()
    conn.close()
    init_db()

def save_template(title: str, questions_dict: dict):
    """Sauvegarde le modèle de questionnaire sous un titre unique."""
    conn = get_connection()
    cursor = conn.cursor()
    data_json = json.dumps(questions_dict)
    cursor.execute("""
        INSERT OR REPLACE INTO templates (title, data_json)
        VALUES (?, ?)
    """, (title.strip(), data_json))
    conn.commit()
    conn.close()

def get_all_templates() -> dict:
    """Récupère l'ensemble des modèles de questionnaires sous forme {titre: questions_dict}."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT title, data_json FROM templates ORDER BY title ASC")
    templates = {}
    for row in cursor.fetchall():
        try:
            templates[row[0]] = json.loads(row[1])
        except Exception:
            pass
    conn.close()
    return templates

def delete_template(title: str):
    """Supprime un modèle de questionnaire par son titre."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM templates WHERE title = ?", (title,))
    conn.commit()
    conn.close()
