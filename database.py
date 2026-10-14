import sqlite3
from datetime import datetime

DB_NAME = "voice_stats.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS voice_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            user_id INTEGER,
            user_label TEXT,
            event_type TEXT,
            duration INTEGER DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def log_event(chat_id: int, user_id: int, user_label: str, event_type: str, duration: int = 0):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO voice_logs (chat_id, user_id, user_label, event_type, duration)
        VALUES (?, ?, ?, ?, ?)
    ''', (chat_id, user_id, user_label, event_type, duration))
    conn.commit()
    conn.close()

def get_daily_stats(chat_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Сброс в 00:00 по МСК (UTC+3)
    cursor.execute('''
        SELECT 
            user_label,
            SUM(CASE WHEN event_type = 'started' THEN 1 ELSE 0 END) as started_count,
            SUM(CASE WHEN event_type = 'ended' THEN 1 ELSE 0 END) as ended_count,
            SUM(duration) as total_duration
        FROM voice_logs
        WHERE chat_id = ? 
          AND timestamp >= datetime('now', '+3 hours', 'start of day', '-3 hours')
        GROUP BY user_id
        ORDER BY total_duration DESC
    ''', (chat_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows
