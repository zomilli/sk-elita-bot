import sqlite3

DB_NAME = "voice_stats.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Таблица для логов голосовых чатов
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
    
    # Автоматически добавляем колонку user_label, если база была создана ранее со старой структурой
    cursor.execute("PRAGMA table_info(voice_logs)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'user_label' not in columns:
        cursor.execute("ALTER TABLE voice_logs ADD COLUMN user_label TEXT")
    
    # Таблица для полученных ачивок
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            user_id INTEGER,
            achievement_code TEXT,
            granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(chat_id, user_id, achievement_code)
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

def get_user_total_stats(chat_id: int, user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 
            SUM(CASE WHEN event_type = 'started' THEN 1 ELSE 0 END) as total_started,
            SUM(CASE WHEN event_type = 'ended' THEN 1 ELSE 0 END) as total_ended,
            SUM(duration) as total_duration
        FROM voice_logs
        WHERE chat_id = ? AND user_id = ?
    ''', (chat_id, user_id))
    row = cursor.fetchone()
    conn.close()
    
    total_started = row[0] or 0
    total_ended = row[1] or 0
    total_duration = row[2] or 0
    return total_started, total_ended, total_duration

def give_achievement(chat_id: int, user_id: int, code: str) -> bool:
    """Возвращает True, если ачивка была выдана впервые."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO user_achievements (chat_id, user_id, achievement_code)
            VALUES (?, ?, ?)
        ''', (chat_id, user_id, code))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def get_user_achievements(chat_id: int, user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT achievement_code FROM user_achievements
        WHERE chat_id = ? AND user_id = ?
    ''', (chat_id, user_id))
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]
