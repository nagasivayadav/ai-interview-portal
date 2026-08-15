import sqlite3
import hashlib
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "interview_portal.db"

def connect():
    return sqlite3.connect(DB_PATH)

def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def init_db():
    con = connect()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS interviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            interview_type TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            score REAL NOT NULL,
            question_count INTEGER NOT NULL,
            results_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    con.commit()
    con.close()

def create_user(name, email, password):
    con = connect()
    try:
        con.execute(
            "INSERT INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)",
            (name.strip(), email.strip().lower(), hash_password(password),
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        con.commit()
        return True, "Account created successfully."
    except sqlite3.IntegrityError:
        return False, "An account with this email already exists."
    finally:
        con.close()

def authenticate_user(email, password):
    con = connect()
    row = con.execute(
        "SELECT id,name,email FROM users WHERE email=? AND password_hash=?",
        (email.strip().lower(), hash_password(password))
    ).fetchone()
    con.close()

    if row:
        return {"id": row[0], "name": row[1], "email": row[2]}
    return None

def save_interview(user_id, meta, score, results):
    con = connect()
    con.execute("""
        INSERT INTO interviews(
            user_id,role,interview_type,difficulty,score,
            question_count,results_json,created_at
        ) VALUES(?,?,?,?,?,?,?,?)
    """, (
        user_id,
        meta["role"],
        meta["type"],
        meta["difficulty"],
        float(score),
        len(results),
        json.dumps(results),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    con.commit()
    con.close()

def get_user_interviews(user_id):
    con = connect()
    rows = con.execute("""
        SELECT role, interview_type, difficulty, score,
               question_count, created_at
        FROM interviews
        WHERE user_id=?
        ORDER BY id DESC
    """, (user_id,)).fetchall()
    con.close()

    return [
        {
            "role": r[0],
            "interview_type": r[1],
            "difficulty": r[2],
            "score": r[3],
            "question_count": r[4],
            "created_at": r[5],
        }
        for r in rows
    ]

def get_user_stats(user_id):
    con = connect()
    row = con.execute("""
        SELECT COUNT(*), COALESCE(AVG(score),0),
               COALESCE(MAX(score),0)
        FROM interviews WHERE user_id=?
    """, (user_id,)).fetchone()

    latest = con.execute("""
        SELECT role FROM interviews
        WHERE user_id=? ORDER BY id DESC LIMIT 1
    """, (user_id,)).fetchone()
    con.close()

    return {
        "count": row[0],
        "avg": row[1],
        "best": row[2],
        "latest_role": latest[0] if latest else None,
    }
