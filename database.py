import sqlite3
import os

# This is the name of our database file
DB_NAME = "hunti.db"

def get_connection():
    """Connect to the SQLite database (creates the file if it doesn't exist)."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # This lets us access columns by name
    return conn

def init_db():
    """Create the tables if they don't exist yet."""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Table for Leads (Companies we find)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            address TEXT,
            website TEXT,
            phone TEXT,
            rating REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. Table for Pitches (AI generated emails)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pitches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER,
            pitch_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES leads (id)
        )
    ''')

    # 3. Table for Email History (Tracking what we sent)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pitch_id INTEGER,
            recipient_email TEXT NOT NULL,
            subject TEXT,
            status TEXT DEFAULT 'sent',
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pitch_id) REFERENCES pitches (id)
        )
    ''')

    # 4. Table for Usage Logs (Rate limiting & Bot prevention)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            action TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    print(f"✅ Database '{DB_NAME}' initialized successfully!")

# Run this immediately to create the file
if __name__ == "__main__":
    init_db()