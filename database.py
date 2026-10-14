import sqlite3

DB_NAME = "voice_stats.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS voice_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            user_id INTEGER,
            display_name TEXT,
            action TEXT,
            duration INTEGER DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def log_event(chat_id: int, user_id: int, display_name: str, action: str, duration: int = 0):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO voice_logs (chat_id, user_id, display_name, action, duration)
        VALUES (?, ?, ?, ?, ?)
    """, (chat_id, user_id, display_name, action, duration))
    conn.commit()
    conn.close()

def get_weekly_stats(chat_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            display_name,
            SUM(CASE WHEN action = 'started' THEN 1 ELSE 0 END) as started_count,
            SUM(CASE WHEN action = 'ended' THEN 1 ELSE 0 END) as ended_count,
            SUM(duration) as total_duration
        FROM voice_logs
        WHERE chat_id = ? AND timestamp >= datetime('now', '-7 days')
        GROUP BY user_id
        ORDER BY total_duration DESC
    """, (chat_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows