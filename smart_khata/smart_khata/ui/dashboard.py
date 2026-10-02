"""
ui/dashboard.py
----------------
The Dashboard tab: headline stats, quick actions, and a short recent
activity feed built from the same data the Transactions tab shows.
"""

import flet as ft

from services import format_currency, format_date_display
from ui import components, theme
from ui.customers import open_customer_form
from ui.transactions import open_transaction_form


def build_dashboard_view(app):
    stats = app.dashboard_service.get_stats()
    recent = app.transaction_service.all_with_customer()[:5]

    header = ft.Container(
        content=ft.Row(
            [
                ft.Column(
                    [
                        ft.Text("Smart Khata", size=22, weight=ft.FontWeight.BOLD, color=theme.TEXT_PRIMARY),
                        ft.Text("Your digital udhaar book", size=12, color=theme.TEXT_SECONDARY),
                    ],
                    spacing=2,
                ),
                ft.Container(
                    content=ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET_ROUNDED, color="#FFFFFF", size=22),
                    bgcolor=theme.PRIMARY,
                    width=46,
                    height=46,
                    border_radius=14,
                    alignment=ft.Alignment(0, 0),
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        padding=ft.padding.only(left=20, right=20, top=24, bottom=8),
    )

    net = stats["receivable"] - stats["payable"]
    balance_card = ft.Container(
        content=ft.Column(
            [
                ft.Text("NET BALANCE", size=11, color="#D8D5FF", weight=ft.FontWeight.W_600),
                ft.Text(format_currency(abs(net)), size=30, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                ft.Text(
                    "You will receive overall" if net >= 0 else "You owe overall",
                    size=12,
                    color="#E7E4FF",
                ),
                ft.Container(height=14),
                ft.Row(
                    [
                        _mini_balance("Receivable", stats["receivable"], ft.Icons.ARROW_DOWNWARD_ROUNDED, "#2FBE7A"),
                        ft.Container(width=1, height=36, bgcolor="#33FFFFFF"),
                        _mini_balance("Payable", stats["payable"], ft.Icons.ARROW_UPWARD_ROUNDED, "#F0685F"),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
            ],
            spacing=4,
        ),
        gradient=ft.LinearGradient(
            begin=ft.Alignment(-1, -1),
            end=ft.Alignment(1, 1),
            colors=[theme.PRIMARY, theme.PRIMARY_DARK],
        ),
        border_radius=theme.RADIUS_LG,
        padding=20,
        margin=ft.margin.symmetric(horizontal=20),
        shadow=theme.soft_shadow(theme.PRIMARY),
    )

    stats_row = ft.Row(
        [
            components.stat_card(
                "Today's Transactions", str(stats["today_transactions"]), ft.Icons.TODAY_ROUNDED,
                theme.PRIMARY, theme.PRIMARY_LIGHT, on_click=lambda e: app.show_tab(2),
            ),
            components.stat_card(
                "Customers", str(stats["customers_count"]), ft.Icons.PEOPLE_ALT_ROUNDED,
                theme.AMBER, theme.AMBER_BG, on_click=lambda e: app.show_tab(1),
            ),
        ],
        spacing=12,
    )

    quick_actions = ft.Container(
        content=ft.Column(
            [
                ft.Text("Quick Actions", size=14, weight=ft.FontWeight.BOLD, color=theme.TEXT_PRIMARY),
                ft.Container(height=8),
                ft.Row(
                    [
                        components.quick_action(
                            ft.Icons.PERSON_ADD_ALT_1_ROUNDED, "Add\nCustomer",
                            lambda e: open_customer_form(app, on_saved=app.refresh_current_tab),
                        ),
                        components.quick_action(
                            ft.Icons.SWAP_HORIZ_ROUNDED, "Add\nTransaction",
                            lambda e: open_transaction_form(app, on_saved=app.refresh_current_tab),
                        ),
                        components.quick_action(
                            ft.Icons.PEOPLE_ALT_ROUNDED, "Customers", lambda e: app.show_tab(1)
                        ),
                        components.quick_action(
                            ft.Icons.RECEIPT_LONG_ROUNDED, "Transactions", lambda e: app.show_tab(2)
                        ),
                    ],
                    spacing=6,
                ),
            ]
        ),
        padding=20,
    )

    recent_section = _build_recent_section(app, recent)

    return ft.Column(
        [
            header,
            ft.Container(height=6),
            balance_card,
            ft.Container(height=16),
            ft.Container(content=stats_row, padding=ft.padding.symmetric(horizontal=20)),
            quick_actions,
            recent_section,
            ft.Container(height=20),
        ],
        scroll=ft.ScrollMode.AUTO,
        spacing=0,
        expand=True,
    )


def _mini_balance(label, amount, icon, accent):
    return ft.Row(
        [
            ft.Container(
                content=ft.Icon(icon, size=14, color="#FFFFFF"),
                bgcolor=accent,
                width=28,
                height=28,
                border_radius=14,
                alignment=ft.Alignment(0, 0),
            ),
            ft.Column(
                [
                    ft.Text(label, size=11, color="#E7E4FF"),
                    ft.Text(format_currency(amount), size=15, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                ],
                spacing=0,
            ),
        ],
        spacing=8,
    )


def _build_recent_section(app, recent):
    if not recent:
        body = components.empty_state(
            ft.Icons.HISTORY_ROUNDED, "No activity yet", "Transactions you record will show up here."
        )
        body = ft.Container(content=body, bgcolor=theme.SURFACE, border_radius=theme.RADIUS_MD)
    else:
        rows = []
        for tx in recent:
            is_gave = tx["type"] == "gave"
            color = theme.RED if is_gave else theme.GREEN
            bg = theme.RED_BG if is_gave else theme.GREEN_BG
            rows.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Container(
                                content=ft.Icon(
                                    ft.Icons.ARROW_UPWARD_ROUNDED if is_gave else ft.Icons.ARROW_DOWNWARD_ROUNDED,
                                    size=16,
                                    color=color,
                                ),
                                bgcolor=bg,
                                width=34,
                                height=34,
                                border_radius=10,
                                alignment=ft.Alignment(0, 0),
                            ),
                            ft.Column(
                                [
                                    ft.Text(
                                        tx["customer_name"], size=13, weight=ft.FontWeight.W_600,
                                        color=theme.TEXT_PRIMARY,
                                    ),
                                    ft.Text(format_date_display(tx["created_at"]), size=11, color=theme.TEXT_SECONDARY),
                                ],
                                spacing=0,
                                expand=True,
                            ),
                            ft.Text(
                                f"{'-' if is_gave else '+'}{format_currency(tx['amount'])}",
                                size=13,
                                weight=ft.FontWeight.BOLD,
                                color=color,
                            ),
                        ],
                        spacing=10,
                    ),
                    padding=ft.padding.symmetric(vertical=10, horizontal=14),
                    on_click=lambda e, cid=tx["customer_id"]: app.open_ledger(cid),
                    ink=True,
                )
            )
        body = ft.Container(
            content=ft.Column(rows, spacing=2),
            bgcolor=theme.SURFACE,
            border_radius=theme.RADIUS_MD,
            shadow=theme.card_shadow(),
        )

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Recent Activity", size=14, weight=ft.FontWeight.BOLD, color=theme.TEXT_PRIMARY),
                        ft.TextButton("See all", on_click=lambda e: app.show_tab(2)),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                body,
            ],
            spacing=4,
        ),
        padding=ft.padding.only(left=20, right=20, top=4),
    )
