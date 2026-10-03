"""
ui/transactions.py
-------------------
The Transactions tab: search across all customers, plus the shared
"Add Transaction" dialog used from here, the dashboard, and the ledger.
"""

import flet as ft

from models import GAVE, GOT
from services import format_currency, format_date_display
from ui import components, theme


def build_transactions_view(app):
    state = {"query": ""}
    list_container = ft.Column(spacing=10)

    def refresh_list():
        txs = app.transaction_service.all_with_customer(state["query"])
        list_container.controls.clear()
        if not txs:
            if state["query"]:
                list_container.controls.append(
                    components.empty_state(
                        ft.Icons.SEARCH_OFF_ROUNDED,
                        "No matches found",
                        "Try a different customer name or note.",
                    )
                )
            else:
                list_container.controls.append(
                    components.empty_state(
                        ft.Icons.RECEIPT_LONG_OUTLINED,
                        "No transactions yet",
                        "Record your first udhaar or payment to see it here.",
                    )
                )
        else:
            for tx in txs:
                list_container.controls.append(_transaction_row(app, tx, refresh_list))
        # Only call update when the control is attached to the page
        try:
            if getattr(list_container, "page", None):
                list_container.update()
        except RuntimeError:
            # If control isn't added to the page yet, skip update.
            pass

    def on_search_change(e):
        state["query"] = (e.control.value or "").strip()
        refresh_list()

    search_field = ft.TextField(
        hint_text="Search by customer or note",
        prefix_icon=ft.Icons.SEARCH_ROUNDED,
        border={
            ft.ControlState.DEFAULT: ft.OutlineInputBorder(
                side=ft.BorderSide(color=theme.BORDER),
                border_radius=theme.RADIUS_MD,
            ),
            ft.ControlState.FOCUSED: ft.OutlineInputBorder(
                side=ft.BorderSide(color=theme.PRIMARY),
                border_radius=theme.RADIUS_MD,
            ),
        },
        filled=True,
        fill_color=theme.SURFACE,
        content_padding=ft.padding.symmetric(horizontal=16, vertical=10),
        text_size=14,
        height=48,
        on_change=on_search_change,
    )

    header = ft.Container(
        content=ft.Row(
            [
                ft.Text("Transactions", size=20, weight=ft.FontWeight.BOLD, color=theme.TEXT_PRIMARY),
                ft.IconButton(
                    icon=ft.Icons.ADD_ROUNDED,
                    icon_color="#FFFFFF",
                    bgcolor=theme.PRIMARY,
                    tooltip="Add transaction",
                    on_click=lambda e: open_transaction_form(app, on_saved=refresh_list),
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        padding=ft.padding.only(left=20, right=20, top=24, bottom=12),
    )

    refresh_list()

    return ft.Column(
        [
            header,
            ft.Container(content=search_field, padding=ft.padding.symmetric(horizontal=20)),
            ft.Container(height=12),
            ft.Container(
                content=list_container,
                padding=ft.padding.symmetric(horizontal=20),
                expand=True,
            ),
            ft.Container(height=20),
        ],
        scroll=ft.ScrollMode.AUTO,
        spacing=0,
        expand=True,
    )


def _transaction_row(app, tx: dict, refresh_list):
    is_gave = tx["type"] == GAVE
    color = theme.RED if is_gave else theme.GREEN
    bg = theme.RED_BG if is_gave else theme.GREEN_BG
    label = "You Gave" if is_gave else "You Got"

    def open_customer(e):
        app.open_ledger(tx["customer_id"])

    def delete_click(e):
        def do_delete():
            app.transaction_service.delete(tx["id"])
            app.show_snackbar("Transaction deleted")
            refresh_list()

        app.confirm_dialog(
            "Delete Transaction", "This will permanently remove this entry.", do_delete
        )

    menu = ft.PopupMenuButton(
        icon=ft.Icons.MORE_VERT_ROUNDED,
        icon_color=theme.TEXT_SECONDARY,
        items=[
            ft.PopupMenuItem(content="Delete", icon=ft.Icons.DELETE_OUTLINE_ROUNDED, on_click=delete_click),
        ],
    )

    subtitle = format_date_display(tx["created_at"])
    if tx["note"]:
        subtitle = f"{tx['note']} \u2022 {subtitle}"

    return ft.Container(
        content=ft.Row(
            [
                ft.Container(
                    content=ft.Icon(
                        ft.Icons.ARROW_UPWARD_ROUNDED if is_gave else ft.Icons.ARROW_DOWNWARD_ROUNDED,
                        size=18,
                        color=color,
                    ),
                    bgcolor=bg,
                    width=40,
                    height=40,
                    border_radius=12,
                    alignment=ft.Alignment(0, 0),
                ),
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text(
                                    tx["customer_name"], size=13, weight=ft.FontWeight.W_600,
                                    color=theme.TEXT_PRIMARY,
                                ),
                                components.balance_badge(label, color, bg),
                            ],
                            spacing=6,
                        ),
                        ft.Text(subtitle, size=11, color=theme.TEXT_SECONDARY),
                    ],
                    spacing=2,
                    expand=True,
                ),
                ft.Text(
                    f"{'-' if is_gave else '+'}{format_currency(tx['amount'])}",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=color,
                ),
                menu,
            ],
            spacing=10,
        ),
        bgcolor=theme.SURFACE,
        padding=12,
        border_radius=theme.RADIUS_MD,
        shadow=theme.card_shadow(),
        on_click=open_customer,
        ink=True,
    )


def open_transaction_form(app, customer_id=None, customer_name=None, default_type=GAVE, on_saved=None):
    """Shared Add Transaction dialog.

    If ``customer_id`` is given (e.g. opened from a customer's ledger) the
    customer is fixed and only the type/amount/note are editable. Otherwise
    a dropdown lets the user pick who the transaction is for.
    """
    customers = app.customer_service.get_all()
    if customer_id is None and not customers:
        app.show_snackbar("Please add a customer first", success=False)
        return

    selected = {"customer_id": customer_id, "type": default_type}
    error_text = ft.Text("", color=theme.RED, size=12)

    if customer_id is None:
        selected["customer_id"] = customers[0].id
        customer_field = ft.Dropdown(
            label="Select Customer*",
            value=str(customers[0].id),
            border_radius=theme.RADIUS_SM,
            filled=True,
            fill_color=theme.BG,
            options=[ft.dropdown.Option(key=str(c.id), text=c.name) for c in customers],
        )
        # Assign change handler after creation for compatibility with installed Flet
        customer_field.on_change = lambda e: selected.update({"customer_id": int(e.control.value)})
    else:
        customer_field = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.PERSON_ROUNDED, color=theme.PRIMARY, size=18),
                    ft.Text(customer_name or "", size=14, weight=ft.FontWeight.W_600, color=theme.TEXT_PRIMARY),
                ],
                spacing=8,
            ),
            bgcolor=theme.PRIMARY_LIGHT,
            padding=12,
            border_radius=theme.RADIUS_SM,
        )

    gave_box = ft.Container(
        content=ft.Text("You Gave", size=13, weight=ft.FontWeight.W_600),
        padding=ft.padding.symmetric(vertical=10),
        border_radius=theme.RADIUS_SM,
        alignment=ft.Alignment(0, 0),
        expand=True,
        ink=True,
    )
    got_box = ft.Container(
        content=ft.Text("You Got", size=13, weight=ft.FontWeight.W_600),
        padding=ft.padding.symmetric(vertical=10),
        border_radius=theme.RADIUS_SM,
        alignment=ft.Alignment(0, 0),
        expand=True,
        ink=True,
    )

    def set_type(t):
        selected["type"] = t
        if t == GAVE:
            gave_box.bgcolor = theme.RED
            gave_box.content.color = "#FFFFFF"
            got_box.bgcolor = theme.BG
            got_box.content.color = theme.TEXT_SECONDARY
        else:
            got_box.bgcolor = theme.GREEN
            got_box.content.color = "#FFFFFF"
            gave_box.bgcolor = theme.BG
            gave_box.content.color = theme.TEXT_SECONDARY
        try:
            if getattr(gave_box, "page", None):
                gave_box.update()
        except RuntimeError:
            pass
        try:
            if getattr(got_box, "page", None):
                got_box.update()
        except RuntimeError:
            pass

    gave_box.on_click = lambda e: set_type(GAVE)
    got_box.on_click = lambda e: set_type(GOT)
    set_type(default_type)

    toggle_row = ft.Container(
        content=ft.Row([gave_box, got_box], spacing=8),
        bgcolor=theme.BG,
        padding=4,
        border_radius=theme.RADIUS_SM + 4,
    )

    amount_field = ft.TextField(
        label="Amount*",
        prefix="PKR ",
        hint_text="0",
        keyboard_type=ft.KeyboardType.NUMBER,
        border=ft.OutlineInputBorder(border_radius=theme.RADIUS_SM),
        filled=True,
        fill_color=theme.BG,
        autofocus=customer_id is not None,
    )
    note_field = ft.TextField(
        label="Note (optional)",
        border=ft.OutlineInputBorder(border_radius=theme.RADIUS_SM),
        filled=True,
        fill_color=theme.BG,
    )

    def save_click(e):
        if customer_id is None and not selected.get("customer_id"):
            error_text.value = "Please select a customer"
            app.page.update()
            return
        raw_amount = (amount_field.value or "").strip().replace(",", "")
        try:
            amount = float(raw_amount)
        except ValueError:
            error_text.value = "Enter a valid amount"
            app.page.update()
            return
        if amount <= 0:
            error_text.value = "Amount must be greater than zero"
            app.page.update()
            return

        target_customer_id = customer_id if customer_id is not None else selected["customer_id"]
        try:
            app.transaction_service.add(target_customer_id, selected["type"], amount, note_field.value or "")
        except Exception as ex:  # noqa: BLE001 - surfaced to the user
            error_text.value = f"Could not save: {ex}"
            app.page.update()
            return

        app.close_dialog()
        app.show_snackbar("Transaction added")
        if on_saved:
            on_saved()

    def cancel_click(e):
        app.close_dialog()

    dlg = ft.AlertDialog(
        modal=True,
        shape=ft.RoundedRectangleBorder(radius=theme.RADIUS_MD),
        title=ft.Text("Add Transaction", weight=ft.FontWeight.BOLD),
        content=ft.Container(
            content=ft.Column(
                [customer_field, toggle_row, amount_field, note_field, error_text],
                spacing=14,
                tight=True,
            ),
            width=340,
        ),
        actions=[
            ft.TextButton("Cancel", on_click=cancel_click),
            ft.FilledButton(
                "Save",
                on_click=save_click,
                style=ft.ButtonStyle(
                    bgcolor=theme.PRIMARY, color="#FFFFFF", shape=ft.RoundedRectangleBorder(radius=10)
                ),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    app.open_dialog(dlg)
