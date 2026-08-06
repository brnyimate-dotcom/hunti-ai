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

    # Form Submissions Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS form_submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, pitch_id INTEGER, company_name TEXT, url TEXT, status TEXT DEFAULT 'success', submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (pitch_id) REFERENCES pitches (id))''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS usage_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, action TEXT NOT NULL, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    conn.commit()
    conn.close()
    
    # Run CRM migrations safely (adds columns if they don't exist)
    migrate_crm()
    
    print(f"✅ Database '{DB_NAME}' initialized successfully!")

def migrate_crm():
    """Add CRM columns to the leads table if they don't exist yet."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(leads)")
    existing_columns = [row[1] for row in cursor.fetchall()]

    if 'status' not in existing_columns:
        cursor.execute("ALTER TABLE leads ADD COLUMN status TEXT DEFAULT 'new'")
        print("➕ Added CRM column: status")
        
    if 'follow_up_date' not in existing_columns:
        cursor.execute("ALTER TABLE leads ADD COLUMN follow_up_date DATE")
        print("➕ Added CRM column: follow_up_date")
        
    if 'notes' not in existing_columns:
        cursor.execute("ALTER TABLE leads ADD COLUMN notes TEXT")
        print("➕ Added CRM column: notes")

    conn.commit()
    conn.close()

def add_lead(company_name, website='', phone='', address='', rating=0.0,
             status='new', follow_up_date=None, notes=''):
    """Add a lead with CRM fields."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO leads
        (company_name, address, website, phone, rating, status, follow_up_date, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (company_name, address, website, phone, rating, status, follow_up_date, notes))
    conn.commit()
    lead_id = cursor.lastrowid
    conn.close()
    print(f"✅ Lead #{lead_id} added: {company_name} [{status}]")
    return lead_id

def update_lead(lead_id, status=None, follow_up_date=None, notes=None):
    """Update CRM fields of an existing lead."""
    conn = get_connection()
    cursor = conn.cursor()
    if status is not None:
        cursor.execute("UPDATE leads SET status = ? WHERE id = ?", (status, lead_id))
    if follow_up_date is not None:
        cursor.execute("UPDATE leads SET follow_up_date = ? WHERE id = ?", (follow_up_date, lead_id))
    if notes is not None:
        cursor.execute("UPDATE leads SET notes = ? WHERE id = ?", (notes, lead_id))
    conn.commit()
    conn.close()
    print(f"✅ Lead #{lead_id} updated")

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