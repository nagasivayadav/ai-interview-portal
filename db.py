import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "interview_portal.db")


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS interviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT,
                interview_type TEXT,
                difficulty TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                interview_id INTEGER NOT NULL,
                question TEXT,
                answer TEXT,
                score REAL,
                feedback TEXT,
                category TEXT DEFAULT 'interview',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(interview_id) REFERENCES interviews(id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS typing_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                wpm REAL,
                accuracy REAL,
                duration_seconds REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS communication_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                pace_score REAL,
                presence_score REAL,
                overall_score REAL,
                feedback TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)


def create_user(username, password):
    with get_conn() as conn:
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))


def get_user(username, password):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?", (username, password)
        ).fetchone()
        return dict(row) if row else None


def create_interview(user_id, role, interview_type, difficulty):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO interviews (user_id, role, interview_type, difficulty) VALUES (?, ?, ?, ?)",
            (user_id, role, interview_type, difficulty),
        )
        return cur.lastrowid


def get_user_by_id(user_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return dict(row) if row else None


def save_result(interview_id, question, answer, score, feedback, category="interview"):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO results (interview_id, question, answer, score, feedback, category) VALUES (?, ?, ?, ?, ?, ?)",
            (interview_id, question, answer, score, feedback, category),
        )


def save_typing_result(user_id, wpm, accuracy, duration_seconds):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO typing_results (user_id, wpm, accuracy, duration_seconds) VALUES (?, ?, ?, ?)",
            (user_id, wpm, accuracy, duration_seconds),
        )


def save_communication_result(user_id, pace_score, presence_score, overall_score, feedback):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO communication_results
               (user_id, pace_score, presence_score, overall_score, feedback)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, pace_score, presence_score, overall_score, feedback),
        )


def get_user_results(user_id):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT r.*, i.role, i.interview_type, i.difficulty, i.created_at as interview_date
               FROM results r
               JOIN interviews i ON r.interview_id = i.id
               WHERE i.user_id = ?
               ORDER BY r.created_at DESC""",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_user_typing_results(user_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM typing_results WHERE user_id=? ORDER BY created_at DESC", (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_user_communication_results(user_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM communication_results WHERE user_id=? ORDER BY created_at DESC", (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_candidates_summary():
    """Admin view: one row per user with aggregate stats."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT u.username,
                      COUNT(DISTINCT i.id) as total_interviews,
                      AVG(r.score) as avg_score,
                      MAX(r.created_at) as last_activity
               FROM users u
               LEFT JOIN interviews i ON i.user_id = u.id
               LEFT JOIN results r ON r.interview_id = i.id
               GROUP BY u.id
               ORDER BY last_activity DESC"""
        ).fetchall()
        return [dict(r) for r in rows]