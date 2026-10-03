import flet as ft

if not hasattr(ft, "padding") or not hasattr(getattr(ft, "padding", None), "only"):
    class _CompatPadding:
        @staticmethod
        def only(*, left=0, top=0, right=0, bottom=0):
            return ft.Padding(left=left, top=top, right=right, bottom=bottom)

        @staticmethod
        def symmetric(*, horizontal=0, vertical=0):
            return ft.Padding(left=horizontal, top=vertical, right=horizontal, bottom=vertical)

        @staticmethod
        def all(value):
            return ft.Padding(left=value, top=value, right=value, bottom=value)

    class _CompatMargin:
        @staticmethod
        def symmetric(*, horizontal=0, vertical=0):
            return ft.Margin(left=horizontal, top=vertical, right=horizontal, bottom=vertical)

        @staticmethod
        def all(value):
            return ft.Margin(left=value, top=value, right=value, bottom=value)

    ft.padding = _CompatPadding()
    ft.margin = _CompatMargin()

from database import init_db
from services import CustomerService, DashboardService, StatementService, TransactionService, WhatsAppService
from ui import theme
from ui import dashboard, customers, ledger, transactions


class SmartKhataApp:
    """Central controller shared by every screen.

    UI modules never touch flet.Page internals like dialogs/overlays
    directly - they go through open_dialog/close_dialog/show_snackbar so
    the app keeps working the same way regardless of which Flet version
    is installed (Flet's dialog/snackbar API has changed more than once).
    """

    def __init__(self, page: ft.Page):
        self.page = page

        # Services (kept as class references - they're stateless / static).
        self.customer_service = CustomerService
        self.transaction_service = TransactionService
        self.dashboard_service = DashboardService
        self.whatsapp_service = WhatsAppService
        self.statement_service = StatementService
        self.share_service = None
        self.file_picker = None
        self._setup_platform_services()

        self.tab_index = 0
        self._last_overlay = None

        self._setup_page()

        self.body = ft.AnimatedSwitcher(
            content=ft.Container(),
            transition=ft.AnimatedSwitcherTransition.FADE,
            duration=220,
            reverse_duration=180,
            switch_in_curve=ft.AnimationCurve.EASE_OUT,
            switch_out_curve=ft.AnimationCurve.EASE_IN,
            expand=True,
        )
        self.nav_bar = self._build_nav_bar()
        self.root_view = ft.View(
            route="/",
            padding=0,
            bgcolor=theme.BG,
            controls=[self.body],
            navigation_bar=self.nav_bar,
        )

        self.page.views.append(self.root_view)
        self.page.on_view_pop = self._on_view_pop
        self.show_tab(0)

    def _setup_platform_services(self):
        """Register native services when the installed Flet runtime provides them."""
        try:
            if hasattr(ft, "Share"):
                self.share_service = ft.Share()
                self.page.services.append(self.share_service)
            if hasattr(ft, "FilePicker"):
                self.file_picker = ft.FilePicker()
                self.page.services.append(self.file_picker)
        except Exception:
            # Statement creation still works even if a platform service is absent.
            self.share_service = None
            self.file_picker = None

    # ------------------------------------------------------------------
    # Page / window setup
    # ------------------------------------------------------------------

    def _setup_page(self):
        page = self.page
        page.title = "Smart Khata"
        page.bgcolor = theme.BG
        page.padding = 0
        page.spacing = 0
        page.theme_mode = ft.ThemeMode.LIGHT
        try:
            page.theme = ft.Theme(color_scheme_seed=theme.PRIMARY)
        except Exception:
            pass
        self._set_window_size(402, 874)

    def _set_window_size(self, width, height):
        page = self.page
        try:
            page.window.width = width
            page.window.height = height
            page.window.min_width = 360
            page.window.min_height = 640
        except Exception:
            try:
                page.window_width = width
                page.window_height = height
            except Exception:
                pass

    def _build_nav_bar(self):
        return ft.NavigationBar(
            selected_index=0,
            bgcolor=theme.SURFACE,
            indicator_color=theme.PRIMARY_LIGHT,
            on_change=self._on_nav_change,
            destinations=[
                ft.NavigationBarDestination(
                    icon=ft.Icons.SPACE_DASHBOARD_OUTLINED,
                    selected_icon=ft.Icons.SPACE_DASHBOARD_ROUNDED,
                    label="Dashboard",
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.PEOPLE_ALT_OUTLINED,
                    selected_icon=ft.Icons.PEOPLE_ALT_ROUNDED,
                    label="Customers",
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.RECEIPT_LONG_OUTLINED,
                    selected_icon=ft.Icons.RECEIPT_LONG_ROUNDED,
                    label="Transactions",
                ),
            ],
        )

    def _on_nav_change(self, e):
        try:
            index = e.control.selected_index
        except Exception:
            index = int(e.data)
        self.show_tab(index)

    # ------------------------------------------------------------------
    # Tab navigation (Dashboard / Customers / Transactions)
    # ------------------------------------------------------------------

    def show_tab(self, index: int):
        self.tab_index = index
        self.nav_bar.selected_index = index
        if index == 0:
            content = dashboard.build_dashboard_view(self)
        elif index == 1:
            content = customers.build_customers_view(self)
        else:
            content = transactions.build_transactions_view(self)
        self.body.content = content
        self.page.update()

    def refresh_current_tab(self):
        self.show_tab(self.tab_index)

    # ------------------------------------------------------------------
    # Drill-down navigation (Customer Ledger)
    # ------------------------------------------------------------------

    def open_ledger(self, customer_id: int):
        view = ledger.build_ledger_view(self, customer_id)
        self.page.views.append(view)
        self.page.update()

    def close_ledger(self):
        if len(self.page.views) > 1:
            self.page.views.pop()
        self.page.update()
        self.refresh_current_tab()

    def _on_view_pop(self, e):
        if len(self.page.views) > 1:
            self.page.views.pop()
        self.page.update()
        self.refresh_current_tab()

    # ------------------------------------------------------------------
    # Dialogs / snackbars
    #
    # Flet's API for showing dialogs & snackbars has changed across
    # versions (page.dialog+.open, then page.open()/page.close(), then
    # page.show_dialog()/page.pop_dialog()). These two helpers try the
    # newest known method first and fall back gracefully, so the app
    # keeps working no matter which Flet release is installed.
    # ------------------------------------------------------------------

    def open_dialog(self, control):
        self._last_overlay = control
        page = self.page
        for name in ("show_dialog", "open_dialog", "open"):
            fn = getattr(page, name, None)
            if callable(fn):
                fn(control)
                return
        # Oldest supported fallback.
        control.open = True
        page.dialog = control
        page.update()

    def close_dialog(self, control=None):
        page = self.page
        for name in ("pop_dialog", "close_dialog"):
            fn = getattr(page, name, None)
            if callable(fn):
                fn()
                return
        target = control or self._last_overlay
        fn = getattr(page, "close", None)
        if callable(fn) and target is not None:
            fn(target)
            return
        if target is not None:
            target.open = False
        page.update()

    def show_snackbar(self, message: str, success: bool = True):
        snack = ft.SnackBar(
            content=ft.Text(message, color="#FFFFFF"),
            bgcolor=theme.GREEN if success else theme.RED,
            behavior=ft.SnackBarBehavior.FLOATING,
            margin=12,
            shape=ft.RoundedRectangleBorder(radius=12),
        )
        self.open_dialog(snack)

    def confirm_dialog(self, title: str, message: str, on_confirm, confirm_text="Delete", danger=True):
        def _cancel(e):
            self.close_dialog()

        def _confirm(e):
            self.close_dialog()
            on_confirm()

        dlg = ft.AlertDialog(
            modal=True,
            shape=ft.RoundedRectangleBorder(radius=theme.RADIUS_MD),
            title=ft.Text(title, weight=ft.FontWeight.BOLD),
            content=ft.Text(message, color=theme.TEXT_SECONDARY),
            actions=[
                ft.TextButton("Cancel", on_click=_cancel),
                ft.FilledButton(
                    confirm_text,
                    on_click=_confirm,
                    style=ft.ButtonStyle(
                        bgcolor=theme.RED if danger else theme.PRIMARY, color="#FFFFFF"
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.open_dialog(dlg)


def main(page: ft.Page):
    try:
        init_db()
    except Exception as ex:
        page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.ERROR_OUTLINE_ROUNDED, color=theme.RED, size=40),
                        ft.Text("Smart Khata could not start", weight=ft.FontWeight.BOLD),
                        ft.Text(str(ex), color=theme.TEXT_SECONDARY, size=12),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                alignment=ft.Alignment(0, 0),
                expand=True,
                padding=24,
            )
        )
        return

    # Show splash first, then start the main app
    def _start_app():
        SmartKhataApp(page)

    try:
        # ensure window is sized to the mobile layout before starting app
        try:
            page.window.width = 402
            page.window.height = 874
        except Exception:
            pass
        _start_app()
    except Exception:
        _start_app()


if __name__ == "__main__":
    if hasattr(ft, "run"):
        ft.run(main)
    else:  # pragma: no cover - older Flet versions
        ft.app(target=main)
