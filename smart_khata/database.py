"""
database.py
------------
Low-level SQLite access for Smart Khata.

Responsible ONLY for:
- knowing where the database file lives
- opening connections with sane defaults (row factory, foreign keys)
- creating the schema on first launch

No business logic lives here - see services.py for that.
"""

import os
import shutil
import sqlite3
import sys
from pathlib import Path


def get_db_path() -> str:
    """Return a stable, user-writable location for the SQLite database.

    PyInstaller/EXE builds often run from a temporary extraction folder, so
    keeping the database next to the executable causes data loss on restart.
    We store it under the user's app-data folder instead.
    """
    if os.name == "nt":
        base_dir = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
        app_dir = base_dir / "SmartKhata"
    elif sys.platform == "darwin":
        app_dir = Path.home() / "Library" / "Application Support" / "SmartKhata"
    else:
        app_dir = Path.home() / ".local" / "share" / "SmartKhata"

    app_dir.mkdir(parents=True, exist_ok=True)
    return str(app_dir / "smart_khata.db")


def migrate_legacy_db(legacy_path: str, current_path: str) -> bool:
    """Move an older database from the project folder into the new app-data folder."""
    legacy = Path(legacy_path)
    current = Path(current_path)

    if not legacy.exists() or current.exists():
        return False

    current.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(legacy, current)
        legacy.unlink()
    except OSError:
        return False
    return True


# Store the database in a user-writable app directory so it survives EXE re-launches.
LEGACY_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "smart_khata.db")
DB_PATH = get_db_path()

# Preserve data from older builds that kept the database next to the source file.
migrate_legacy_db(LEGACY_DB_PATH, DB_PATH)


def get_connection() -> sqlite3.Connection:
    """Return a new SQLite connection configured for this app.

    A fresh connection is opened per call (SQLite connections are cheap
    and this keeps the code simple and thread-safe for a small local app).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Needed for ON DELETE CASCADE to actually cascade.
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create the database file and tables if they do not exist yet.

    Safe to call every time the app starts.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                note TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('gave', 'got')),
                amount REAL NOT NULL CHECK (amount > 0),
                note TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (customer_id) REFERENCES customers (id)
                    ON DELETE CASCADE
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_transactions_customer "
            "ON transactions (customer_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_transactions_created "
            "ON transactions (created_at)"
        )
        conn.commit()
    except sqlite3.Error as ex:
        # Surface a clear error rather than a silent, half-created database.
        raise RuntimeError(f"Could not initialize Smart Khata database: {ex}") from ex
    finally:
        conn.close()
