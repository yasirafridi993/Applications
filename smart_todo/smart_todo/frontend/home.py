"""
ui/home.py
The "Home" dashboard: stat cards, a prominent Add Task button, a short
"Today" preview, and the (optional) update-available banner.
"""

from typing import Callable, Optional

import flet as ft

from backend import database
from frontend.task_form import open_task_dialog
from monetization.admob.admob_service import AdmobService

STAT_DEFS = [
    ("total", "Total Tasks", ft.Icons.LIST_ALT, ft.Colors.PRIMARY),
    ("pending", "Pending", ft.Icons.PENDING_ACTIONS, ft.Colors.TERTIARY),
    ("completed", "Completed", ft.Icons.CHECK_CIRCLE, ft.Colors.GREEN),
    ("today", "Due Today", ft.Icons.TODAY, ft.Colors.ERROR),
]


class HomeView:
    """Builds and owns the Home screen. Call refresh() after any data change."""

    def __init__(
        self,
        page: ft.Page,
        on_data_changed: Callable[[], None],
        go_to_tasks: Callable[[], None],
        admob_service: Optional[AdmobService] = None,
    ):
        self.page = page
        self.on_data_changed = on_data_changed
        self.go_to_tasks = go_to_tasks
        self.admob_service = admob_service

        self.stat_value_texts = {}
        self.stats_row = self._build_stats_row()

        self.today_list = ft.Column(spacing=8)
        self.today_empty = ft.Text(
            "Nothing due today. Enjoy the breathing room.",
            size=13,
            color=ft.Colors.ON_SURFACE_VARIANT,
        )

        self.update_banner = self._build_update_banner()
        # Holds the AdMob banner control for free users; stays empty where
        # ads aren't supported or available.
        self.ad_slot = ft.Container(alignment=ft.Alignment(0.5, 0.5))

        self.view = ft.Column(
            [
                self.update_banner,
                ft.Text("Smart Todo", size=26, weight=ft.FontWeight.BOLD),
                ft.Text("Here's your day at a glance.", size=13,
                        color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Container(height=8),
                self.stats_row,
                ft.Container(height=8),
                ft.FilledButton(
                    "Add Task",
                    icon=ft.Icons.ADD,
                    style=ft.ButtonStyle(
                        padding=ft.Padding.symmetric(vertical=18, horizontal=20),
                        shape=ft.RoundedRectangleBorder(radius=14),
                    ),
                    on_click=lambda e: open_task_dialog(self.page, self._after_change),
                    width=1000,
                ),
                ft.Container(height=12),
                ft.Row(
                    [
                        ft.Text("Due Today", size=16, weight=ft.FontWeight.W_600),
                        ft.TextButton("See all tasks", on_click=lambda e: self.go_to_tasks()),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                self.today_empty,
                self.today_list,
                self.ad_slot,
            ],
            spacing=6,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    # -- building blocks -----------------------------------------------------

    def _build_stats_row(self) -> ft.ResponsiveRow:
        cards = []
        for key, label, icon, color in STAT_DEFS:
            value_text = ft.Text("0", size=22, weight=ft.FontWeight.BOLD, color=color)
            self.stat_value_texts[key] = value_text
            cards.append(
                ft.Container(
                    col=6,
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Icon(icon, color=color, size=20),
                                value_text,
                                ft.Text(label, size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                            ],
                            spacing=2,
                        ),
                        bgcolor=ft.Colors.SURFACE,
                        border_radius=16,
                        padding=14,
                        shadow=ft.BoxShadow(
                            blur_radius=8,
                            color=ft.Colors.with_opacity(0.08, ft.Colors.SHADOW),
                            offset=ft.Offset(0, 2),
                        ),
                    ),
                )
            )
        return ft.ResponsiveRow(cards, spacing=10, run_spacing=10)

    def _build_update_banner(self) -> ft.Container:
        self.update_message = ft.Text("", size=12, color=ft.Colors.ON_TERTIARY_CONTAINER)
        self._update_now_btn = ft.TextButton("Update Now")
        self._update_later_btn = ft.TextButton(
            "Later", on_click=lambda e: self._dismiss_banner()
        )
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.SYSTEM_UPDATE, color=ft.Colors.ON_TERTIARY_CONTAINER),
                            ft.Text("New Update Available", weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.ON_TERTIARY_CONTAINER),
                        ],
                        spacing=8,
                    ),
                    self.update_message,
                    ft.Row(
                        [self._update_later_btn, self._update_now_btn],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                spacing=4,
            ),
            bgcolor=ft.Colors.TERTIARY_CONTAINER,
            border_radius=16,
            padding=14,
            visible=False,
        )

    def _snack(self, message: str) -> None:
        try:
            if self.view.page:
                bar = ft.SnackBar(ft.Text(message), open=True)
                self.page.add(bar)
                self.page.update()
        except RuntimeError:
            pass

    # -- public API -----------------------------------------------------------

    def show_update_available(self, latest_version: str, play_store_url: str) -> None:
        """Called from main.py once the background update check finds a newer version."""
        self.update_message.value = f"Version {latest_version} is available. Yours is up to date otherwise."
        self._update_now_btn.on_click = lambda e: self.page.launch_url(play_store_url)
        self.update_banner.visible = True
        try:
            if self.view.page:
                self.view.update()
        except RuntimeError:
            pass

    def _dismiss_banner(self):
        self.update_banner.visible = False
        try:
            if self.view.page:
                self.view.update()
        except RuntimeError:
            pass

    def _after_change(self):
        self.refresh()
        self.on_data_changed()

    def _refresh_monetization(self) -> None:
        if self.admob_service:
            self.ad_slot.content = self.admob_service.banner_control(False)
        else:
            self.ad_slot.content = None

    def refresh(self) -> None:
        self._refresh_monetization()
        stats = database.get_dashboard_stats()
        for key, value_text in self.stat_value_texts.items():
            value_text.value = str(stats.get(key, 0))

        today_tasks = database.get_today_tasks()
        self.today_list.controls = [
            ft.Row(
                [
                    ft.Icon(
                        ft.Icons.CHECK_CIRCLE if t.completed else ft.Icons.RADIO_BUTTON_UNCHECKED,
                        size=18,
                        color=ft.Colors.GREEN if t.completed else ft.Colors.OUTLINE,
                    ),
                    ft.Text(
                        t.title,
                        size=13,
                        style=ft.TextStyle(
                            decoration=ft.TextDecoration.LINE_THROUGH if t.completed else None
                        ),
                    ),
                ],
                spacing=8,
            )
            for t in today_tasks[:5]
        ]
        self.today_empty.visible = len(today_tasks) == 0

        try:
            if self.view.page:
                self.view.update()
        except RuntimeError:
            pass
