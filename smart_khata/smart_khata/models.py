"""
models.py
---------
Plain data structures shared across the app. No database or UI code here.
"""

from dataclasses import dataclass
from typing import Optional

# Transaction type constants.
# GAVE  -> "You Gave" / Udhaar   -> increases what the customer owes you.
# GOT   -> "You Got" / Received  -> decreases what the customer owes you.
GAVE = "gave"
GOT = "got"

TYPE_LABELS = {
    GAVE: "You Gave",
    GOT: "You Got",
}


@dataclass
class Customer:
    id: Optional[int]
    name: str
    phone: str = ""
    note: str = ""
    created_at: str = ""
    # Positive balance  -> customer owes the shopkeeper (receivable).
    # Negative balance  -> shopkeeper owes the customer (payable/advance).
    balance: float = 0.0


@dataclass
class Transaction:
    id: Optional[int]
    customer_id: int
    type: str  # GAVE or GOT
    amount: float
    note: str = ""
    created_at: str = ""
