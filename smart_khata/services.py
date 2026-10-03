"""
services.py
-----------
All business logic for Smart Khata: validation, calculations, and
parameterized SQL queries. UI code never talks to sqlite3 directly -
it always goes through the classes/functions in this file.
"""

import re
import urllib.parse
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

from database import get_connection, get_db_path
from models import GAVE, GOT, Customer, Transaction

# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def format_currency(amount: float) -> str:
    """Format a number as a PKR-style currency string."""
    amount = round(float(amount or 0), 2)
    if amount == int(amount):
        return f"PKR {int(amount):,}"
    return f"\u20b9{amount:,.2f}"


def _time_12h(dt: datetime) -> str:
    hour = dt.strftime("%I").lstrip("0") or "12"
    return f"{hour}:{dt.strftime('%M %p')}"


def format_date_display(created_at: str) -> str:
    """Turn a stored 'YYYY-MM-DD HH:MM:SS' string into a friendly label."""
    try:
        dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return created_at or ""

    today = date.today()
    time_part = _time_12h(dt)
    if dt.date() == today:
        return f"Today, {time_part}"
    if (today - dt.date()).days == 1:
        return f"Yesterday, {time_part}"
    return f"{dt.strftime('%d %b %Y')}, {time_part}"


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------


class CustomerService:
    @staticmethod
    def add(name: str, phone: str = "", note: str = "") -> int:
        name = (name or "").strip()
        if not name:
            raise ValueError("Customer name is required")
        conn = get_connection()
        try:
            cur = conn.execute(
                "INSERT INTO customers (name, phone, note, created_at) "
                "VALUES (?, ?, ?, ?)",
                (name, (phone or "").strip(), (note or "").strip(), now_str()),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    @staticmethod
    def update(customer_id: int, name: str, phone: str = "", note: str = "") -> None:
        name = (name or "").strip()
        if not name:
            raise ValueError("Customer name is required")
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE customers SET name = ?, phone = ?, note = ? WHERE id = ?",
                (name, (phone or "").strip(), (note or "").strip(), customer_id),
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def delete(customer_id: int) -> None:
        conn = get_connection()
        try:
            conn.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def count() -> int:
        conn = get_connection()
        try:
            row = conn.execute("SELECT COUNT(*) AS c FROM customers").fetchone()
            return row["c"] if row else 0
        finally:
            conn.close()

    @staticmethod
    def _all_balances() -> Dict[int, float]:
        conn = get_connection()
        try:
            rows = conn.execute(
                """
                SELECT customer_id,
                       SUM(CASE WHEN type = 'gave' THEN amount ELSE -amount END) AS bal
                FROM transactions
                GROUP BY customer_id
                """
            ).fetchall()
            return {r["customer_id"]: (r["bal"] or 0.0) for r in rows}
        finally:
            conn.close()

    @staticmethod
    def _balance_for(customer_id: int) -> float:
        conn = get_connection()
        try:
            row = conn.execute(
                """
                SELECT SUM(CASE WHEN type = 'gave' THEN amount ELSE -amount END) AS bal
                FROM transactions WHERE customer_id = ?
                """,
                (customer_id,),
            ).fetchone()
            return (row["bal"] or 0.0) if row else 0.0
        finally:
            conn.close()

    @classmethod
    def get_all(cls, search: str = "") -> List[Customer]:
        conn = get_connection()
        try:
            search = (search or "").strip()
            if search:
                like = f"%{search}%"
                rows = conn.execute(
                    "SELECT * FROM customers WHERE name LIKE ? OR phone LIKE ? "
                    "ORDER BY name COLLATE NOCASE",
                    (like, like),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM customers ORDER BY name COLLATE NOCASE"
                ).fetchall()
        finally:
            conn.close()

        balances = cls._all_balances()
        return [
            Customer(
                id=r["id"],
                name=r["name"],
                phone=r["phone"] or "",
                note=r["note"] or "",
                created_at=r["created_at"],
                balance=balances.get(r["id"], 0.0),
            )
            for r in rows
        ]

    @classmethod
    def get(cls, customer_id: int) -> Optional[Customer]:
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM customers WHERE id = ?", (customer_id,)
            ).fetchone()
        finally:
            conn.close()
        if not row:
            return None
        return Customer(
            id=row["id"],
            name=row["name"],
            phone=row["phone"] or "",
            note=row["note"] or "",
            created_at=row["created_at"],
            balance=cls._balance_for(customer_id),
        )


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------


class TransactionService:
    @staticmethod
    def add(customer_id: int, tx_type: str, amount: float, note: str = "") -> int:
        if tx_type not in (GAVE, GOT):
            raise ValueError("Invalid transaction type")
        if amount is None or amount <= 0:
            raise ValueError("Amount must be greater than zero")
        conn = get_connection()
        try:
            cur = conn.execute(
                "INSERT INTO transactions (customer_id, type, amount, note, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (customer_id, tx_type, round(float(amount), 2), (note or "").strip(), now_str()),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    @staticmethod
    def delete(tx_id: int) -> None:
        conn = get_connection()
        try:
            conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def clear_for_customer(customer_id: int) -> int:
        conn = get_connection()
        try:
            cur = conn.execute(
                "DELETE FROM transactions WHERE customer_id = ?", (customer_id,)
            )
            conn.commit()
            return cur.rowcount
        finally:
            conn.close()

    @staticmethod
    def for_customer(customer_id: int) -> List[Transaction]:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM transactions WHERE customer_id = ? "
                "ORDER BY created_at DESC, id DESC",
                (customer_id,),
            ).fetchall()
        finally:
            conn.close()
        return [
            Transaction(
                id=r["id"],
                customer_id=r["customer_id"],
                type=r["type"],
                amount=r["amount"],
                note=r["note"] or "",
                created_at=r["created_at"],
            )
            for r in rows
        ]

    @staticmethod
    def all_with_customer(search: str = "") -> List[dict]:
        conn = get_connection()
        try:
            search = (search or "").strip()
            query = (
                "SELECT t.id, t.customer_id, t.type, t.amount, t.note, t.created_at, "
                "c.name AS customer_name "
                "FROM transactions t JOIN customers c ON c.id = t.customer_id"
            )
            params: tuple = ()
            if search:
                query += " WHERE c.name LIKE ? OR t.note LIKE ?"
                like = f"%{search}%"
                params = (like, like)
            query += " ORDER BY t.created_at DESC, t.id DESC"
            rows = conn.execute(query, params).fetchall()
        finally:
            conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def today_count() -> int:
        today = date.today().strftime("%Y-%m-%d")
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM transactions WHERE substr(created_at, 1, 10) = ?",
                (today,),
            ).fetchone()
            return row["c"] if row else 0
        finally:
            conn.close()

    @staticmethod
    def totals_for_customer(customer_id: int) -> Dict[str, float]:
        conn = get_connection()
        try:
            row = conn.execute(
                """
                SELECT
                    COALESCE(SUM(CASE WHEN type = 'gave' THEN amount ELSE 0 END), 0) AS total_gave,
                    COALESCE(SUM(CASE WHEN type = 'got' THEN amount ELSE 0 END), 0) AS total_got
                FROM transactions WHERE customer_id = ?
                """,
                (customer_id,),
            ).fetchone()
            return {"gave": row["total_gave"], "got": row["total_got"]}
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# PDF statements
# ---------------------------------------------------------------------------


class StatementService:
    """Build local, printable customer statements from the existing SQLite data."""

    COMPLETE_HISTORY = "complete"
    CURRENT_MONTH = "month"
    CUSTOM_RANGE = "custom"

    @staticmethod
    def _parse_date(value: str, field_name: str) -> date:
        try:
            return datetime.strptime((value or "").strip(), "%Y-%m-%d").date()
        except ValueError as ex:
            raise ValueError(f"{field_name} must use YYYY-MM-DD format") from ex

    @classmethod
    def _date_range(cls, period: str, start_date: str = "", end_date: str = ""):
        today = date.today()
        if period == cls.COMPLETE_HISTORY:
            return None, None, "Complete history"
        if period == cls.CURRENT_MONTH:
            start = today.replace(day=1)
            return start, today, today.strftime("%B %Y")
        if period == cls.CUSTOM_RANGE:
            start = cls._parse_date(start_date, "Start date")
            end = cls._parse_date(end_date, "End date")
            if start > end:
                raise ValueError("Start date cannot be after end date")
            return start, end, f"{start.strftime('%d %b %Y')} - {end.strftime('%d %b %Y')}"
        raise ValueError("Invalid statement period")

    @classmethod
    def statement_data(cls, customer_id: int, period: str = COMPLETE_HISTORY,
                       start_date: str = "", end_date: str = "") -> Dict:
        customer = CustomerService.get(customer_id)
        if customer is None:
            raise ValueError("Customer not found")

        start, end, label = cls._date_range(period, start_date, end_date)
        query = "SELECT * FROM transactions WHERE customer_id = ?"
        params: list = [customer_id]
        if start:
            query += " AND substr(created_at, 1, 10) >= ?"
            params.append(start.isoformat())
        if end:
            query += " AND substr(created_at, 1, 10) <= ?"
            params.append(end.isoformat())
        query += " ORDER BY created_at ASC, id ASC"

        conn = get_connection()
        try:
            rows = conn.execute(query, params).fetchall()
        finally:
            conn.close()

        transactions = [
            Transaction(id=row["id"], customer_id=row["customer_id"], type=row["type"],
                        amount=row["amount"], note=row["note"] or "", created_at=row["created_at"])
            for row in rows
        ]
        total_gave = sum(float(tx.amount) for tx in transactions if tx.type == GAVE)
        total_got = sum(float(tx.amount) for tx in transactions if tx.type == GOT)
        balance = round(total_gave - total_got, 2)
        return {
            "customer": customer,
            "transactions": transactions,
            "total_gave": total_gave,
            "total_got": total_got,
            "balance": balance,
            "period_label": label,
        }

    @staticmethod
    def status_for_balance(balance: float) -> str:
        if balance > 0.004:
            return "Customer owes you"
        if balance < -0.004:
            return "You owe customer (advance)"
        return "Account settled"

    @classmethod
    def summary_text(cls, data: Dict) -> str:
        """Short, platform-neutral text used by the native share sheet."""
        customer = data["customer"]
        balance = data["balance"]
        if balance > 0.004:
            balance_label = "Customer owes you"
        elif balance < -0.004:
            balance_label = "Customer advance"
        else:
            balance_label = "Balance"
        return "\n".join([
            "Smart Khata - Account Summary",
            f"Customer: {customer.name}",
            f"Period: {data['period_label']}",
            f"Credit given / consumed: {format_currency(data['total_gave'])}",
            f"Payments received: {format_currency(data['total_got'])}",
            f"{balance_label}: {format_currency(abs(balance))}",
            f"Status: {cls.status_for_balance(balance)}",
        ])

    @staticmethod
    def _safe_filename(value: str) -> str:
        return re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_") or "customer"

    @classmethod
    def generate_pdf(cls, customer_id: int, period: str = COMPLETE_HISTORY,
                     start_date: str = "", end_date: str = "") -> tuple[Path, Dict]:
        """Generate an A4 PDF in the local app-data folder and return it with its data."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib.units import mm
            from reportlab.platypus import (KeepTogether, Paragraph, SimpleDocTemplate,
                                            Spacer, Table, TableStyle)
        except ImportError as ex:
            raise RuntimeError("PDF support is unavailable. Install the ReportLab dependency.") from ex

        data = cls.statement_data(customer_id, period, start_date, end_date)
        customer = data["customer"]
        statement_dir = Path(get_db_path()).parent / "statements"
        statement_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = statement_dir / f"SmartKhata_{cls._safe_filename(customer.name)}_{stamp}.pdf"

        navy, green, red, muted = "#183153", "#168A5B", "#C53A3A", "#5F6B7A"
        styles = getSampleStyleSheet()
        title = ParagraphStyle("StatementTitle", parent=styles["Heading1"], fontName="Helvetica-Bold",
                               fontSize=20, leading=24, textColor=colors.HexColor(navy), spaceAfter=2)
        meta = ParagraphStyle("StatementMeta", parent=styles["Normal"], fontSize=8.5, leading=12,
                              textColor=colors.HexColor(muted))
        body = ParagraphStyle("StatementBody", parent=styles["Normal"], fontSize=8.5, leading=11)
        amount = ParagraphStyle("StatementAmount", parent=body, alignment=TA_RIGHT)
        status_style = ParagraphStyle("StatementStatus", parent=styles["Normal"], fontName="Helvetica-Bold",
                                      fontSize=11, leading=14, textColor=colors.HexColor(green))
        legend_style = ParagraphStyle("StatementLegend", parent=meta, fontSize=8, leading=11)

        def money(value: float) -> str:
            return format_currency(abs(value))

        def header_footer(canvas, doc):
            canvas.saveState()
            width, height = A4
            canvas.setStrokeColor(colors.HexColor("#DDE4EC"))
            canvas.line(16 * mm, height - 16 * mm, width - 16 * mm, height - 16 * mm)
            canvas.setFillColor(colors.HexColor(navy))
            canvas.circle(21 * mm, height - 11 * mm, 3.5 * mm, fill=1, stroke=0)
            canvas.setFillColor(colors.white)
            canvas.setFont("Helvetica-Bold", 8)
            canvas.drawCentredString(21 * mm, height - 12.3 * mm, "SK")
            canvas.setFillColor(colors.HexColor(muted))
            canvas.setFont("Helvetica", 8)
            canvas.drawRightString(width - 16 * mm, 10 * mm, f"Page {doc.page}")
            canvas.drawString(16 * mm, 10 * mm, "Smart Khata • Customer Statement")
            canvas.restoreState()

        doc = SimpleDocTemplate(str(output), pagesize=A4, rightMargin=16 * mm, leftMargin=16 * mm,
                                topMargin=23 * mm, bottomMargin=18 * mm, title="Smart Khata Statement")
        story = [
            Paragraph("SMART KHATA", title),
            Paragraph("Customer Account Statement", meta),
            Spacer(1, 5 * mm),
        ]
        contact = customer.phone or "Not provided"
        details = Table([
            [Paragraph("<b>Customer</b><br/>" + customer.name, body),
             Paragraph("<b>Contact</b><br/>" + contact, body),
             Paragraph("<b>Statement period</b><br/>" + data["period_label"], body)],
        ], colWidths=[58 * mm, 52 * mm, 58 * mm])
        details.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3F6F9")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDE4EC")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDE4EC")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        story += [details, Spacer(1, 5 * mm)]
        if data["balance"] > 0.004:
            balance_label = "CUSTOMER OWES YOU"
        elif data["balance"] < -0.004:
            balance_label = "CUSTOMER ADVANCE"
        else:
            balance_label = "BALANCE"
        summary = Table([
                ["CREDIT GIVEN / CONSUMED", "PAYMENTS RECEIVED", balance_label],
            [money(data["total_gave"]), money(data["total_got"]), money(data["balance"])],
        ], colWidths=[56 * mm, 56 * mm, 56 * mm])
        summary.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(navy)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F3F6F9")),
            ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"), ("FONTSIZE", (0, 1), (-1, 1), 12),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDE4EC")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDE4EC")),
            ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        story += [summary, Spacer(1, 3 * mm)]
        status_color = green if data["balance"] > 0.004 else red if data["balance"] < -0.004 else muted
        status_style.textColor = colors.HexColor(status_color)
        story += [
            Paragraph(f"Final status: {cls.status_for_balance(data['balance'])}", status_style),
            Paragraph(
                f"<font color='{red}'>Red: credit given / items consumed</font>"
                f" &nbsp;&nbsp; <font color='{green}'>Green: payments received</font>",
                legend_style,
            ),
            Spacer(1, 4 * mm),
        ]
        story.append(Paragraph("Transaction History", ParagraphStyle("History", parent=title, fontSize=13, leading=16)))
        rows = [["Date", "Entry", "Amount", "Details"]]
        row_colors = []
        for tx in data["transactions"]:
            try:
                tx_date = datetime.strptime(tx.created_at, "%Y-%m-%d %H:%M:%S").strftime("%d %b %Y\n%I:%M %p")
            except ValueError:
                tx_date = tx.created_at
            is_given = tx.type == GAVE
            entry_color = red if is_given else green
            row_colors.append((entry_color, "#FCEEEE" if is_given else "#EAF6F0"))
            rows.append([
                Paragraph(tx_date.replace("\n", "<br/>"), body),
                Paragraph(f"<font color='{entry_color}'><b>"
                          f"{'Credit given' if is_given else 'Payment received'}</b></font>", body),
                Paragraph(f"<font color='{entry_color}'><b>{money(tx.amount)}</b></font>", amount),
                Paragraph(tx.note or "—", body),
            ])
        if len(rows) == 1:
            rows.append([Paragraph("No transactions for this period.", body), "", "", ""])
        history = Table(rows, colWidths=[35 * mm, 30 * mm, 32 * mm, 71 * mm], repeatRows=1)
        history.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(navy)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#DDE4EC")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        for row_index, (_, row_bg) in enumerate(row_colors, start=1):
            history.setStyle(TableStyle([
                ("BACKGROUND", (0, row_index), (-1, row_index), colors.HexColor(row_bg)),
            ]))
        story.append(history)
        doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
        return output, data


# ---------------------------------------------------------------------------
# Dashboard aggregates
# ---------------------------------------------------------------------------


class DashboardService:
    @staticmethod
    def get_stats() -> Dict[str, float]:
        conn = get_connection()
        try:
            rows = conn.execute(
                """
                SELECT customer_id,
                       SUM(CASE WHEN type = 'gave' THEN amount ELSE -amount END) AS bal
                FROM transactions
                GROUP BY customer_id
                """
            ).fetchall()
        finally:
            conn.close()

        receivable = sum(r["bal"] for r in rows if r["bal"] and r["bal"] > 0)
        payable = sum(-r["bal"] for r in rows if r["bal"] and r["bal"] < 0)
        return {
            "receivable": receivable,
            "payable": payable,
            "today_transactions": TransactionService.today_count(),
            "customers_count": CustomerService.count(),
        }


# ---------------------------------------------------------------------------
# WhatsApp sharing (no API key / no paid integration - just a wa.me deep link)
# ---------------------------------------------------------------------------


class WhatsAppService:
    @staticmethod
    def build_message(customer: Customer) -> str:
        totals = TransactionService.totals_for_customer(customer.id)
        lines = [
            "*Smart Khata - Account Summary*",
            "",
            f"Customer: {customer.name}",
        ]
        if customer.phone:
            lines.append(f"Phone: {customer.phone}")
        lines += [
            "",
            f"You Gave (Udhaar): {format_currency(totals['gave'])}",
            f"You Got (Received): {format_currency(totals['got'])}",
            "",
        ]

        bal = round(customer.balance, 2)
        if bal > 0:
            lines.append(f"Remaining Udhaar Amount: {format_currency(bal)}")
        elif bal < 0:
            lines.append(f"Advance / Customer Balance: {format_currency(abs(bal))}")
        else:
            lines.append("Khata is Clear")

        lines += ["", "Generated by Smart Khata"]
        return "\n".join(lines)

    @staticmethod
    def build_share_url(customer: Customer) -> str:
        message = WhatsAppService.build_message(customer)
        text = urllib.parse.quote(message)
        digits = "".join(ch for ch in (customer.phone or "") if ch.isdigit())
        if digits:
            return f"https://wa.me/{digits}?text={text}"
        # No phone on file - open WhatsApp's contact picker with the text ready.
        return f"https://wa.me/?text={text}"
