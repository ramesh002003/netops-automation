"""
SQLite Local Storage for NetOps Data
Stores: devices, issues, metrics, raw logs
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/netops.db")


def init_db():
    """Create tables if they don't exist"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            ip TEXT,
            last_seen TEXT
        );

        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device TEXT,
            type TEXT,
            severity TEXT,
            title TEXT,
            evidence TEXT,
            count INTEGER,
            detected_at TEXT
        );

        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device TEXT,
            cpu_percent REAL,
            memory_percent REAL,
            recorded_at TEXT
        );

        CREATE TABLE IF NOT EXISTS raw_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device TEXT,
            filename TEXT,
            content TEXT,
            collected_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_issues_device ON issues(device);
        CREATE INDEX IF NOT EXISTS idx_issues_type ON issues(type);
        CREATE INDEX IF NOT EXISTS idx_issues_time ON issues(detected_at);
    """)
    conn.commit()
    return conn


def save_device(name, ip):
    conn = init_db()
    conn.execute(
        "INSERT OR REPLACE INTO devices (name, ip, last_seen) VALUES (?, ?, ?)",
        (name, ip, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def save_issue(device, issue):
    conn = init_db()
    conn.execute(
        "INSERT INTO issues (device, type, severity, title, evidence, count, detected_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (device, issue["type"], issue["severity"], issue["title"],
         json.dumps(issue["evidence"]), issue["count"],
         datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def save_metrics(device, cpu, memory):
    conn = init_db()
    conn.execute(
        "INSERT INTO metrics (device, cpu_percent, memory_percent, recorded_at) VALUES (?, ?, ?, ?)",
        (device, cpu, memory, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def save_raw_log(device, filename, content):
    conn = init_db()
    conn.execute(
        "INSERT INTO raw_logs (device, filename, content, collected_at) VALUES (?, ?, ?, ?)",
        (device, filename, content, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


# ─── Query Helpers ───

def get_recent_issues(hours=24):
    """Get all issues from last N hours"""
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM issues WHERE detected_at > datetime('now', ?) ORDER BY detected_at DESC",
        (f"-{hours} hours",)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_device_history(device, limit=50):
    """Get CPU/memory history for a device"""
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM metrics WHERE device = ? ORDER BY recorded_at DESC LIMIT ?",
        (device, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_issue_summary():
    """Count issues by type and severity"""
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT type, severity, COUNT(*) as total FROM issues GROUP BY type, severity"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_devices():
    """List all known devices"""
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM devices ORDER BY last_seen DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]   
