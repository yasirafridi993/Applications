# Smart Todo

Smart Todo is a lightweight, offline-first task manager built with Python and Flet. It helps you capture tasks, organize them by due date and status, and quickly review what needs attention today without depending on a remote service.

## Highlights

- Add, edit, complete, and delete tasks
- Store everything locally in SQLite
- Search and filter by All, Today, Pending, and Completed
- Track due dates and optional due times
- View a dashboard summary for total, pending, completed, and due-today items
- Toggle between light and dark themes
- Run without a backend or internet connection for core task management
- Show optional AdMob banners on supported mobile builds

## Screens and workflow

The app uses a simple two-tab layout:

- Home: summary cards and quick task overview
- Tasks: search, filters, and task list management

A floating action button allows adding new tasks from anywhere in the app, and task editing uses a reusable dialog flow.

## Project structure

```text
smart_todo/
├── main.py
├── pyproject.toml
├── requirements.txt
├── README.md
├── smart_todo.db
├── android/
│   └── README.md
├── backend/
│   ├── __init__.py
│   ├── database.py
│   ├── models.py
│   └── update_checker.py
├── frontend/
│   ├── __init__.py
│   ├── home.py
│   ├── task_form.py
│   └── tasks.py
├── monetization/
│   ├── __init__.py
│   └── admob/
│       ├── __init__.py
│       ├── admob_service.py
│       └── config.py
└── .venv/
```

## Tech stack

- Python 3.10+
- Flet
- SQLite
- AdMob via flet-ads

## Prerequisites

- Python 3.10 or newer
- pip
- A local environment for running Flet apps

## Setup

1. Open a terminal in the project root.
2. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```powershell
pip install -r requirements.txt
```

Optional if you want the project installed as a package as well:

```powershell
pip install -e .
```

## Run locally

```powershell
python main.py
```

Or directly with the virtual environment:

```powershell
.\.venv\Scripts\python.exe main.py
```

## App behavior and notes

- The database file is created automatically in the project root as `smart_todo.db`.
- Core app features work without a backend or internet connection.
- Update checks run in a background thread and fail silently if unavailable.
- AdMob is optional and safely disabled when unsupported or unavailable.
- The app currently focuses on desktop/local testing and mobile packaging compatibility.

## Configuration

- Android metadata and app settings live in [pyproject.toml](pyproject.toml).
- AdMob configuration is handled in the monetization layer under the [monetization/admob](monetization/admob) folder.
- The database logic lives in [backend/database.py](backend/database.py), and the task model is defined in [backend/models.py](backend/models.py).

## License

This project is provided as-is for local development and learning. Add an appropriate license before publishing or sharing it publicly.

## Future ideas

- recurring tasks
- drag-to-reorder list
- categories or tags
- cloud sync
- custom reminders
- offline export/import
