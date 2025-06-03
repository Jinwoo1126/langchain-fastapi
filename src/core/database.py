import sqlite3
import jwt
import datetime
import bcrypt
from typing import Optional
from pathlib import Path
from .settings import settings

DB_PATH = Path(__file__).parent.parent.parent / "users.db"

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # 사용자 테이블 생성
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 세션 테이블 생성
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()

def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())

def create_user(username: str, password: str) -> bool:
    try:
        conn = get_db()
        c = conn.cursor()
        password_hash = hash_password(password)
        c.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                 (username, password_hash))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def verify_user(username: str, password: str) -> Optional[dict]:
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = c.fetchone()
    conn.close()
    
    if user and verify_password(password, user['password_hash']):
        return dict(user)
    return None

def create_session(user_id: int) -> str:
    # JWT 토큰 생성
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    token = jwt.encode(
        {
            'user_id': user_id,
            'exp': expires_at
        },
        settings.SECRET_KEY,
        algorithm='HS256'
    )
    
    # DB에 세션 저장
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)',
             (user_id, token, expires_at))
    conn.commit()
    conn.close()
    
    return token

def verify_session(token: str) -> Optional[dict]:
    try:
        # JWT 토큰 검증
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        user_id = payload['user_id']
        
        # DB에서 세션 확인
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT u.* FROM users u
            JOIN sessions s ON u.id = s.user_id
            WHERE s.token = ? AND s.expires_at > CURRENT_TIMESTAMP
        ''', (token,))
        user = c.fetchone()
        conn.close()
        
        if user:
            return dict(user)
    except jwt.ExpiredSignatureError:
        delete_session(token)
    except jwt.InvalidTokenError:
        pass
    return None

def delete_session(token: str):
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM sessions WHERE token = ?', (token,))
    conn.commit()
    conn.close()

# 데이터베이스 초기화
init_db()

# 기본 관리자 계정 생성
if not verify_user("admin", "admin"):
    create_user("admin", "admin")
    create_user("jinwoo1126", "jinwoo1126!")
