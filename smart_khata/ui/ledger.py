"""
ui/ledger.py
------------
The customer ledger: balance summary, You Gave / You Got actions,
full transaction history grouped by date, and WhatsApp sharing.

This is pushed as its own ft.View (drill-down navigation) rather than
living in the bottom-tab AnimatedSwitcher, so it gets its own back button
and hides the bottom navigation bar like a native detail screen would.
"""

from datetime import date, datetime
import webbrowser

import flet as ft

from models import GAVE
from services import format_currency, format_date_display
from ui import components, theme
from ui.customers import open_customer_form
from ui.transactions import open_transaction_form


def build_ledger_view(app, customer_id: int):
    customer = app.customer_service.get(customer_id)
    if customer is None:
        return ft.View(
            route=f"/ledger/{customer_id}",
            bgcolor=theme.BG,
            controls=[
                ft.Container(
                    content=components.empty_state(
                        ft.Icons.PERSON_OFF_ROUNDED, "Customer not found",
                        "This customer may have been deleted.",
                    ),
                    expand=True,
                    alignment=ft.Alignment(0, 0),
                )
            ],
        )

    list_container = ft.Column(spacing=10)
    balance_section = ft.Container(content=_balance_summary(customer))

    def clear_all_click(e):
        def clear_records():
            try:
                count = app.transaction_service.clear_for_customer(customer_id)
                refresh()
                app.show_snackbar(f"Cleared {count} records for {customer.name}")
            except Exception as ex:
                app.show_snackbar(f"Could not clear customer records: {ex}", success=False)

        app.confirm_dialog(
            "Clear Customer Khata",
            f"Permanently remove all transaction records for {customer.name}? "
            "The customer profile will remain, but their balance will reset to zero.",
            clear_records,
            confirm_text="Clear All",
        )

    clear_all_btn = ft.OutlinedButton(
        "Clear All",
        icon=ft.Icons.DELETE_SWEEP_OUTLINED,
        on_click=clear_all_click,
        style=ft.ButtonStyle(
            color=theme.RED,
            side=ft.BorderSide(1, theme.RED),
            shape=ft.RoundedRectangleBorder(radius=10),
        ),
    )

    def refresh(reload_customer: bool = True):
        nonlocal customer
        if reload_customer:
            reloaded = app.customer_service.get(customer_id)
            if reloaded is None:
                app.close_ledger()
                return
            customer = reloaded

        txs = app.transaction_service.for_customer(customer_id)
        clear_all_btn.disabled = not txs
        list_container.controls.clear()
        if not txs:
            list_container.controls.append(
                components.empty_state(
                    ft.Icons.RECEIPT_LONG_OUTLINED,
                    "No transactions yet",
                    "Add the first entry for this customer.",
                )
            )
        else:
            for date_label, items in _group_by_date(txs):
                list_container.controls.append(
                    ft.Text(date_label, size=12, weight=ft.FontWeight.W_600, color=theme.TEXT_SECONDARY)
                )
                for tx in items:
                    list_container.controls.append(_tx_tile(app, tx, refresh))

        balance_section.content = _balance_summary(customer)
        top_name_text.value = customer.name
        top_phone_text.value = customer.phone or "No phone number"

        # Only call update when the controls are attached to the page
        try:
            if getattr(list_container, "page", None):
                list_container.update()
        except RuntimeError:
            pass
        try:
            if getattr(clear_all_btn, "page", None):
                clear_all_btn.update()
        except RuntimeError:
            pass
        try:
            if getattr(balance_section, "page", None):
                balance_section.update()
        except RuntimeError:
            pass
        try:
            if getattr(top_name_text, "page", None):
                top_name_text.update()
        except RuntimeError:
            pass
        try:
            if getattr(top_phone_text, "page", None):
                top_phone_text.update()
        except RuntimeError:
            pass

    def whatsapp_click(e):
        url = app.whatsapp_service.build_share_url(customer)
        # Prefer page.launch_url when available (newer Flet), otherwise
        # fall back to opening the system browser using webbrowser.
        fn = getattr(app.page, "launch_url", None)
        if callable(fn):
            try:
                fn(url)
                return
            except Exception:
                pass
        try:
            webbrowser.open(url, new=2)
        except Exception:
            # Last resort: no-op
            pass

    def open_statement_dialog(e):
        period_picker = ft.Dropdown(
            label="Statement period",
            value=app.statement_service.COMPLETE_HISTORY,
            options=[
                ft.DropdownOption(key=app.statement_service.COMPLETE_HISTORY, text="Complete history"),
                ft.DropdownOption(key=app.statement_service.CURRENT_MONTH, text="Current month"),
                ft.DropdownOption(key=app.statement_service.CUSTOM_RANGE, text="Custom date range"),
            ],
            width=320,
        )
        start_field = ft.TextField(label="Start date", hint_text="YYYY-MM-DD", width=154, visible=False)
        end_field = ft.TextField(label="End date", hint_text="YYYY-MM-DD", width=154, visible=False)

        def period_change(evt):
            is_custom = period_picker.value == app.statement_service.CUSTOM_RANGE
            start_field.visible = is_custom
            end_field.visible = is_custom
            try:
                start_field.update()
                end_field.update()
            except RuntimeError:
                pass

        # Flet 1.x renamed Dropdown's change callback to ``on_select``;
        # older supported Flet releases use ``on_change``.
        if hasattr(period_picker, "on_select"):
            period_picker.on_select = period_change
        else:
            period_picker.on_change = period_change

        def make_pdf():
            return app.statement_service.generate_pdf(
                customer.id, period_picker.value, start_field.value, end_field.value
            )

        def create_pdf(evt):
            try:
                path, _ = make_pdf()
                app.show_snackbar(f"PDF created: {path.name}")
            except Exception as ex:
                app.show_snackbar(f"Could not create PDF: {ex}", success=False)

        async def save_pdf():
            try:
                path, _ = make_pdf()
                if app.file_picker is None:
                    webbrowser.open(path.as_uri(), new=2)
                    app.show_snackbar("PDF opened. Use your system save option to keep a copy.")
                    return
                destination = await app.file_picker.save_file(
                    dialog_title="Save PDF Statement", file_name=path.name,
                    allowed_extensions=["pdf"], src_bytes=path.read_bytes(),
                )
                if destination:
                    app.show_snackbar("PDF statement saved")
            except Exception as ex:
                app.show_snackbar(f"Could not save PDF: {ex}", success=False)

        def save_click(evt):
            try:
                app.page.run_task(save_pdf)
            except Exception as ex:
                app.show_snackbar(f"Could not open save dialog: {ex}", success=False)

        async def share_pdf():
            try:
                path, data = make_pdf()
                if app.share_service is None:
                    webbrowser.open(path.as_uri(), new=2)
                    app.show_snackbar("PDF opened. Native sharing is unavailable in this Flet runtime.")
                    return
                await app.share_service.share_files(
                    [ft.ShareFile(path=str(path), mime_type="application/pdf", name=path.name)],
                    title="Smart Khata PDF Statement",
                    text=app.statement_service.summary_text(data),
                )
            except Exception as ex:
                app.show_snackbar(f"Could not share PDF: {ex}", success=False)

        def share_pdf_click(evt):
            try:
                app.page.run_task(share_pdf)
            except Exception as ex:
                app.show_snackbar(f"Could not start sharing: {ex}", success=False)

        async def share_summary():
            try:
                data = app.statement_service.statement_data(
                    customer.id, period_picker.value, start_field.value, end_field.value
                )
                text = app.statement_service.summary_text(data)
                if app.share_service is None:
                    app.show_snackbar("Native sharing is unavailable in this Flet runtime.", success=False)
                    return
                await app.share_service.share_text(text, title="Smart Khata Summary")
            except Exception as ex:
                app.show_snackbar(f"Could not share summary: {ex}", success=False)

        def share_summary_click(evt):
            try:
                app.page.run_task(share_summary)
            except Exception as ex:
                app.show_snackbar(f"Could not start sharing: {ex}", success=False)

        def back_click(evt):
            app.close_dialog(dialog)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Generate PDF Statement", weight=ft.FontWeight.BOLD),
            content=ft.Column(
                [
                    ft.Text("Choose which ledger entries to include.", size=12, color=theme.TEXT_SECONDARY),
                    period_picker,
                    ft.Row([start_field, end_field], spacing=12),
                ],
                tight=True,
                spacing=12,
            ),
            actions=[
                ft.TextButton("Back", on_click=back_click),
                ft.TextButton("Create PDF", on_click=create_pdf),
                ft.TextButton("Save / Open PDF", on_click=save_click),
                ft.TextButton("Share Summary", on_click=share_summary_click),
                ft.FilledButton("Share PDF", on_click=share_pdf_click),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        app.open_dialog(dialog)

    def back_click(e):
        app.close_ledger()

    def edit_click(e):
        open_customer_form(app, customer=customer, on_saved=refresh)

    def delete_click(e):
        def do_delete():
            app.customer_service.delete(customer.id)
            app.close_ledger()
            app.show_snackbar(f"{customer.name} deleted")

        app.confirm_dialog(
            "Delete Customer",
            f"Delete {customer.name} and all their transaction history? "
            "This cannot be undone.",
            do_delete,
        )

    def add_gave(e):
        open_transaction_form(
            app, customer_id=customer.id, customer_name=customer.name,
            default_type="gave", on_saved=refresh,
        )

    def add_got(e):
        open_transaction_form(
            app, customer_id=customer.id, customer_name=customer.name,
            default_type="got", on_saved=refresh,
        )

    top_name_text = ft.Text(customer.name, size=16, weight=ft.FontWeight.BOLD, color=theme.TEXT_PRIMARY)
    top_phone_text = ft.Text(customer.phone or "No phone number", size=11, color=theme.TEXT_SECONDARY)

    top_bar = ft.Container(
        content=ft.Row(
            [
                ft.IconButton(icon=ft.Icons.ARROW_BACK_ROUNDED, icon_color=theme.TEXT_PRIMARY, on_click=back_click),
                ft.Column([top_name_text, top_phone_text], spacing=0, expand=True),
                ft.PopupMenuButton(
                    icon=ft.Icons.MORE_VERT_ROUNDED,
                    icon_color=theme.TEXT_SECONDARY,
                    items=[
                        ft.PopupMenuItem(content="Edit Customer", icon=ft.Icons.EDIT_OUTLINED, on_click=edit_click),
                        ft.PopupMenuItem(
                            content="Delete Customer", icon=ft.Icons.DELETE_OUTLINE_ROUNDED, on_click=delete_click
                        ),
                    ],
                ),
            ],
            spacing=4,
        ),
        padding=ft.padding.only(left=8, right=12, top=20, bottom=8),
        bgcolor=theme.SURFACE,
        shadow=theme.card_shadow(),
    )

    whatsapp_btn = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.CHAT_ROUNDED, color="#FFFFFF", size=18),
                ft.Text("Share on WhatsApp", size=13, weight=ft.FontWeight.W_600, color="#FFFFFF"),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8,
        ),
        bgcolor=theme.WHATSAPP_GREEN,
        padding=12,
        border_radius=theme.RADIUS_MD,
        on_click=whatsapp_click,
        ink=True,
        margin=ft.margin.symmetric(horizontal=20),
    )

    statement_btn = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.PICTURE_AS_PDF_OUTLINED, color="#FFFFFF", size=18),
                ft.Text("Generate PDF Statement", size=13, weight=ft.FontWeight.W_600, color="#FFFFFF"),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8,
        ),
        bgcolor=theme.PRIMARY,
        padding=12,
        border_radius=theme.RADIUS_MD,
        on_click=open_statement_dialog,
        ink=True,
        margin=ft.margin.symmetric(horizontal=20),
    )

    action_row = ft.Container(
        content=ft.Row(
            [
                ft.FilledButton(
                    "You Gave",
                    icon=ft.Icons.ARROW_UPWARD_ROUNDED,
                    on_click=add_gave,
                    style=ft.ButtonStyle(
                        bgcolor=theme.RED, color="#FFFFFF", shape=ft.RoundedRectangleBorder(radius=12)
                    ),
                    expand=True,
                ),
                ft.FilledButton(
                    "You Got",
                    icon=ft.Icons.ARROW_DOWNWARD_ROUNDED,
                    on_click=add_got,
                    style=ft.ButtonStyle(
                        bgcolor=theme.GREEN, color="#FFFFFF", shape=ft.RoundedRectangleBorder(radius=12)
                    ),
                    expand=True,
                ),
            ],
            spacing=12,
        ),
        padding=ft.padding.symmetric(horizontal=20),
    )

    refresh(reload_customer=False)

    body = ft.Column(
        [
            balance_section,
            ft.Container(height=12),
            action_row,
            ft.Container(height=8),
            statement_btn,
            ft.Container(height=8),
            whatsapp_btn,
            ft.Container(height=16),
            ft.Container(
                content=ft.Row(
                    [
                        ft.Text(
                            "Transaction History",
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color=theme.TEXT_PRIMARY,
                            expand=True,
                        ),
                        clear_all_btn,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                padding=ft.padding.only(left=20, right=20, bottom=8),
            ),
            ft.Container(content=list_container, padding=ft.padding.symmetric(horizontal=20), expand=True),
            ft.Container(height=20),
        ],
        scroll=ft.ScrollMode.AUTO,
        spacing=0,
        expand=True,
    )

    return ft.View(
        route=f"/ledger/{customer_id}",
        padding=0,
        bgcolor=theme.BG,
        controls=[top_bar, body],
    )


def _balance_summary(customer):
    bal = customer.balance
    if bal > 0.004:
        color, sub = theme.GREEN, "You will receive (Udhaar)"
    elif bal < -0.004:
        color, sub = theme.RED, "You owe (Advance balance)"
    else:
        color, sub = theme.TEXT_SECONDARY, "Khata is clear"

    return ft.Container(
        content=ft.Column(
            [
                ft.Text("CURRENT BALANCE", size=11, color=theme.TEXT_SECONDARY, weight=ft.FontWeight.W_600),
                ft.Text(format_currency(abs(bal)), size=28, weight=ft.FontWeight.BOLD, color=color),
                ft.Text(sub, size=12, color=theme.TEXT_SECONDARY),
            ],
            spacing=4,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(vertical=20),
        alignment=ft.Alignment(0, 0),
    )


def _group_by_date(txs):
    groups: dict = {}
    order = []
    today = date.today()
    for tx in txs:
        try:
            d = datetime.strptime(tx.created_at, "%Y-%m-%d %H:%M:%S").date()
        except (ValueError, TypeError):
            d = today
        if d == today:
            label = "Today"
        elif (today - d).days == 1:
            label = "Yesterday"
        else:
            label = d.strftime("%d %b %Y")
        if label not in groups:
            groups[label] = []
            order.append(label)
        groups[label].append(tx)
    return [(label, groups[label]) for label in order]


def _tx_tile(app, tx, refresh):
    is_gave = tx.type == GAVE
    color = theme.RED if is_gave else theme.GREEN
    bg = theme.RED_BG if is_gave else theme.GREEN_BG
    label = "You Gave" if is_gave else "You Got"

    def delete_click(e):
        def do_delete():
            app.transaction_service.delete(tx.id)
            app.show_snackbar("Transaction deleted")
            refresh()

        app.confirm_dialog(
            "Delete Transaction", "This will permanently remove this entry.", do_delete
        )

    subtitle = format_date_display(tx.created_at)
    if tx.note:
        subtitle = f"{subtitle} \u2022 {tx.note}"

    return ft.Container(
        content=ft.Row(
            [
                ft.Container(
                    content=ft.Icon(
                        ft.Icons.ARROW_UPWARD_ROUNDED if is_gave else ft.Icons.ARROW_DOWNWARD_ROUNDED,
                        size=16,
                        color=color,
                    ),
                    bgcolor=bg,
                    width=36,
                    height=36,
                    border_radius=11,
                    alignment=ft.Alignment(0, 0),
                ),
                ft.Column(
                    [
                        ft.Text(label, size=13, weight=ft.FontWeight.W_600, color=theme.TEXT_PRIMARY),
                        ft.Text(subtitle, size=11, color=theme.TEXT_SECONDARY),
                    ],
                    spacing=2,
                    expand=True,
                ),
                ft.Text(
                    f"{'-' if is_gave else '+'}{format_currency(tx.amount)}",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=color,
                ),
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                    icon_color=theme.TEXT_SECONDARY,
                    icon_size=18,
                    on_click=delete_click,
                ),
            ],
            spacing=10,
        ),
        bgcolor=theme.SURFACE,
        padding=12,
        border_radius=theme.RADIUS_MD,
        shadow=theme.card_shadow(),
    )
