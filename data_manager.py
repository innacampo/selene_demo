import json
from pathlib import Path
from datetime import datetime


# ============================================================================
# Constants
# ============================================================================

USER_DATA_DIR = Path("user_data")
PULSE_HISTORY_FILE = USER_DATA_DIR / "pulse_history.json"


# ============================================================================
# Data Management Functions
# ============================================================================


def ensure_user_data_dir():
    """Ensure the user_data directory exists."""
    if not USER_DATA_DIR.exists():
        USER_DATA_DIR.mkdir(exist_ok=True)


def load_pulse_history() -> list:
    """Load pulse history from JSON file."""
    if PULSE_HISTORY_FILE.exists():
        try:
            with open(PULSE_HISTORY_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []


def save_pulse_entry(entry_data: dict):
    """
    Save a daily attune (pulse) entry to the history file.

    Args:
        entry_data (dict): Dictionary containing the pulse data.
                           Should typically include: rest, climate, clarity, notes.
    """
    ensure_user_data_dir()

    # Add timestamp
    entry_data["timestamp"] = datetime.now().isoformat()

    # Load existing history
    history = load_pulse_history()

    # Append new entry
    history.append(entry_data)

    # Save back to file
    with open(PULSE_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def get_filtered_pulse_history(start_date: datetime, end_date: datetime) -> list:
    """
    Get pulse history entries within a specific date range.

    Args:
        start_date (datetime): Start of the range (inclusive).
        end_date (datetime): End of the range (inclusive).

    Returns:
        list: Filtered list of pulse entries.
    """
    history = load_pulse_history()
    filtered = []

    for entry in history:
        try:
            timestamp = datetime.fromisoformat(entry["timestamp"])
            # Normalize to date for comparison if needed,
            # but usually we want to compare the full datetime.
            if start_date <= timestamp <= end_date:
                filtered.append(entry)
        except (KeyError, ValueError):
            continue

    return filtered
