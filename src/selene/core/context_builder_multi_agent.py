"""
Context Builder for Multi-Agent Insights Pipeline.

Aggregates all user data (profile, pulse, notes, chat) into a unified
context structure for downstream analysis.
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta

import streamlit as st

from selene import settings
from selene.storage.data_manager import get_filtered_pulse_history, load_pulse_history

logger = logging.getLogger(__name__)

# Configuration
USER_PROFILE_FILE = settings.PROFILE_PATH
NOTES_FILE = settings.USER_DATA_DIR / "notes.json"


@dataclass
class ContextMetadata:
    """Metadata about the aggregated context."""

    pulse_entry_count: int
    notes_count: int
    chat_message_count: int
    date_range_start: str
    date_range_end: str
    context_generated_at: str
    has_profile: bool
    data_completeness_score: float  # 0-1 score


def load_user_profile() -> dict:
    """
    Load user profile with validation.

    Returns:
        Dict containing profile data or empty dict with defaults
    """
    if not USER_PROFILE_FILE.exists():
        logger.warning("Profile file not found, using defaults")
        return {"stage_title": "Unknown", "neuro_symptoms": [], "profile_complete": False}

    try:
        with open(USER_PROFILE_FILE, encoding="utf-8") as f:
            profile = json.load(f)

        # Validate required fields
        profile.setdefault("stage_title", "Unknown")
        profile.setdefault("neuro_symptoms", [])
        profile["profile_complete"] = True

        logger.debug(f"Loaded profile: stage={profile['stage_title']}")
        return profile

    except json.JSONDecodeError as e:
        logger.error(f"Profile JSON error: {e}")
        return {"stage_title": "Unknown", "neuro_symptoms": [], "profile_complete": False}
    except Exception as e:
        logger.error(f"Profile load error: {e}")
        return {"stage_title": "Unknown", "neuro_symptoms": [], "profile_complete": False}


def load_notes(
    start_date: datetime | None = None, end_date: datetime | None = None
) -> tuple[str, int]:
    """
    Load and aggregate notes within date range.

    Args:
        start_date: Filter start (None = no filter)
        end_date: Filter end (None = no filter)

    Returns:
        Tuple[str, int]: (concatenated_notes, count)
    """

    def _parse_iso(ts: str) -> datetime | None:
        if not ts:
            return None
        try:
            return datetime.fromisoformat(ts)
        except ValueError:
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                return None

    def _in_range(ts: str) -> bool:
        parsed = _parse_iso(ts)
        if parsed is None:
            return not (start_date or end_date)
        if start_date and parsed < start_date:
            return False
        if end_date and parsed > end_date:
            return False
        return True

    collected: list[tuple[datetime, str, str]] = []
    seen: set[tuple[str, str]] = set()

    def _add_note(timestamp: str, note_text: str):
        text = (note_text or "").strip()
        if not text:
            return
        ts = (timestamp or "").strip()
        if (start_date or end_date) and not _in_range(ts):
            return
        key = (ts, text)
        if key in seen:
            return
        seen.add(key)
        collected.append((_parse_iso(ts) or datetime.min, ts, text))

    try:
        # Source 1 (legacy): notes.json
        if NOTES_FILE.exists():
            try:
                with open(NOTES_FILE, encoding="utf-8") as f:
                    notes_data = json.load(f)

                if isinstance(notes_data, list):
                    for note in notes_data:
                        if not isinstance(note, dict):
                            continue
                        _add_note(
                            note.get("timestamp", ""), note.get("content", note.get("text", ""))
                        )
            except json.JSONDecodeError:
                logger.error("Notes JSON decode error")
            except Exception as e:
                logger.error(f"Legacy notes load error: {e}")

        # Source 2 (primary): pulse history notes
        pulse_entries = (
            get_filtered_pulse_history(start_date, end_date)
            if (start_date and end_date)
            else load_pulse_history()
        )
        for entry in pulse_entries:
            if not isinstance(entry, dict):
                continue
            _add_note(entry.get("timestamp", ""), entry.get("notes", ""))

        if not collected:
            return "No notes in this period.", 0

        collected.sort(key=lambda item: item[0])
        formatted_notes = [f"[{timestamp}] {text}" for _, timestamp, text in collected]
        aggregated = "\n\n".join(formatted_notes)
        logger.debug(f"Loaded {len(formatted_notes)} notes")
        return aggregated, len(formatted_notes)

    except Exception as e:
        logger.error(f"Notes load error: {e}")
        return "Error loading notes.", 0


def load_chat_context(
    start_date: datetime | None = None, end_date: datetime | None = None
) -> tuple[str, int]:
    """
    Load user chat messages (not assistant responses) within date range.

    Reads from ChromaDB via the chat_db module (chat history is stored
    there, not in a flat JSON file).

    Args:
        start_date: Filter start
        end_date: Filter end

    Returns:
        Tuple[str, int]: (concatenated_messages, count)
    """
    try:
        from selene.storage.chat_db import _get_chat_client

        collection, error = _get_chat_client()
        if collection is None or collection.count() == 0:
            return "No chat history available.", 0

        results = collection.get(
            where={"role": "user"},
            include=["documents", "metadatas"],
        )

        if not results["ids"]:
            return "No chat history available.", 0

        user_messages = []
        for doc, meta in zip(results["documents"], results["metadatas"], strict=False):
            if start_date or end_date:
                try:
                    msg_date = datetime.fromisoformat(meta.get("timestamp", ""))
                    if start_date and msg_date < start_date:
                        continue
                    if end_date and msg_date > end_date:
                        continue
                except (ValueError, TypeError):
                    continue

            if doc:
                timestamp = meta.get("timestamp", "")
                user_messages.append(f"[{timestamp}] {doc}")

        if not user_messages:
            return "No user messages in this period.", 0

        aggregated = "\n\n".join(user_messages)
        logger.debug(f"Loaded {len(user_messages)} user messages from chat DB")
        return aggregated, len(user_messages)

    except Exception as e:
        logger.error(f"Chat context load error: {e}")
        return "No chat history available.", 0


def calculate_completeness_score(context: dict) -> float:
    """
    Calculate data completeness score (0-1).

    Factors:
    - Profile exists (0.2)
    - Has pulse data (0.4)
    - Has notes (0.2)
    - Has chat history (0.2)
    """
    score = 0.0

    if context.get("profile", {}).get("profile_complete"):
        score += 0.2

    if len(context.get("pulse_entries", [])) > 0:
        score += 0.4

    if context["metadata"]["notes_count"] > 0:
        score += 0.2

    if context["metadata"]["chat_message_count"] > 0:
        score += 0.2

    return round(score, 2)


@st.cache_data(ttl=300, show_spinner=False)
def build_complete_context(
    start_date: datetime | None = None, end_date: datetime | None = None, default_days: int = 30
) -> dict:
    """
    Build unified context from all data sources.

    Args:
        start_date: Analysis start date (None = default_days ago)
        end_date: Analysis end date (None = now)
        default_days: Default lookback if dates not specified

    Returns:
        Dict with keys:
            - profile: User profile dict
            - pulse_entries: List of pulse data
            - all_notes: Aggregated notes text
            - chat_context: Aggregated user messages
            - metadata: ContextMetadata
    """
    logger.info("Building complete context")

    # Determine date range
    if end_date is None:
        end_date = datetime.now()

    if start_date is None:
        start_date = end_date - timedelta(days=default_days)

    logger.debug(f"Date range: {start_date.date()} to {end_date.date()}")

    # Load all data sources
    profile = load_user_profile()
    pulse_entries = get_filtered_pulse_history(start_date, end_date)
    all_notes, notes_count = load_notes(start_date, end_date)
    chat_context, chat_count = load_chat_context(start_date, end_date)

    # Build metadata
    metadata = ContextMetadata(
        pulse_entry_count=len(pulse_entries),
        notes_count=notes_count,
        chat_message_count=chat_count,
        date_range_start=start_date.isoformat(),
        date_range_end=end_date.isoformat(),
        context_generated_at=datetime.now().isoformat(),
        has_profile=profile.get("profile_complete", False),
        data_completeness_score=0.0,  # Will calculate below
    )

    # Assemble context
    context = {
        "profile": profile,
        "pulse_entries": pulse_entries,
        "all_notes": all_notes,
        "chat_context": chat_context,
        "metadata": asdict(metadata),
    }

    # Calculate and update completeness
    context["metadata"]["data_completeness_score"] = calculate_completeness_score(context)

    logger.info(
        f"Context built: {metadata.pulse_entry_count} pulse entries, "
        f"{metadata.notes_count} notes, {metadata.chat_message_count} messages, "
        f"completeness: {context['metadata']['data_completeness_score']}"
    )

    return context


def get_context_summary(context: dict) -> str:
    """
    Generate human-readable summary of context.

    Args:
        context: Context dict from build_complete_context()

    Returns:
        Formatted summary string
    """
    meta = context["metadata"]

    date_start = datetime.fromisoformat(meta["date_range_start"]).strftime("%Y-%m-%d")
    date_end = datetime.fromisoformat(meta["date_range_end"]).strftime("%Y-%m-%d")

    summary = f"""
Context Summary
===============
Date Range: {date_start} to {date_end}
Profile: {"Complete" if meta["has_profile"] else "Incomplete"}
Pulse Entries: {meta["pulse_entry_count"]}
Notes: {meta["notes_count"]}
Chat Messages: {meta["chat_message_count"]}
Data Completeness: {meta["data_completeness_score"] * 100:.0f}%
Generated: {datetime.fromisoformat(meta["context_generated_at"]).strftime("%Y-%m-%d %H:%M:%S")}
"""

    return summary.strip()
