"""
models.py
Data model for Smart Todo.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Task:
    """Represents a single todo task."""

    id: Optional[int]
    title: str
    description: str = ""
    due_date: Optional[str] = None   # ISO format: YYYY-MM-DD
    due_time: Optional[str] = None   # 24h format: HH:MM
    completed: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_row(cls, row) -> "Task":
        """Build a Task from a sqlite3.Row."""
        return cls(
            id=row["id"],
            title=row["title"],
            description=row["description"] or "",
            due_date=row["due_date"],
            due_time=row["due_time"],
            completed=bool(row["completed"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def has_due_datetime(self) -> bool:
        return bool(self.due_date)

    def due_label(self) -> str:
        """Human friendly due date/time label."""
        if not self.due_date:
            return "No due date"
        label = self.due_date
        if self.due_time:
            label += f"  {self.due_time}"
        return label
