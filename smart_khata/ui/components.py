"""
ui/components.py
-----------------
Small, reusable pieces of UI shared by dashboard/customers/ledger/transactions
so the app has one consistent look instead of every screen rolling its own
cards and buttons.
"""

import flet as ft

from ui import theme


def stat_card(title: str, value: str, icon, icon_color: str, icon_bg: str, on_click=None):
    """A compact card used for small dashboard metrics."""
    return ft.Container(
        content=ft.Row(
            [
                ft.Container(
                    content=ft.Icon(icon, color=icon_color, size=20),
                    bgcolor=icon_bg,
                    width=42,
                    height=42,
                    border_radius=12,
                    alignment=ft.Alignment(0, 0),
                ),
                ft.Column(
                    [
                        ft.Text(value, size=17, color=theme.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
                        ft.Text(title, size=11, color=theme.TEXT_SECONDARY, weight=ft.FontWeight.W_500),
                    ],
                    spacing=1,
                ),
            ],
            spacing=10,
        ),
        bgcolor=theme.SURFACE,
        padding=14,
        border_radius=theme.RADIUS_MD,
        shadow=theme.card_shadow(),
        on_click=on_click,
        ink=on_click is not None,
        expand=True,
    )


def quick_action(icon, label: str, on_click):
    """One button in the dashboard's quick-action row."""
    return ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Icon(icon, color=theme.PRIMARY, size=22),
                    bgcolor=theme.PRIMARY_LIGHT,
                    width=50,
                    height=50,
                    border_radius=16,
                    alignment=ft.Alignment(0, 0),
                ),
                ft.Text(
                    label,
                    size=11,
                    weight=ft.FontWeight.W_600,
                    color=theme.TEXT_PRIMARY,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        ),
        on_click=on_click,
        padding=ft.padding.symmetric(vertical=10, horizontal=4),
        border_radius=theme.RADIUS_MD,
        ink=True,
        expand=True,
    )


def empty_state(icon, title: str, subtitle: str):
    """Shown instead of a list when there is nothing to display yet."""
    return ft.Container(
        content=ft.Column(
            [
                ft.Icon(icon, size=52, color=theme.TEXT_SECONDARY),
                ft.Container(height=4),
                ft.Text(title, size=15, weight=ft.FontWeight.BOLD, color=theme.TEXT_PRIMARY),
                ft.Text(
                    subtitle,
                    size=12,
                    color=theme.TEXT_SECONDARY,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=4,
        ),
        alignment=ft.Alignment(0, 0),
        padding=ft.padding.symmetric(vertical=48, horizontal=24),
    )


def balance_badge(label: str, color: str, bg: str):
    return ft.Container(
        content=ft.Text(label, size=10, weight=ft.FontWeight.W_600, color=color),
        bgcolor=bg,
        padding=ft.padding.symmetric(horizontal=8, vertical=2),
        border_radius=6,
    )
