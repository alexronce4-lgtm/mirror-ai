import sqlite3
import json
from datetime import datetime

DB_PATH = "mirror.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mirror_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            risk_level TEXT,
            risk_score INTEGER,
            confidence REAL,
            key_observations TEXT,
            immediate_actions TEXT,
            megan_message TEXT
        )
    """)
    conn.commit()
    conn.close()


def log_session(data: dict):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT INTO mirror_sessions
            (timestamp, risk_level, risk_score, confidence, key_observations, immediate_actions, megan_message)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            data.get("risk_level"),
            data.get("risk_score"),
            data.get("confidence"),
            json.dumps(data.get("key_observations", [])),
            json.dumps(data.get("immediate_actions", [])),
            data.get("megan_message"),
        ),
    )
    conn.commit()
    conn.close()


def get_history(limit: int = 10) -> list:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM mirror_sessions ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    result = []
    for row in rows:
        entry = dict(row)
        entry["key_observations"] = json.loads(entry.get("key_observations") or "[]")
        entry["immediate_actions"] = json.loads(entry.get("immediate_actions") or "[]")
        result.append(entry)
    return result
