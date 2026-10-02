"""
ui/customers.py
----------------
The Customers tab: search, list, add/edit/delete.
"""

import flet as ft

from services import format_currency
from ui import components, theme


def build_customers_view(app):
    state = {"query": ""}
    list_container = ft.Column(spacing=10)

    def refresh_list():
        found = app.customer_service.get_all(state["query"])
        list_container.controls.clear()
        if not found:
            if state["query"]:
                list_container.controls.append(
                    components.empty_state(
                        ft.Icons.SEARCH_OFF_ROUNDED,
                        "No matches found",
                        "Try a different name or phone number.",
                    )
                )
            else:
                list_container.controls.append(
                    components.empty_state(
                        ft.Icons.PEOPLE_OUTLINE_ROUNDED,
                        "No customers yet",
                        "Add your first customer to start tracking udhaar.",
                    )
                )
        else:
            for customer in found:
                list_container.controls.append(_customer_card(app, customer, refresh_list))
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
        hint_text="Search customers by name or phone",
        prefix_icon=ft.Icons.SEARCH_ROUNDED,
        border_radius=theme.RADIUS_MD,
        filled=True,
        fill_color=theme.SURFACE,
        border_color=theme.BORDER,
        focused_border_color=theme.PRIMARY,
        content_padding=ft.padding.symmetric(horizontal=16, vertical=10),
        text_size=14,
        height=48,
        on_change=on_search_change,
    )

    header = ft.Container(
        content=ft.Row(
            [
                ft.Text("Customers", size=20, weight=ft.FontWeight.BOLD, color=theme.TEXT_PRIMARY),
                ft.IconButton(
                    icon=ft.Icons.PERSON_ADD_ALT_1_ROUNDED,
                    icon_color="#FFFFFF",
                    bgcolor=theme.PRIMARY,
                    tooltip="Add customer",
                    on_click=lambda e: open_customer_form(app, on_saved=refresh_list),
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


def _customer_card(app, customer, refresh_list):
    bal = customer.balance
    if bal > 0.004:
        bal_color, bal_bg, bal_label = theme.GREEN, theme.GREEN_BG, "You'll Get"
    elif bal < -0.004:
        bal_color, bal_bg, bal_label = theme.RED, theme.RED_BG, "You'll Give"
    else:
        bal_color, bal_bg, bal_label = theme.TEXT_SECONDARY, theme.BORDER, "Settled"

    initial = (customer.name[:1] if customer.name else "?").upper()

    def go_ledger(e):
        app.open_ledger(customer.id)

    def edit_click(e):
        open_customer_form(app, customer=customer, on_saved=refresh_list)

    def delete_click(e):
        def do_delete():
            app.customer_service.delete(customer.id)
            app.show_snackbar(f"{customer.name} deleted")
            refresh_list()

        app.confirm_dialog(
            "Delete Customer",
            f"Delete {customer.name} and all their transaction history? "
            "This cannot be undone.",
            do_delete,
        )

    menu = ft.PopupMenuButton(
        icon=ft.Icons.MORE_VERT_ROUNDED,
        icon_color=theme.TEXT_SECONDARY,
        items=[
            ft.PopupMenuItem(content="Edit", icon=ft.Icons.EDIT_OUTLINED, on_click=edit_click),
            ft.PopupMenuItem(content="Delete", icon=ft.Icons.DELETE_OUTLINE_ROUNDED, on_click=delete_click),
        ],
    )

    return ft.Container(
        content=ft.Row(
            [
                ft.Container(
                    content=ft.Text(initial, size=16, weight=ft.FontWeight.BOLD, color=theme.PRIMARY),
                    bgcolor=theme.PRIMARY_LIGHT,
                    width=46,
                    height=46,
                    border_radius=23,
                    alignment=ft.Alignment(0, 0),
                ),
                ft.Column(
                    [
                        ft.Text(customer.name, size=14, weight=ft.FontWeight.W_600, color=theme.TEXT_PRIMARY),
                        ft.Text(customer.phone or "No phone number", size=12, color=theme.TEXT_SECONDARY),
                    ],
                    spacing=2,
                    expand=True,
                ),
                ft.Column(
                    [
                        ft.Text(format_currency(abs(bal)), size=14, weight=ft.FontWeight.BOLD, color=bal_color),
                        components.balance_badge(bal_label, bal_color, bal_bg),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.END,
                    spacing=4,
                ),
                menu,
            ],
            spacing=10,
        ),
        bgcolor=theme.SURFACE,
        padding=14,
        border_radius=theme.RADIUS_MD,
        shadow=theme.card_shadow(),
        on_click=go_ledger,
        ink=True,
    )


def open_customer_form(app, customer=None, on_saved=None):
    """Shared Add/Edit customer dialog."""
    is_edit = customer is not None

    name_field = ft.TextField(
        label="Customer Name*",
        value=customer.name if is_edit else "",
        border_radius=theme.RADIUS_SM,
        filled=True,
        fill_color=theme.BG,
        autofocus=not is_edit,
    )
    phone_field = ft.TextField(
        label="Phone Number",
        value=customer.phone if is_edit else "",
        border_radius=theme.RADIUS_SM,
        filled=True,
        fill_color=theme.BG,
        keyboard_type=ft.KeyboardType.PHONE,
        hint_text="e.g. 923001234567",
    )
    note_field = ft.TextField(
        label="Address / Note (optional)",
        value=customer.note if is_edit else "",
        border_radius=theme.RADIUS_SM,
        filled=True,
        fill_color=theme.BG,
        multiline=True,
        min_lines=1,
        max_lines=3,
    )
    error_text = ft.Text("", color=theme.RED, size=12)

    def save_click(e):
        name = (name_field.value or "").strip()
        if not name:
            error_text.value = "Please enter a customer name"
            app.page.update()
            return
        try:
            if is_edit:
                app.customer_service.update(
                    customer.id, name, phone_field.value or "", note_field.value or ""
                )
                message = "Customer updated"
            else:
                app.customer_service.add(name, phone_field.value or "", note_field.value or "")
                message = "Customer added"
        except Exception as ex:  # noqa: BLE001 - surfaced to the user, not swallowed
            error_text.value = f"Could not save: {ex}"
            app.page.update()
            return

        app.close_dialog()
        app.show_snackbar(message)
        if on_saved:
            on_saved()

    def cancel_click(e):
        app.close_dialog()

    dlg = ft.AlertDialog(
        modal=True,
        shape=ft.RoundedRectangleBorder(radius=theme.RADIUS_MD),
        title=ft.Text("Edit Customer" if is_edit else "Add Customer", weight=ft.FontWeight.BOLD),
        content=ft.Container(
            content=ft.Column([name_field, phone_field, note_field, error_text], spacing=12, tight=True),
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
