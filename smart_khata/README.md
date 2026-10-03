# Smart Khata

Smart Khata is a lightweight Python desktop/mobile app for managing customer credit and transactions using a local SQLite database. It is built with Flet and designed to run fully offline without any backend server, login system, or cloud sync.

## Overview

This project helps individuals and small businesses track:

- customer balances
- credit given and received
- transaction history
- per-customer ledger details
- WhatsApp-ready settlement summaries

## Features

- Customer management with add, edit, and delete actions
- Transaction recording for credit and payment flows
- Dashboard with summary information
- Customer-specific ledger view
- Clear-all action for a customer's transaction history, with confirmation
- Automatic balance calculation
- Customer-friendly PDF statements with balance status and color-coded entries
- WhatsApp message generation for follow-ups
- Local SQLite storage for offline usage
- Modern desktop/mobile UI built with Flet

## How balances work

The app uses a straightforward credit model:

- You Gave (Udhaar): increases the customer balance you are owed
- You Got (Received): decreases the amount owed
- Customer balance = total You Gave - total You Got

Balance meanings:

- Positive: customer owes you
- Negative: you owe the customer
- Zero: account is settled

PDF statements show credit given/consumed in red and payments received in green.
The balance summary clearly identifies whether the customer owes you or has an
advance balance.

## Tech stack

- Python 3.10+
- Flet
- SQLite

## Requirements

- Python 3.10 or newer
- pip

## Installation

Open a terminal in the project folder and create a virtual environment:

```powershell
py -3 -m venv .venv
```

Install dependencies through the environment's Python rather than the `pip`
launcher:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If the project folder has been moved or copied with an existing `.venv`, rebuild
that environment first because virtual environments contain location-specific
launchers and are not portable:

```powershell
py -3 -m venv --clear .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run the app

```powershell
.\.venv\Scripts\python.exe main.py
```

On the first launch, the app automatically creates a local SQLite database file and required tables in the project folder.

## Project structure

```text
smart_khata/
├── main.py                 # App entry point and UI controller
├── database.py             # SQLite setup and schema creation
├── models.py               # Data models for customers and transactions
├── services.py             # Business logic and query handling
├── requirements.txt        # Python dependencies
├── pyproject.toml          # Project metadata
├── README.md               # Project documentation
├── assets/
│   └── icon.svg            # App icon
├── ui/
│   ├── __init__.py
│   ├── theme.py            # Shared styling and colors
│   ├── components.py       # Reusable UI elements
│   ├── dashboard.py        # Dashboard screen
│   ├── customers.py        # Customer management screen
│   ├── ledger.py           # Customer ledger view
│   └── transactions.py     # Transaction screen
├── tests/
│   └── test_database.py    # Database validation tests
└── .venv/                  # Local virtual environment (optional)
```

## WhatsApp sharing

The app can generate a WhatsApp share message for a customer using the customer's phone number when available. It uses the standard WhatsApp link flow and does not rely on a backend or API.

For best results:

- save phone numbers with the country code
- example: `9230012345678` for Pakistan

If no phone number is available, the app falls back to the WhatsApp contact picker with the summary pre-filled.

## Notes

- Deleting a customer also removes their transaction history.
- This app is designed to be fully local and offline.
- Data is stored in a SQLite file instead of a remote server.

## License

This project is intended for local personal or small-business use.

## Contribution

Contributions, fixes, and UI improvements are welcome. Please keep the project lightweight, source-focused, and easy to run locally.
