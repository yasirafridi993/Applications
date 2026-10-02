"""
update_checker.py
Optional, non-blocking check for a newer Smart Todo release.

Design goals:
- The app must work perfectly with no internet connection at all.
- Never raises: any network/parsing failure just means "no update info".
- Never blocks the UI thread: call check_for_update() from a background
  thread (main.py does this with threading.Thread).

To point this at a real release feed, change UPDATE_INFO_URL to a JSON
endpoint you control (e.g. a raw file in a GitHub repo) that returns:
    {"latest_version": "1.1.0", "play_store_url": "https://play.google.com/store/apps/details?id=com.smarttodo.app"}
"""

import json
import urllib.request
from dataclasses import dataclass
from typing import Optional

CURRENT_VERSION = "1.0.0"

# Replace with your own hosted version-info JSON file when you publish the app.
UPDATE_INFO_URL = "https://raw.githubusercontent.com/example/smart-todo/main/version.json"

PLAY_STORE_URL = "https://play.google.com/store/apps/details?id=com.smarttodo.app"

REQUEST_TIMEOUT_SECONDS = 4


@dataclass
class UpdateResult:
    update_available: bool
    latest_version: str = CURRENT_VERSION
    play_store_url: str = PLAY_STORE_URL
    error: Optional[str] = None


def _version_tuple(version: str):
    """'1.2.10' -> (1, 2, 10), tolerant of malformed strings."""
    parts = []
    for chunk in version.strip().split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts) if parts else (0,)


def check_for_update(timeout: int = REQUEST_TIMEOUT_SECONDS) -> UpdateResult:
    """
    Best-effort update check. Always returns an UpdateResult, never raises.
    Safe to call with no internet connection - simply reports no update.
    """
    try:
        with urllib.request.urlopen(UPDATE_INFO_URL, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))

        latest_version = str(data.get("latest_version", CURRENT_VERSION))
        play_store_url = str(data.get("play_store_url", PLAY_STORE_URL))

        is_newer = _version_tuple(latest_version) > _version_tuple(CURRENT_VERSION)
        return UpdateResult(
            update_available=is_newer,
            latest_version=latest_version,
            play_store_url=play_store_url,
        )
    except Exception as exc:  # noqa: BLE001 - deliberately broad: never crash the app
        # No internet, DNS failure, timeout, bad JSON, etc. all land here.
        return UpdateResult(update_available=False, error=str(exc))
