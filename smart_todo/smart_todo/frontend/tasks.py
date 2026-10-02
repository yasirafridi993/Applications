"""
ui/tasks.py
The "Tasks" screen: All / Today / Pending / Completed tabs, search,
task cards, and complete/edit/delete actions with a delete confirmation.
"""

from typing import Callable, List

import flet as ft

from backend import database
from backend.models import Task
from frontend.task_form import open_task_dialog

FILTERS = ["All", "Today", "Pending", "Completed"]


class TasksView:
    """Builds and owns the Tasks screen. Call refresh() after any data change."""

    def __init__(self, page: ft.Page, on_data_changed: Callable[[], None]):
        self.page = page
        self.on_data_changed = on_data_changed  # lets Home refresh its stats too
        self.active_filter = "All"
        self.search_text = ""

        self.search_field = ft.TextField(
            hint_text="Search tasks...",
            prefix_icon=ft.Icons.SEARCH,
            border_radius=14,
            dense=True,
            on_change=self._on_search_change,
        )

        self.filter_buttons = []
        self.filter_row = self._build_filter_row()

        self.list_view = ft.ListView(expand=True, spacing=10, padding=ft.Padding.only(top=6))
        self.empty_state = self._build_empty_state()

        self.body = ft.Column(
            [self.list_view, self.empty_state],
            expand=True,
        )

        self.view = ft.Column(
            [
                ft.Text("My Tasks", size=22, weight=ft.FontWeight.BOLD),
                self.search_field,
                self.filter_row,
                self.body,
            ],
            spacing=12,
            expand=True,
        )

    # -- building blocks ---------------------------------------------------

    def _build_filter_row(self) -> ft.Row:
        buttons = []
        for idx, label in enumerate(FILTERS):
            button = ft.TextButton(
                label,
                on_click=lambda e, name=label: self._on_filter_change(name),
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=12),
                    bgcolor=ft.Colors.PRIMARY_CONTAINER if idx == 0 else None,
                    color=ft.Colors.PRIMARY if idx == 0 else ft.Colors.ON_SURFACE_VARIANT,
                ),
            )
            self.filter_buttons.append(button)
            buttons.append(button)
        return ft.Row(buttons, spacing=8, wrap=True)

    def _on_filter_change(self, label: str) -> None:
        self.active_filter = label
        for button, button_label in zip(self.filter_buttons, FILTERS):
            is_active = button_label == label
            button.style = ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=12),
                bgcolor=ft.Colors.PRIMARY_CONTAINER if is_active else None,
                color=ft.Colors.PRIMARY if is_active else ft.Colors.ON_SURFACE_VARIANT,
            )
        self.refresh()

    def _build_empty_state(self) -> ft.Container:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.TASK_ALT, size=64, color=ft.Colors.OUTLINE),
                    ft.Text("No tasks here", size=16, weight=ft.FontWeight.W_600),
                    ft.Text(
                        "Tap the + button to add your first task.",
                        size=13,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=6,
            ),
            alignment=ft.Alignment(0.5, 0.5),
            padding=ft.Padding.only(top=60),
            visible=False,
        )

    def _task_card(self, task: Task) -> ft.Container:
        title_style = ft.TextStyle(
            size=15,
            weight=ft.FontWeight.W_600,
            decoration=ft.TextDecoration.LINE_THROUGH if task.completed else None,
            color=ft.Colors.ON_SURFACE_VARIANT if task.completed else ft.Colors.ON_SURFACE,
        )

        due_chip = None
        if task.due_date:
            due_chip = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.SCHEDULE, size=13, color=ft.Colors.PRIMARY),
                        ft.Text(task.due_label(), size=11, color=ft.Colors.PRIMARY),
                    ],
                    spacing=4,
                    tight=True,
                ),
                bgcolor=ft.Colors.PRIMARY_CONTAINER,
                border_radius=20,
                padding=ft.Padding.symmetric(horizontal=8, vertical=3),
            )

        info_column = ft.Column(
            [
                ft.Text(task.title, style=title_style),
                *([ft.Text(task.description, size=12,
                            color=ft.Colors.ON_SURFACE_VARIANT, max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS)]
                  if task.description else []),
                *([due_chip] if due_chip else []),
            ],
            spacing=4,
            expand=True,
        )

        return ft.Container(
            content=ft.Row(
                [
                    ft.Checkbox(
                        value=task.completed,
                        on_change=lambda e, t=task: self._toggle_complete(t),
                    ),
                    info_column,
                    ft.IconButton(
                        icon=ft.Icons.EDIT_OUTLINED,
                        icon_size=19,
                        tooltip="Edit",
                        on_click=lambda e, t=task: open_task_dialog(
                            self.page, self._refresh_and_notify, task=t
                        ),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_size=19,
                        icon_color=ft.Colors.ERROR,
                        tooltip="Delete",
                        on_click=lambda e, t=task: self._confirm_delete(t),
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=ft.Colors.SURFACE,
            border_radius=16,
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            shadow=ft.BoxShadow(
                blur_radius=8,
                color=ft.Colors.with_opacity(0.08, ft.Colors.SHADOW),
                offset=ft.Offset(0, 2),
            ),
        )

    # -- data / events -------------------------------------------------------

    def _fetch_tasks(self) -> List[Task]:
        if self.active_filter == "Today":
            return database.get_today_tasks(self.search_text)
        if self.active_filter == "Pending":
            return database.get_pending_tasks(self.search_text)
        if self.active_filter == "Completed":
            return database.get_completed_tasks(self.search_text)
        return database.get_all_tasks(self.search_text)

    def refresh(self) -> None:
        """Re-query and redraw this screen only. Does NOT notify Home -
        see _refresh_and_notify() for the version used after an actual
        data change (that distinction is what keeps refresh_all() from
        recursing back into this method forever)."""
        tasks = self._fetch_tasks()
        self.list_view.controls = [self._task_card(t) for t in tasks]
        self.empty_state.visible = len(tasks) == 0
        try:
            if self.view.page:
                self.body.update()
        except RuntimeError:
            pass

    def _refresh_and_notify(self) -> None:
        """Use this after an action that actually changed task data
        (add/edit/complete/delete) so Home's stats stay in sync too."""
        self.refresh()
        self.on_data_changed()

    def _on_search_change(self, e: ft.ControlEvent):
        self.search_text = self.search_field.value or ""
        self.refresh()

    def _toggle_complete(self, task: Task):
        database.set_task_completed(task.id, not task.completed)
        self._refresh_and_notify()

    def _confirm_delete(self, task: Task):
        def do_delete(e):
            database.delete_task(task.id)
            close(e)
            self._refresh_and_notify()

        def close(e):
            self.page.pop_dialog()
            self.page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Delete task?"),
            content=ft.Text(f'"{task.title}" will be permanently deleted.'),
            actions=[
                ft.TextButton("Cancel", on_click=close),
                ft.FilledButton(
                    "Delete",
                    icon=ft.Icons.DELETE_OUTLINE,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.ERROR, color=ft.Colors.ON_ERROR),
                    on_click=do_delete,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=16),
        )
        self.page.show_dialog(dialog)
