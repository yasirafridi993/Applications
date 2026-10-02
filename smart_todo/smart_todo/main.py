"""
main.py
Smart Todo - entry point.

Run with:  python main.py

Wires together the SQLite database, the Home dashboard, the Tasks screen,
bottom navigation, a light/dark theme toggle, the global "Add Task" FAB,
and a background, non-blocking app-update check.
"""

import threading

import flet as ft

from backend import database
from backend import update_checker
from frontend.home import HomeView
from frontend.tasks import TasksView
from frontend.task_form import open_task_dialog
from monetization.admob.admob_service import AdmobService



def main(page: ft.Page) -> None:
    page.title = "Smart Todo"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.INDIGO, use_material3=True)
    page.dark_theme = ft.Theme(color_scheme_seed=ft.Colors.INDIGO, use_material3=True)
    page.padding = 0
    page.bgcolor = ft.Colors.SURFACE

    # Best-effort mobile-sized preview window on desktop; harmless if unsupported.
    try:
        page.window.width = 420
        page.window.height = 860
        page.window.resizable = True
    except Exception:
        pass

    # ---- data layer ---------------------------------------------------
    database.init_db()

    # ---- monetization (fully separate from Todo UI/database logic) -------
    # Both services degrade to safe no-ops if their native side isn't
    # available (desktop preview, flet-ads missing, the Play Billing
    # extension not yet built) - Smart Todo's own features never depend
    # on either succeeding.
    admob_service = AdmobService(page)

    # ---- screens --------------------------------------------------------
    content_area = ft.Container(expand=True, padding=16)

    def refresh_all() -> None:
        home_view.refresh()
        tasks_view.refresh()

    def show_tab(index: int) -> None:
        nav_bar.selected_index = index
        content_area.content = home_view.view if index == 0 else tasks_view.view
        page.update()

    home_view = HomeView(
        page,
        on_data_changed=refresh_all,
        go_to_tasks=lambda: show_tab(1),
        admob_service=admob_service,
    )
    tasks_view = TasksView(page, on_data_changed=refresh_all)

    # ---- theme toggle -----------------------------------------------------
    def toggle_theme(e: ft.ControlEvent) -> None:
        page.theme_mode = (
            ft.ThemeMode.DARK if page.theme_mode == ft.ThemeMode.LIGHT else ft.ThemeMode.LIGHT
        )
        theme_icon_button.icon = (
            ft.Icons.DARK_MODE_OUTLINED
            if page.theme_mode == ft.ThemeMode.LIGHT
            else ft.Icons.LIGHT_MODE_OUTLINED
        )
        page.update()

    theme_icon_button = ft.IconButton(
        icon=ft.Icons.DARK_MODE_OUTLINED,
        tooltip="Toggle theme",
        on_click=toggle_theme,
    )

    page.appbar = ft.AppBar(
        title=ft.Text("Smart Todo", weight=ft.FontWeight.BOLD),
        center_title=False,
        bgcolor=ft.Colors.SURFACE,
        actions=[theme_icon_button, ft.Container(width=6)],
    )

    # ---- bottom navigation --------------------------------------------
    nav_bar = ft.NavigationBar(
        selected_index=0,
        on_change=lambda e: show_tab(e.control.selected_index),
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.HOME_OUTLINED,
                                         selected_icon=ft.Icons.HOME, label="Home"),
            ft.NavigationBarDestination(icon=ft.Icons.CHECKLIST_OUTLINED,
                                         selected_icon=ft.Icons.CHECKLIST, label="Tasks"),
        ],
    )
    page.navigation_bar = nav_bar

    # ---- global Add Task FAB -------------------------------------------
    page.floating_action_button = ft.FloatingActionButton(
        icon=ft.Icons.ADD,
        tooltip="Add Task",
        on_click=lambda e: open_task_dialog(page, refresh_all),
    )

    page.add(content_area)
    show_tab(0)
    refresh_all()

    # ---- background, non-blocking update check --------------------------
    def run_update_check() -> None:
        result = update_checker.check_for_update()
        if result.update_available:
            home_view.show_update_available(result.latest_version, result.play_store_url)
        # Any error/no-update case is silently ignored - the app keeps
        # working normally offline, exactly as required.

    threading.Thread(target=run_update_check, daemon=True).start()


if __name__ == "__main__":
    ft.run(main)
