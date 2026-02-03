"""
Context Builder for MedGemma
Aggregates all available user data sources into coherent context for the LLM.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
import streamlit as st


# ============================================================================
# User Profile Context
# ============================================================================


def get_profile_context() -> str:
    """
    Get user profile information from session state or file.
    Returns formatted text suitable for LLM system prompt.
    """
    # Try session state first
    profile = st.session_state.get("user_profile")
    
    # Fallback to file
    if not profile:
        profile_path = Path("user_data/user_profile.json")
        if profile_path.exists():
            with open(profile_path, "r") as f:
                profile = json.load(f)
    
    if not profile:
        return ""
    
    # Load stage descriptions
    try:
        with open("metadata/stages.json", "r") as f:
            stages_data = json.load(f)
    except Exception:
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
        neuro_map = {
            "3am_wakeup": "The 3 AM Wakeup (nighttime waking with anxiety)",
            "word_search": "The Word Search (difficulty finding words)",
            "short_fuse": "The Short Fuse (chemical irritability)",
        }
        symptoms = [neuro_map.get(s, s) for s in neuro]
        lines.append(f"Neuro Symptoms: {', '.join(symptoms)}")
    
    return "\n".join(lines)


# ============================================================================
# Pulse History Context
# ============================================================================


def get_recent_pulse_context(days: int = 7) -> str:
    """
    Get recent pulse (daily attune) entries as context.
    
    Args:
        days: How many days back to retrieve (default 7)
    
    Returns:
        Formatted text summary of recent patterns
    """
    pulse_path = Path("user_data/pulse_history.json")
    if not pulse_path.exists():
        return ""
    
    try:
        with open(pulse_path, "r") as f:
            history = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return ""
    
    if not history:
        return ""
    
    # Filter to recent entries
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
        return ""
    
    # Analyze patterns
    sleep_issues = sum(1 for e in recent if e.get("rest") in ["3 AM Awakening", "Fragmented"])
    hot_flashes = sum(1 for e in recent if e.get("climate") in ["Warm", "Flashing", "Heavy"])
    brain_fog = sum(1 for e in recent if e.get("clarity") == "Brain Fog")
    
    lines = [
        f"=== RECENT SYMPTOMS (Last {days} Days, {len(recent)} Entries) ===",
        f"Sleep Disruptions: {sleep_issues}/{len(recent)} nights",
        f"Hot Flash Episodes: {hot_flashes}/{len(recent)} days",
        f"Brain Fog Days: {brain_fog}/{len(recent)} days",
    ]
    
    # Add most recent entry details
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
    
    return "\n".join(lines)


# ============================================================================
# Pulse Pattern Analysis (for deeper queries)
# ============================================================================


def get_pulse_pattern_analysis(days: int = 30) -> dict:
    """
    Analyze pulse data for patterns over a longer period.
    Returns structured data rather than formatted text.
    
    Returns:
        dict with keys: sleep_pattern, climate_pattern, clarity_pattern, trends
    """
    pulse_path = Path("user_data/pulse_history.json")
    if not pulse_path.exists():
        return {}
    
    try:
        with open(pulse_path, "r") as f:
            history = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}
    
    if not history:
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
        return {}
    
    total = len(recent)
    
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
        pct = (count / analysis["total_entries"] * 100) if analysis["total_entries"] > 0 else 0
        lines.append(f"  {state}: {count} days ({pct:.0f}%)")
    
    lines.append("\nHot Flash Pattern:")
    for state, count in analysis.get("climate_pattern", {}).items():
        pct = (count / analysis["total_entries"] * 100) if analysis["total_entries"] > 0 else 0
        lines.append(f"  {state}: {count} days ({pct:.0f}%)")
    
    lines.append("\nMental Clarity Pattern:")
    for state, count in analysis.get("clarity_pattern", {}).items():
        pct = (count / analysis["total_entries"] * 100) if analysis["total_entries"] > 0 else 0
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
    Build comprehensive user context from all available data sources.
    
    Args:
        include_profile: Include user profile (stage, neuro symptoms)
        include_recent_pulse: Include recent daily attune entries
        include_pulse_analysis: Include deeper pattern analysis
        recent_pulse_days: How many days of recent pulse to include
        analysis_days: How many days for pattern analysis
    
    Returns:
        Formatted multi-line string ready to inject into LLM prompt
    """
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
        return ""
    
    return "\n\n".join(sections)
