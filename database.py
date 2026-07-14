import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_data.db")

def get_db_connection():
    """SQLite ma'lumotlar bazasiga ulanish yaratish"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Natijalarni lug'at (dict) ko'rinishida olish uchun
    return conn

def init_db():
    """Ma'lumotlar bazasi jadvallarini yaratish"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # users jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                chat_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                is_banned INTEGER DEFAULT 0,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # messages jadvali (rolling history uchun)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                role TEXT,
                content TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES users (chat_id)
            )
        """)
        conn.commit()

def add_or_update_user(chat_id, username, first_name, last_name):
    """Foydalanuvchini bazaga qo'shish yoki ma'lumotlarini yangilash"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (chat_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_name = excluded.last_name
        """, (chat_id, username, first_name, last_name))
        conn.commit()

def save_chat_message(chat_id, role, content):
    """Suhbat xabarini bazaga saqlash"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO messages (chat_id, role, content)
            VALUES (?, ?, ?)
        """, (chat_id, role, content))
        conn.commit()

def get_chat_history(chat_id, limit=10):
    """Foydalanuvchining oxirgi N ta xabarlar tarixini olish"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Oxirgi limit ta xabarni olib, vaqt bo'yicha to'g'ri tartiblash (ascending)
        cursor.execute("""
            SELECT role, content FROM (
                SELECT id, role, content FROM messages 
                WHERE chat_id = ? 
                ORDER BY id DESC 
                LIMIT ?
            ) ORDER BY id ASC
        """, (chat_id, limit))
        rows = cursor.fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in rows]

def clear_chat_history(chat_id):
    """Foydalanuvchining chat tarixini tozalash (/reset buyrug'i uchun)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        conn.commit()

def is_banned(chat_id):
    """Foydalanuvchi blocklanganligini tekshirish"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT is_banned FROM users WHERE chat_id = ?", (chat_id,))
        row = cursor.fetchone()
        if row:
            return bool(row["is_banned"])
        return False

def set_ban_status(chat_id, is_banned_status):
    """Foydalanuvchini blocklash yoki blokdan ochish"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_banned = ? WHERE chat_id = ?", (1 if is_banned_status else 0, chat_id))
        conn.commit()
        return cursor.rowcount > 0  # Agar o'zgarish bo'lsa True, bo'lmasa False

def get_stats():
    """Admin panel uchun bot statistikasini olish"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Jami a'zolar
        cursor.execute("SELECT COUNT(*) as cnt FROM users")
        total_users = cursor.fetchone()["cnt"]
        
        # Blocklangan a'zolar
        cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE is_banned = 1")
        banned_users = cursor.fetchone()["cnt"]
        
        # Jami xabarlar soni
        cursor.execute("SELECT COUNT(*) as cnt FROM messages")
        total_messages = cursor.fetchone()["cnt"]
        
        # Oxirgi 24 soatda faol bo'lgan a'zolar
        cursor.execute("""
            SELECT COUNT(DISTINCT chat_id) as cnt FROM messages 
            WHERE timestamp >= datetime('now', '-1 day')
        """)
        active_24h = cursor.fetchone()["cnt"]

        return {
            "total_users": total_users,
            "banned_users": banned_users,
            "total_messages": total_messages,
            "active_24h": active_24h
        }

def get_all_active_users():
    """Taqiqlanmagan (faol) barcha a'zolarning chat_id larini olish (broadcast uchun)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id FROM users WHERE is_banned = 0")
        rows = cursor.fetchall()
        return [row["chat_id"] for row in rows]

def get_user_info(chat_id):
    """Muayyan a'zoning batafsil ma'lumotlarini olish"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT chat_id, username, first_name, last_name, is_banned, joined_at
            FROM users WHERE chat_id = ?
        """, (chat_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
