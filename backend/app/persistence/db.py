"""SQLite connection + schema initialisation."""
from __future__ import annotations
import os
import sqlite3
from app.core.config import DATABASE_PATH

_MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "migrations")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Run all migration SQL files against the database."""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    migration_file = os.path.join(_MIGRATIONS_DIR, "001_init.sql")
    with open(migration_file, "r", encoding="utf-8") as f:
        sql = f.read()
    conn = get_connection()
    conn.executescript(sql)
    conn.commit()
    conn.close()
    _seed_default_user()


def _seed_default_user() -> None:
    """Insert a default admin user using direct bcrypt."""
    import bcrypt
    import uuid
    from datetime import datetime, timezone

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM users")
        count = cur.fetchone()[0]
        if count == 0:
            # Hash 'admin' directly with bcrypt
            pwd_bytes = "admin".encode("utf-8")
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")

            cur.execute(
                """
                INSERT INTO users (id, username, password_hash, role, display_name, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    "admin",
                    hashed,
                    "admin",
                    "Administrator",
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
    except Exception:
        pass  # Table might not exist yet if migration failed
    finally:
        conn.close()
