import sqlite3
import os

DB_NAME = "hunti.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT, company_name TEXT NOT NULL, address TEXT, website TEXT, phone TEXT, rating REAL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS pitches (
        id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER, pitch_text TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (lead_id) REFERENCES leads (id))''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS emails (
        id INTEGER PRIMARY KEY AUTOINCREMENT, pitch_id INTEGER, recipient_email TEXT NOT NULL, subject TEXT, status TEXT DEFAULT 'sent', sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (pitch_id) REFERENCES pitches (id))''')

    # NEW: Form Submissions Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS form_submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, pitch_id INTEGER, company_name TEXT, url TEXT, status TEXT DEFAULT 'success', submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (pitch_id) REFERENCES pitches (id))''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS usage_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, action TEXT NOT NULL, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    conn.commit()
    conn.close()
    print(f"✅ Database '{DB_NAME}' initialized successfully!")

def log_form_submission(pitch_id: int, company_name: str, url: str) -> None:
    """Log a successful website form submission."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO form_submissions (pitch_id, company_name, url, status)
        VALUES (?, ?, ?, 'success')
    ''', (pitch_id, company_name, url))
    conn.commit()
    conn.close()

def get_form_submission_count() -> int:
    """Get total number of form submissions."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM form_submissions')
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_lead_count_from_db() -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM leads')
    count = cursor.fetchone()[0]
    conn.close()
    return count

if __name__ == "__main__":
    init_db()