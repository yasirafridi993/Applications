"""
database.py
All SQLite access for Smart Todo lives here. The rest of the app never
touches sqlite3 directly - it goes through this module's functions.

The database file is stored next to the app so the app works completely
offline and tasks survive an app restart.
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, date
from typing import List, Optional

from backend.models import Task

# backend/ sits one level under the project root (next to main.py) - keep
# the DB file at the project root, not nested inside backend/, so it's in
# the same place it always was for anyone upgrading an existing install.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "smart_todo.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    description TEXT DEFAULT '',
    due_date    TEXT,
    due_time    TEXT,
    completed   INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_tasks_completed ON tasks(completed);
"""


@contextmanager
def get_connection():
    """Yield a sqlite3 connection with sane defaults, always closed safely."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create the database file and schema if they don't exist yet."""
    with get_connection() as conn:
        conn.executescript(SCHEMA)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Create / Update / Delete
# ---------------------------------------------------------------------------

def add_task(title: str, description: str = "", due_date: Optional[str] = None,
             due_time: Optional[str] = None) -> int:
    """Insert a new task. Returns the new task's id."""
    title = title.strip()
    if not title:
        raise ValueError("Task title cannot be empty.")
    now = _now()
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO tasks (title, description, due_date, due_time,
                                   completed, created_at, updated_at)
               VALUES (?, ?, ?, ?, 0, ?, ?)""",
            (title, description.strip(), due_date, due_time, now, now),
        )
        return cur.lastrowid


def update_task(task_id: int, title: str, description: str = "",
                 due_date: Optional[str] = None, due_time: Optional[str] = None) -> None:
    """Update an existing task's editable fields."""
    title = title.strip()
    if not title:
        raise ValueError("Task title cannot be empty.")
    with get_connection() as conn:
        conn.execute(
            """UPDATE tasks
               SET title = ?, description = ?, due_date = ?, due_time = ?, updated_at = ?
               WHERE id = ?""",
            (title, description.strip(), due_date, due_time, _now(), task_id),
        )


def delete_task(task_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))


def set_task_completed(task_id: int, completed: bool) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE tasks SET completed = ?, updated_at = ? WHERE id = ?",
            (1 if completed else 0, _now(), task_id),
        )


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------

def _rows_to_tasks(rows) -> List[Task]:
    return [Task.from_row(r) for r in rows]


def get_task_by_id(task_id: int) -> Optional[Task]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return Task.from_row(row) if row else None


def get_all_tasks(search: str = "") -> List[Task]:
    query = """SELECT * FROM tasks
               WHERE (? = '' OR title LIKE ? OR description LIKE ?)
               ORDER BY completed ASC,
                        (due_date IS NULL), due_date ASC,
                        (due_time IS NULL), due_time ASC,
                        created_at DESC"""
    like = f"%{search.strip()}%"
    with get_connection() as conn:
        rows = conn.execute(query, (search.strip(), like, like)).fetchall()
        return _rows_to_tasks(rows)


def get_pending_tasks(search: str = "") -> List[Task]:
    return [t for t in get_all_tasks(search) if not t.completed]


def get_completed_tasks(search: str = "") -> List[Task]:
    return [t for t in get_all_tasks(search) if t.completed]


def get_today_tasks(search: str = "") -> List[Task]:
    today = date.today().isoformat()
    return [t for t in get_all_tasks(search) if t.due_date == today]


def get_dashboard_stats() -> dict:
    """Counts used by the Home dashboard."""
    today = date.today().isoformat()
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM tasks WHERE completed = 0").fetchone()[0]
        completed = conn.execute("SELECT COUNT(*) FROM tasks WHERE completed = 1").fetchone()[0]
        due_today = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE due_date = ? AND completed = 0", (today,)
        ).fetchone()[0]
    return {
        "total": total,
        "pending": pending,
        "completed": completed,
        "today": due_today,
    }
