import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta

DATABASE_NAME = 'ad_bot.db'

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            balance REAL DEFAULT 0,
            invited_by INTEGER,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ads (
            ad_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            url TEXT NOT NULL,
            reward REAL DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')


        cursor.execute('''
        CREATE TABLE IF NOT EXISTS errors (
            error_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            error_details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ad_views (
            view_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            ad_id INTEGER,
            view_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_confirmed BOOLEAN DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (ad_id) REFERENCES ads (ad_id)
        )
        ''')

        conn.commit()        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS referrals (
            referral_id INTEGER PRIMARY KEY AUTOINCREMENT,
            inviter_id INTEGER NOT NULL,
            invited_id INTEGER NOT NULL UNIQUE,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (inviter_id) REFERENCES users (user_id),
            FOREIGN KEY (invited_id) REFERENCES users (user_id)
        )
        ''')
        
        conn.commit()

def get_ad_id_by_view(view_id):
    """الحصول على معرف الإعلان من معرف المشاهدة"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT ad_id FROM ad_views WHERE view_id = ?', (view_id,))
        result = cursor.fetchone()
        return result['ad_id'] if result else None

def log_error(user_id, error_details):
    """تسجيل الأخطاء في قاعدة البيانات"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO errors (user_id, error_details, timestamp)
        VALUES (?, ?, datetime('now'))
        ''', (user_id, str(error_details)))
        conn.commit()

def get_last_ad_view(user_id, ad_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        SELECT view_date FROM ad_views 
        WHERE user_id = ? AND ad_id = ?
        ORDER BY view_date DESC LIMIT 1
        ''', (user_id, ad_id))
        result = cursor.fetchone()
        return result['view_date'] if result else None

def calculate_cooldown(last_view, cooldown_hours):
    last_view = datetime.strptime(last_view, '%Y-%m-%d %H:%M:%S')
    now = datetime.now()
    remaining = (last_view + timedelta(hours=cooldown_hours)) - now
    return round(remaining.total_seconds() / 3600) if remaining.total_seconds() > 0 else 0

def add_ad_view(user_id, ad_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO ad_views (user_id, ad_id, is_confirmed)
        VALUES (?, ?, 0)
        ''', (user_id, ad_id))
        conn.commit()
        return cursor.lastrowid

def confirm_ad_view(view_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        UPDATE ad_views 
        SET is_confirmed = 1 
        WHERE view_id = ?
        ''', (view_id,))
        conn.commit()

def get_user_balance(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        return result['balance'] if result else 0

def update_balance(user_id, amount):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        UPDATE users 
        SET balance = balance + ? 
        WHERE user_id = ?
        ''', (amount, user_id))
        conn.commit()

def add_user(user_id, username, first_name, last_name, invited_by=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, invited_by)
        VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name, invited_by))
        conn.commit()

def get_user_referrals(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        SELECT COUNT(*) as count FROM referrals 
        WHERE inviter_id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        return result['count'] if result else 0

def add_referral(inviter_id, invited_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO referrals (inviter_id, invited_id)
        VALUES (?, ?)
        ''', (inviter_id, invited_id))
        conn.commit()

def get_user_info(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return cursor.fetchone()
