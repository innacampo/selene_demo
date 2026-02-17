"""
Local Persistence Layer with Enhanced Validation and Error Handling.
"""

import json
import logging
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import streamlit as st

from selene import settings

logger = logging.getLogger(__name__)

# Configuration
USER_DATA_DIR = settings.USER_DATA_DIR
PULSE_HISTORY_FILE = settings.PULSE_HISTORY_FILE
BACKUP_DIR = USER_DATA_DIR / "backups"
MAX_BACKUPS = 10

@dataclass
class PulseEntry:
    """Validated pulse entry structure."""
    rest: str | None = None
    climate: str | None = None
    clarity: str | None = None
    notes: str = ""
    timestamp: str = ""

    def validate(self) -> tuple[bool, str]:
        """Validate pulse entry data."""
        from selene.constants import VALID_CLARITY_VALUES, VALID_CLIMATE_VALUES, VALID_REST_VALUES

        # At least one symptom required
        if all(v is None for v in [self.rest, self.climate, self.clarity]):
            return False, "At least one symptom score required"

        # Validate against allowed label sets
        if self.rest is not None and self.rest not in VALID_REST_VALUES:
            return False, f"Invalid rest value: {self.rest}"
        if self.climate is not None and self.climate not in VALID_CLIMATE_VALUES:
            return False, f"Invalid climate value: {self.climate}"
        if self.clarity is not None and self.clarity not in VALID_CLARITY_VALUES:
            return False, f"Invalid clarity value: {self.clarity}"

        # Validate timestamp
        if self.timestamp:
            try:
                datetime.fromisoformat(self.timestamp)
            except ValueError:
                return False, "Invalid timestamp format"

        return True, ""


def ensure_user_data_dir():
    """Ensure data directories exist."""
    for directory in [USER_DATA_DIR, BACKUP_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def create_backup():
    """Create timestamped backup, maintain MAX_BACKUPS."""
    if not PULSE_HISTORY_FILE.exists():
        return

    ensure_user_data_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"pulse_history_{timestamp}.json"

    try:
        shutil.copy2(PULSE_HISTORY_FILE, backup_file)
        logger.info(f"Backup created: {backup_file}")

        # Cleanup old backups
        backups = sorted(BACKUP_DIR.glob("pulse_history_*.json"))
        for old_backup in backups[:-MAX_BACKUPS]:
            old_backup.unlink()

    except Exception as e:
        logger.error(f"Backup failed: {e}")


@st.cache_data(ttl=60, show_spinner=False)
def load_pulse_history() -> list[dict]:
    """Load and validate pulse history."""
    if not PULSE_HISTORY_FILE.exists():
        return []

    try:
        with open(PULSE_HISTORY_FILE, encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            logger.error("Invalid file format")
            return []

        return [e for e in data if isinstance(e, dict)]

    except json.JSONDecodeError:
        logger.error("JSON decode error, attempting restore")
        return restore_from_backup()
    except Exception as e:
        logger.error(f"Load error: {e}")
        return []


def restore_from_backup() -> list[dict]:
    """Restore from most recent valid backup."""
    if not BACKUP_DIR.exists():
        return []

    backups = sorted(BACKUP_DIR.glob("pulse_history_*.json"), reverse=True)

    for backup_file in backups:
        try:
            with open(backup_file, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                shutil.copy2(backup_file, PULSE_HISTORY_FILE)
                logger.info(f"Restored from {backup_file}")
                return data
        except Exception:
            continue

    return []


def save_pulse_entry(entry_data: dict) -> tuple[bool, str]:
    """
    Save pulse entry with atomic writes and validation.
    
    Returns:
        (success: bool, error_message: str)
    """
    ensure_user_data_dir()

    # Add timestamp
    if "timestamp" not in entry_data:
        entry_data["timestamp"] = datetime.now().isoformat()

    # Validate
    try:
        pulse_entry = PulseEntry(**entry_data)
        is_valid, error_msg = pulse_entry.validate()
        if not is_valid:
            return False, f"Invalid entry: {error_msg}"
    except TypeError as e:
        return False, f"Invalid structure: {e}"

    # Backup before modify
    create_backup()

    # Load, append, atomic save
    history = load_pulse_history()
    history.append(entry_data)

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='w',
            dir=USER_DATA_DIR,
            delete=False,
            suffix='.tmp',
            encoding='utf-8'
        ) as tmp:
            json.dump(history, tmp, indent=2, ensure_ascii=False)
            tmp_path = tmp.name

        shutil.move(tmp_path, PULSE_HISTORY_FILE)
        logger.info(f"Saved entry ({len(history)} total)")

        # Invalidate caches
        invalidate_all_caches()

        return True, ""

    except Exception as e:
        logger.error(f"Save failed: {e}")
        if tmp_path and Path(tmp_path).exists():
            Path(tmp_path).unlink()
        return False, f"Save failed: {e}"


def get_filtered_pulse_history(start_date: datetime, end_date: datetime) -> list[dict]:
    """Get entries in date range."""
    history = load_pulse_history()
    filtered = []

    for entry in history:
        try:
            timestamp = datetime.fromisoformat(entry["timestamp"])
            if start_date <= timestamp <= end_date:
                filtered.append(entry)
        except (KeyError, ValueError):
            continue

    logger.debug(f"Filtered {len(filtered)}/{len(history)} entries")
    return filtered


def invalidate_all_caches():
    """Invalidate all dependent caches."""
    load_pulse_history.clear()

    try:
        from selene.core.med_logic import invalidate_user_context_cache
        invalidate_user_context_cache()
    except ImportError:
        pass

    try:
        from selene.core.context_builder import get_pulse_pattern_analysis, get_recent_pulse_context
        get_recent_pulse_context.clear()
        get_pulse_pattern_analysis.clear()
    except ImportError:
        pass

    try:
        from selene.core.context_builder_multi_agent import load_pulse_history as ma_load
        ma_load.clear()
    except ImportError:
        pass


def verify_data_integrity() -> tuple[bool, list[str]]:
    """Verify pulse history integrity."""
    issues = []

    if not PULSE_HISTORY_FILE.exists():
        return True, []

    try:
        history = load_pulse_history()

        # Check duplicates
        timestamps = [e.get("timestamp") for e in history if "timestamp" in e]
        if len(timestamps) != len(set(timestamps)):
            issues.append("Duplicate timestamps")

        # Check chronological order
        for i in range(len(history) - 1):
            try:
                ts1 = datetime.fromisoformat(history[i]["timestamp"])
                ts2 = datetime.fromisoformat(history[i+1]["timestamp"])
                if ts1 > ts2:
                    issues.append(f"Out of order at index {i}")
                    break
            except:
                pass

        # Validate entries
        invalid = sum(1 for e in history
                     if not PulseEntry(**e).validate()[0])
        if invalid > 0:
            issues.append(f"{invalid} invalid entries")

        return len(issues) == 0, issues

    except Exception as e:
        return False, [f"Check failed: {e}"]
