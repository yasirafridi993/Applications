"""
ui/task_form.py
Add / Edit Task dialog: a single reusable AlertDialog used both for
creating a brand-new task and editing an existing one.
"""

from datetime import datetime
from typing import Callable, Optional

import flet as ft

from backend import database
from backend.models import Task


def open_task_dialog(
    page: ft.Page,
    on_saved: Callable[[], None],
    task: Optional[Task] = None,
) -> None:
    """
    Open the Add/Edit Task dialog.
    - task=None  -> "Add Task" mode.
    - task=Task  -> "Edit Task" mode, fields pre-filled.
    on_saved() is called after a successful save so the caller can refresh.
    """
    is_edit = task is not None

    title_field = ft.TextField(
        label="Title",
        value=task.title if is_edit else "",
        autofocus=not is_edit,
        border_radius=12,
        max_length=100,
    )
    description_field = ft.TextField(
        label="Description (optional)",
        value=task.description if is_edit else "",
        multiline=True,
        min_lines=2,
        max_lines=4,
        border_radius=12,
    )

    # Local mutable state for the picked due date/time.
    state = {
        "due_date": task.due_date if is_edit else None,
        "due_time": task.due_time if is_edit else None,
    }

    due_date_text = ft.Text(
        state["due_date"] or "No due date",
        size=13,
        color=ft.Colors.ON_SURFACE_VARIANT,
    )
    due_time_text = ft.Text(
        state["due_time"] or "No due time",
        size=13,
        color=ft.Colors.ON_SURFACE_VARIANT,
    )
    error_text = ft.Text("", color=ft.Colors.ERROR, size=12)

    def on_date_change(e: ft.ControlEvent):
        if date_picker.value:
            state["due_date"] = date_picker.value.date().isoformat()
            due_date_text.value = state["due_date"]
            due_date_text.update()

    def on_time_change(e: ft.ControlEvent):
        if time_picker.value:
            state["due_time"] = time_picker.value.strftime("%H:%M")
            due_time_text.value = state["due_time"]
            due_time_text.update()

    date_picker = ft.DatePicker(
        first_date=datetime(2020, 1, 1),
        last_date=datetime(2100, 12, 31),
        on_change=on_date_change,
    )
    time_picker = ft.TimePicker(on_change=on_time_change)
    page.overlay.extend([date_picker, time_picker])

    def clear_due_date(e):
        state["due_date"] = None
        state["due_time"] = None
        due_date_text.value = "No due date"
        due_time_text.value = "No due time"
        due_date_text.update()
        due_time_text.update()

    def close_dialog(e=None):
        page.pop_dialog()
        page.update()

    def save_task(e):
        title = title_field.value.strip() if title_field.value else ""
        if not title:
            error_text.value = "Title is required."
            error_text.update()
            return

        try:
            if is_edit:
                database.update_task(
                    task.id,
                    title=title,
                    description=description_field.value or "",
                    due_date=state["due_date"],
                    due_time=state["due_time"],
                )
            else:
                database.add_task(
                    title=title,
                    description=description_field.value or "",
                    due_date=state["due_date"],
                    due_time=state["due_time"],
                )
        except Exception as ex:  # noqa: BLE001
            error_text.value = f"Could not save task: {ex}"
            error_text.update()
            return

        close_dialog()
        on_saved()

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Edit Task" if is_edit else "Add Task", weight=ft.FontWeight.BOLD),
        content=ft.Container(
            width=360,
            content=ft.Column(
                [
                    title_field,
                    description_field,
                    ft.Row(
                        [
                            ft.OutlinedButton(
                                "Due date",
                                icon=ft.Icons.CALENDAR_MONTH,
                                on_click=lambda e: (setattr(date_picker, 'open', True), page.update()),
                            ),
                            due_date_text,
                        ],
                        alignment=ft.MainAxisAlignment.START,
                        spacing=10,
                    ),
                    ft.Row(
                        [
                            ft.OutlinedButton(
                                "Due time",
                                icon=ft.Icons.ACCESS_TIME,
                                on_click=lambda e: (setattr(time_picker, 'open', True), page.update()),
                            ),
                            due_time_text,
                        ],
                        alignment=ft.MainAxisAlignment.START,
                        spacing=10,
                    ),
                    ft.TextButton(
                        "Clear due date/time",
                        icon=ft.Icons.CLOSE,
                        on_click=clear_due_date,
                        visible=True,
                    ),
                    error_text,
                ],
                tight=True,
                spacing=10,
            ),
        ),
        actions=[
            ft.TextButton("Cancel", on_click=close_dialog),
            ft.FilledButton("Save", icon=ft.Icons.CHECK, on_click=save_task),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        shape=ft.RoundedRectangleBorder(radius=16),
    )

    page.show_dialog(dialog)
