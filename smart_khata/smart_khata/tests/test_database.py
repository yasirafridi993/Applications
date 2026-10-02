import os
from pathlib import Path

from database import get_db_path, migrate_legacy_db


def test_get_db_path_uses_appdata_on_windows(monkeypatch, tmp_path):
    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setenv("APPDATA", str(tmp_path))

    db_path = get_db_path()

    assert db_path == str(Path(tmp_path) / "SmartKhata" / "smart_khata.db")


def test_migrate_legacy_db_moves_existing_file(tmp_path):
    legacy_dir = tmp_path / "legacy"
    legacy_dir.mkdir()
    legacy_db = legacy_dir / "smart_khata.db"
    legacy_db.write_text("legacy-data")

    appdata_dir = tmp_path / "AppData" / "Roaming" / "SmartKhata"
    appdata_dir.mkdir(parents=True)
    new_db = appdata_dir / "smart_khata.db"

    moved = migrate_legacy_db(str(legacy_db), str(new_db))

    assert moved is True
    assert new_db.exists()
    assert new_db.read_text() == "legacy-data"
    assert not legacy_db.exists()
