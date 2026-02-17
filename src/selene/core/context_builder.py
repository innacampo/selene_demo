"""
User Context Aggregator for MedGemma.

This module is responsible for synthesizing a 'User Snapshot' by aggregating data
from various local sources (Profiles, Pulse histories, Pattern logs).
This synthesized context is then injected into the LLM prompt to enable
personalized, clinically-aware reasoning without manual user input of their history.
"""

import json
import logging
import time
from datetime import datetime, timedelta

import streamlit as st

from selene import settings
from selene.constants import NEURO_SYMPTOM_MAP
from selene.storage.data_manager import load_pulse_history

logger = logging.getLogger(__name__)


# ============================================================================
# User Profile Context
# ============================================================================


def get_user_profile_hash() -> str:
    """
    Generate a hash of user profile and pulse data for cache invalidation.

    This function is used by med_logic.py to determine if the user context
    cache should be invalidated. It hashes the profile's last_updated time
    and the pulse history file's modification time.

    Returns:
        str: MD5 hash representing the current state of user data.
    """
    import hashlib

    logger.debug("get_user_profile_hash: ENTER")
    hash_parts = []

    # Include profile last_updated time
    profile_path = settings.PROFILE_PATH
    if profile_path.exists():
        try:
            with open(profile_path, encoding="utf-8") as f:
                profile = json.load(f)
                hash_parts.append(str(profile.get("last_updated", "")))
                hash_parts.append(str(profile.get("stage", "")))
                logger.debug(f"get_user_profile_hash: profile last_updated={profile.get('last_updated', '')}, stage={profile.get('stage', '')}")
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"get_user_profile_hash: Failed to read profile: {e}")

    # Include pulse history modification time
    pulse_path = settings.PULSE_HISTORY_FILE
    if pulse_path.exists():
        mtime = pulse_path.stat().st_mtime
        hash_parts.append(str(mtime))
        logger.debug(f"get_user_profile_hash: pulse_mtime={mtime}")

    if not hash_parts:
        logger.debug("get_user_profile_hash: no data found, returning empty hash")
        return hashlib.md5(b"").hexdigest()

    combined = "|".join(hash_parts)
    result = hashlib.md5(combined.encode()).hexdigest()
    logger.debug(f"get_user_profile_hash: hash={result}")
    return result


def get_profile_context() -> str:
    """
    Get user profile information from session state or file.
    Returns formatted text suitable for LLM system prompt.
    """
    logger.debug("get_profile_context: ENTER")
    # Try session state first
    profile = st.session_state.get("user_profile")
    source = "session_state"

    # Fallback to file
    if not profile:
        if settings.PROFILE_PATH.exists():
            source = "file"
            try:
                with open(settings.PROFILE_PATH, encoding="utf-8") as f:
                    profile = json.load(f)
            except Exception as e:
                logger.warning(f"get_profile_context: Failed to read profile file: {e}")

    if not profile:
        logger.debug("get_profile_context: No profile found")
        return ""

    logger.debug(f"get_profile_context: Using profile from {source}")

    # Load stage descriptions
    try:
        with open(settings.STAGES_METADATA_PATH, encoding="utf-8") as f:
            stages_data = json.load(f)
    except Exception as e:
        logger.warning(f"get_profile_context: Failed to load stages metadata: {e}")
        stages_data = {"stages": {}}

    stage_key = profile.get("stage", "")
    stage_info = stages_data.get("stages", {}).get(stage_key, {})

    lines = [
        "=== USER PROFILE ===",
        f"Stage: {profile.get('stage_title', 'Unknown')}",
        f"Description: {stage_info.get('description', 'N/A')}",
    ]

    # Add neuro symptoms if present
    neuro = profile.get("neuro_symptoms", [])
    if neuro:
        symptoms = [NEURO_SYMPTOM_MAP.get(s, s) for s in neuro]
        lines.append(f"Neuro Symptoms: {', '.join(symptoms)}")

    logger.debug(f"get_profile_context: EXIT with Stage={profile.get('stage_title', 'Unknown')}")
    return "\n".join(lines)


# ============================================================================
# Pulse History Context
# ============================================================================


@st.cache_data(ttl=60, show_spinner=False)
def get_recent_pulse_context(days: int = 7) -> str:
    """
    Generate a human-readable summary of the user's daily 'Pulse' entries (symptoms).

    Args:
        days: The look-back window in days.

    Returns:
        str: A formatted summary block including occurrence rates and the most recent entry.
    """
    logger.debug(f"get_recent_pulse_context: ENTER days={days}")
    history = load_pulse_history()
    if not history:
        logger.debug("get_recent_pulse_context: No pulse history")
        return ""

    # Filter entries within the look-back window
    cutoff = datetime.now() - timedelta(days=days)
    recent = []

    for entry in history:
        try:
            ts = datetime.fromisoformat(entry["timestamp"])
            if ts >= cutoff:
                recent.append(entry)
        except (KeyError, ValueError):
            continue

    logger.debug(f"get_recent_pulse_context: recent_count={len(recent)}")
    if not recent:
        return ""

    # Aggregate occurrence counts for key symptom categories
    sleep_issues = 0
    hot_flashes = 0
    brain_fog = 0
    for e in recent:
        if e.get("rest") in ("3 AM Awakening", "Fragmented"):
            sleep_issues += 1
        if e.get("climate") in ("Warm", "Flashing", "Heavy"):
            hot_flashes += 1
        if e.get("clarity") == "Brain Fog":
            brain_fog += 1

    logger.debug(f"get_recent_pulse_context: sleep_issues={sleep_issues}, hot_flashes={hot_flashes}, brain_fog={brain_fog}")

    lines = [
        f"=== RECENT SYMPTOMS (Last {days} Days, {len(recent)} Entries) ===",
        f"Sleep Disruptions: {sleep_issues}/{len(recent)} nights",
        f"Hot Flash Episodes: {hot_flashes}/{len(recent)} days",
        f"Brain Fog Days: {brain_fog}/{len(recent)} days",
    ]

    # Detailed breadcrumbs for the most recent check-in
    if recent:
        latest = recent[-1]
        try:
            latest_date = datetime.fromisoformat(latest["timestamp"]).strftime("%b %d")
        except (KeyError, ValueError):
            latest_date = "recent"

        lines.append(f"\nMost Recent Entry ({latest_date}):")
        lines.append(f"  Rest: {latest.get('rest', 'Not recorded')}")
        lines.append(f"  Climate: {latest.get('climate', 'Not recorded')}")
        lines.append(f"  Clarity: {latest.get('clarity', 'Not recorded')}")
        if latest.get("notes"):
            lines.append(f"  Notes: {latest['notes']}")

    logger.debug("get_recent_pulse_context: EXIT")
    return "\n".join(lines)


# ============================================================================
# Pulse Pattern Analysis (for deeper queries)
# ============================================================================


@st.cache_data(ttl=120, show_spinner=False)
def get_pulse_pattern_analysis(days: int = 30) -> dict:
    """
    Analyze pulse data for patterns over a longer period.
    Returns structured data rather than formatted text.

    Returns:
        dict with keys: sleep_pattern, climate_pattern, clarity_pattern, trends
    """
    logger.debug(f"get_pulse_pattern_analysis: ENTER days={days}")
    history = load_pulse_history()
    if not history:
        logger.debug("get_pulse_pattern_analysis: No pulse history")
        return {}

    # Filter to date range
    cutoff = datetime.now() - timedelta(days=days)
    recent = []

    for entry in history:
        try:
            ts = datetime.fromisoformat(entry["timestamp"])
            if ts >= cutoff:
                recent.append(entry)
        except (KeyError, ValueError):
            continue

    if not recent:
        logger.debug("get_pulse_pattern_analysis: After cutoff, no recent entries")
        return {}

    total = len(recent)
    logger.debug(f"get_pulse_pattern_analysis: recent_count={total}")

    # Sleep patterns
    sleep_counts = {
        "3 AM Awakening": sum(1 for e in recent if e.get("rest") == "3 AM Awakening"),
        "Fragmented": sum(1 for e in recent if e.get("rest") == "Fragmented"),
        "Restorative": sum(1 for e in recent if e.get("rest") == "Restorative"),
    }

    # Climate patterns
    climate_counts = {
        "Cool": sum(1 for e in recent if e.get("climate") == "Cool"),
        "Warm": sum(1 for e in recent if e.get("climate") == "Warm"),
        "Flashing": sum(1 for e in recent if e.get("climate") == "Flashing"),
        "Heavy": sum(1 for e in recent if e.get("climate") == "Heavy"),
    }

    # Clarity patterns
    clarity_counts = {
        "Brain Fog": sum(1 for e in recent if e.get("clarity") == "Brain Fog"),
        "Neutral": sum(1 for e in recent if e.get("clarity") == "Neutral"),
        "Focused": sum(1 for e in recent if e.get("clarity") == "Focused"),
    }

    # Identify trends
    trends = []

    if sleep_counts["3 AM Awakening"] + sleep_counts["Fragmented"] > total * 0.5:
        trends.append("Persistent sleep disruption pattern")

    if climate_counts["Flashing"] + climate_counts["Heavy"] > total * 0.3:
        trends.append("Frequent hot flash episodes")

    if clarity_counts["Brain Fog"] > total * 0.4:
        trends.append("Regular cognitive fog")

    logger.debug(f"get_pulse_pattern_analysis: EXIT trends={trends}")
    return {
        "period_days": days,
        "total_entries": total,
        "sleep_pattern": sleep_counts,
        "climate_pattern": climate_counts,
        "clarity_pattern": clarity_counts,
        "trends": trends,
    }


def format_pulse_analysis_for_llm(analysis: dict) -> str:
    """
    Convert pulse pattern analysis dict into LLM-friendly text.
    """
    if not analysis:
        return ""

    lines = [
        f"=== SYMPTOM PATTERNS (Last {analysis['period_days']} Days) ===",
        f"Total Tracked Days: {analysis['total_entries']}",
        "",
        "Sleep Pattern:",
    ]

    for state, count in analysis.get("sleep_pattern", {}).items():
        pct = (
            (count / analysis["total_entries"] * 100)
            if analysis["total_entries"] > 0
            else 0
        )
        lines.append(f"  {state}: {count} days ({pct:.0f}%)")

    lines.append("\nHot Flash Pattern:")
    for state, count in analysis.get("climate_pattern", {}).items():
        pct = (
            (count / analysis["total_entries"] * 100)
            if analysis["total_entries"] > 0
            else 0
        )
        lines.append(f"  {state}: {count} days ({pct:.0f}%)")

    lines.append("\nMental Clarity Pattern:")
    for state, count in analysis.get("clarity_pattern", {}).items():
        pct = (
            (count / analysis["total_entries"] * 100)
            if analysis["total_entries"] > 0
            else 0
        )
        lines.append(f"  {state}: {count} days ({pct:.0f}%)")

    if analysis.get("trends"):
        lines.append("\nNotable Trends:")
        for trend in analysis["trends"]:
            lines.append(f"  • {trend}")

    return "\n".join(lines)


# ============================================================================
# Unified Context Builder
# ============================================================================


def build_user_context(
    include_profile: bool = True,
    include_recent_pulse: bool = True,
    include_pulse_analysis: bool = False,
    recent_pulse_days: int = 7,
    analysis_days: int = 30,
) -> str:
    """
    Construct a unified context string from all available personalization sources.

    This is the main entry point for the RAG pipeline to get a 'Patient Snapshot'.

    Args:
        include_profile: Whether to include the user's Menopause Stage and neuro traits.
        include_recent_pulse: Whether to include recent daily symptom entries.
        include_pulse_analysis: Whether to include long-term pattern trends.
        recent_pulse_days: Look-back window for manual entry summaries.
        analysis_days: Look-back window for deeper pattern detection.

    Returns:
        str: A formatted multi-section block ready for injection into the LLM prompt.
    """
    logger.debug(f"build_user_context: ENTER include_profile={include_profile}, include_recent_pulse={include_recent_pulse}, include_pulse_analysis={include_pulse_analysis}, recent_pulse_days={recent_pulse_days}, analysis_days={analysis_days}")
    start_time = time.time()
    sections = []

    if include_profile:
        profile_ctx = get_profile_context()
        if profile_ctx:
            sections.append(profile_ctx)

    if include_recent_pulse:
        pulse_ctx = get_recent_pulse_context(days=recent_pulse_days)
        if pulse_ctx:
            sections.append(pulse_ctx)

    if include_pulse_analysis:
        analysis = get_pulse_pattern_analysis(days=analysis_days)
        analysis_ctx = format_pulse_analysis_for_llm(analysis)
        if analysis_ctx:
            sections.append(analysis_ctx)

    if not sections:
        logger.debug("build_user_context: No sections built, returning empty string")
        return ""

    res = "\n\n".join(sections)
    duration = time.time() - start_time
    logger.info(f"User Context Building: {duration:.3f}s")
    logger.debug(f"build_user_context: EXIT length={len(res)} chars")
    return res
