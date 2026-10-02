from pathlib import Path

import database
import services
from database import init_db
from models import GAVE, GOT
from services import CustomerService, StatementService, TransactionService


def test_statement_pdf_and_filtered_totals(tmp_path, monkeypatch):
    db_file = tmp_path / "smart_khata.db"
    monkeypatch.setattr(database, "DB_PATH", str(db_file))
    monkeypatch.setattr(services, "get_db_path", lambda: str(db_file))
    init_db()

    customer_id = CustomerService.add("Ayesha", "03001234567")
    TransactionService.add(customer_id, GAVE, 1200, "Groceries")
    TransactionService.add(customer_id, GOT, 250, "Part payment")

    data = StatementService.statement_data(customer_id)
    assert data["total_gave"] == 1200
    assert data["total_got"] == 250
    assert data["balance"] == 950
    assert StatementService.status_for_balance(data["balance"]) == "You Have to Receive"
    assert "Ayesha" in StatementService.summary_text(data)

    pdf_path, pdf_data = StatementService.generate_pdf(customer_id)
    assert pdf_data["balance"] == 950
    assert pdf_path.exists()
    assert pdf_path.read_bytes().startswith(b"%PDF")


def test_custom_statement_range_rejects_invalid_dates(tmp_path, monkeypatch):
    db_file = tmp_path / "smart_khata.db"
    monkeypatch.setattr(database, "DB_PATH", str(db_file))
    monkeypatch.setattr(services, "get_db_path", lambda: str(db_file))
    init_db()
    customer_id = CustomerService.add("Bilal")

    try:
        StatementService.statement_data(customer_id, StatementService.CUSTOM_RANGE, "2026-09-02", "2026-09-01")
    except ValueError as ex:
        assert "Start date" in str(ex)
    else:
        raise AssertionError("Invalid date ranges must be rejected")
