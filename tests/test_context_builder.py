"""
Unit tests for context_builder.py and context_builder_multi_agent.py

Tests cover: profile hash generation, pulse context aggregation, pattern
analysis, build_user_context assembly, multi-agent context loading, and
completeness scoring.

Heavy use of mocking to avoid Streamlit/file I/O side-effects.
"""

import hashlib
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

# Streamlit must be patched before importing modules that reference st.*
_st_mock = MagicMock()
sys.modules.setdefault("streamlit", _st_mock)

# Patch st.cache_data / st.cache_resource so decorated functions run normally
def _passthrough_decorator(*args, **kwargs):
    """Return function unchanged – removes caching."""
    if args and callable(args[0]):
        return args[0]
    def wrapper(fn):
        return fn
    return wrapper

_st_mock.cache_data = _passthrough_decorator
_st_mock.cache_resource = _passthrough_decorator
_st_mock.session_state = {}

from selene.core import context_builder as cb
from selene.core import context_builder_multi_agent as cb_multi

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pulse_entry(rest="Restorative", climate="Cool", clarity="Focused",
                 notes="", days_ago=0):
    ts = (datetime.now() - timedelta(days=days_ago)).isoformat()
    return {"rest": rest, "climate": climate, "clarity": clarity,
            "notes": notes, "timestamp": ts}


# ===================================================================
# context_builder.get_user_profile_hash
# ===================================================================


class TestGetUserProfileHash:
    def test_empty_when_no_files(self, tmp_path):
        with patch.object(cb.settings, "PROFILE_PATH", tmp_path / "nope.json"), \
             patch.object(cb.settings, "PULSE_HISTORY_FILE", tmp_path / "nope2.json"):
            result = cb.get_user_profile_hash()
            assert result == hashlib.md5(b"").hexdigest()

    def test_includes_profile_fields(self, tmp_path):
        profile_path = tmp_path / "profile.json"
        profile_path.write_text(json.dumps({
            "last_updated": "2026-02-17",
            "stage": "peri",
        }))
        pulse_path = tmp_path / "pulse.json"
        pulse_path.write_text("[]")

        with patch.object(cb.settings, "PROFILE_PATH", profile_path), \
             patch.object(cb.settings, "PULSE_HISTORY_FILE", pulse_path):
            h1 = cb.get_user_profile_hash()
            assert isinstance(h1, str) and len(h1) == 32

    def test_hash_changes_when_profile_updates(self, tmp_path):
        profile_path = tmp_path / "profile.json"
        pulse_path = tmp_path / "pulse.json"
        pulse_path.write_text("[]")

        profile_path.write_text(json.dumps({"last_updated": "t1", "stage": "peri"}))
        with patch.object(cb.settings, "PROFILE_PATH", profile_path), \
             patch.object(cb.settings, "PULSE_HISTORY_FILE", pulse_path):
            h1 = cb.get_user_profile_hash()

        profile_path.write_text(json.dumps({"last_updated": "t2", "stage": "post"}))
        with patch.object(cb.settings, "PROFILE_PATH", profile_path), \
             patch.object(cb.settings, "PULSE_HISTORY_FILE", pulse_path):
            h2 = cb.get_user_profile_hash()

        assert h1 != h2


# ===================================================================
# context_builder.get_profile_context
# ===================================================================


class TestGetProfileContext:
    def test_returns_empty_when_no_profile(self):
        _st_mock.session_state = {}
        with patch.object(cb.settings, "PROFILE_PATH", Path("/fake/nope.json")):
            result = cb.get_profile_context()
            assert result == ""

    def test_formats_profile_from_session_state(self, tmp_path):
        stages_path = tmp_path / "stages.json"
        stages_path.write_text(json.dumps({
            "stages": {"peri": {"description": "Perimenopause"}}
        }))

        _st_mock.session_state = {
            "user_profile": {
                "stage": "peri",
                "stage_title": "Perimenopause",
                "neuro_symptoms": ["3am_wakeup"],
            }
        }

        with patch.object(cb.settings, "STAGES_METADATA_PATH", stages_path):
            result = cb.get_profile_context()
            assert "USER PROFILE" in result
            assert "Perimenopause" in result
            assert "3 AM Wakeup" in result


# ===================================================================
# context_builder.get_recent_pulse_context
# ===================================================================


class TestGetRecentPulseContext:
    def test_empty_when_no_history(self):
        with patch.object(cb, "load_pulse_history", return_value=[]):
            assert cb.get_recent_pulse_context(days=7) == ""

    def test_counts_sleep_issues(self):
        entries = [
            _pulse_entry(rest="3 AM Awakening", days_ago=1),
            _pulse_entry(rest="Fragmented", days_ago=2),
            _pulse_entry(rest="Restorative", days_ago=3),
        ]
        with patch.object(cb, "load_pulse_history", return_value=entries):
            text = cb.get_recent_pulse_context(days=7)
            assert "Sleep Disruptions: 2/3" in text

    def test_counts_hot_flashes(self):
        entries = [
            _pulse_entry(climate="Flashing", days_ago=0),
            _pulse_entry(climate="Warm", days_ago=1),
            _pulse_entry(climate="Cool", days_ago=2),
        ]
        with patch.object(cb, "load_pulse_history", return_value=entries):
            text = cb.get_recent_pulse_context(days=7)
            assert "Hot Flash Episodes: 2/3" in text

    def test_respects_day_window(self):
        entries = [
            _pulse_entry(rest="Fragmented", days_ago=0),
            _pulse_entry(rest="Fragmented", days_ago=20),  # outside window
        ]
        with patch.object(cb, "load_pulse_history", return_value=entries):
            text = cb.get_recent_pulse_context(days=7)
            assert "1 Entries" in text


# ===================================================================
# context_builder.get_pulse_pattern_analysis
# ===================================================================


class TestPulsePatternAnalysis:
    def test_empty_returns_empty_dict(self):
        with patch.object(cb, "load_pulse_history", return_value=[]):
            assert cb.get_pulse_pattern_analysis(days=30) == {}

    def test_sleep_disruption_trend(self):
        entries = [
            _pulse_entry(rest="3 AM Awakening", days_ago=i) for i in range(10)
        ]
        with patch.object(cb, "load_pulse_history", return_value=entries):
            analysis = cb.get_pulse_pattern_analysis(days=30)
            assert "Persistent sleep disruption pattern" in analysis["trends"]
            assert analysis["sleep_pattern"]["3 AM Awakening"] == 10

    def test_format_pulse_analysis_for_llm(self):
        analysis = {
            "period_days": 30,
            "total_entries": 5,
            "sleep_pattern": {"3 AM Awakening": 3, "Fragmented": 1, "Restorative": 1},
            "climate_pattern": {"Cool": 5, "Warm": 0, "Flashing": 0, "Heavy": 0},
            "clarity_pattern": {"Brain Fog": 0, "Neutral": 3, "Focused": 2},
            "trends": [],
        }
        text = cb.format_pulse_analysis_for_llm(analysis)
        assert "SYMPTOM PATTERNS" in text
        assert "3 AM Awakening: 3 days" in text


# ===================================================================
# context_builder.build_user_context
# ===================================================================


class TestBuildUserContext:
    def test_empty_when_all_disabled(self):
        result = cb.build_user_context(
            include_profile=False,
            include_recent_pulse=False,
            include_pulse_analysis=False,
        )
        assert result == ""

    def test_combines_sections(self):
        with patch.object(cb, "get_profile_context", return_value="PROFILE_BLOCK"), \
             patch.object(cb, "get_recent_pulse_context", return_value="PULSE_BLOCK"):
            result = cb.build_user_context(
                include_profile=True,
                include_recent_pulse=True,
                include_pulse_analysis=False,
            )
            assert "PROFILE_BLOCK" in result
            assert "PULSE_BLOCK" in result


# ===================================================================
# context_builder_multi_agent: load_user_profile
# ===================================================================


class TestMultiAgentLoadProfile:
    def test_defaults_when_missing(self, tmp_path):
        with patch.object(cb_multi, "USER_PROFILE_FILE", tmp_path / "nope.json"):
            profile = cb_multi.load_user_profile()
            assert profile["stage_title"] == "Unknown"
            assert profile["profile_complete"] is False

    def test_loads_existing(self, tmp_path):
        pf = tmp_path / "profile.json"
        pf.write_text(json.dumps({"stage_title": "Perimenopause", "neuro_symptoms": ["3am_wakeup"]}))
        with patch.object(cb_multi, "USER_PROFILE_FILE", pf):
            profile = cb_multi.load_user_profile()
            assert profile["stage_title"] == "Perimenopause"
            assert profile["profile_complete"] is True

    def test_corrupt_json_returns_defaults(self, tmp_path):
        pf = tmp_path / "profile.json"
        pf.write_text("{{{bad json")
        with patch.object(cb_multi, "USER_PROFILE_FILE", pf):
            profile = cb_multi.load_user_profile()
            assert profile["stage_title"] == "Unknown"


# ===================================================================
# context_builder_multi_agent: load_notes
# ===================================================================


class TestMultiAgentLoadNotes:
    def test_missing_file(self, tmp_path):
        with patch.object(cb_multi, "NOTES_FILE", tmp_path / "nope.json"):
            text, count = cb_multi.load_notes()
            assert count == 0

    def test_valid_notes(self, tmp_path):
        nf = tmp_path / "notes.json"
        nf.write_text(json.dumps([
            {"content": "Feeling tired", "timestamp": "2026-02-10T10:00:00"},
            {"content": "Better today", "timestamp": "2026-02-12T10:00:00"},
        ]))
        with patch.object(cb_multi, "NOTES_FILE", nf):
            text, count = cb_multi.load_notes()
            assert count == 2
            assert "Feeling tired" in text

    def test_date_filter(self, tmp_path):
        nf = tmp_path / "notes.json"
        nf.write_text(json.dumps([
            {"content": "old note", "timestamp": "2025-01-01T10:00:00"},
            {"content": "recent note", "timestamp": "2026-02-15T10:00:00"},
        ]))
        start = datetime(2026, 2, 1)
        with patch.object(cb_multi, "NOTES_FILE", nf):
            text, count = cb_multi.load_notes(start_date=start)
            assert count == 1
            assert "recent note" in text


# ===================================================================
# context_builder_multi_agent: calculate_completeness_score
# ===================================================================


class TestCompletenessScore:
    def test_zero_when_empty(self):
        ctx = {
            "profile": {"profile_complete": False},
            "pulse_entries": [],
            "metadata": {"notes_count": 0, "chat_message_count": 0},
        }
        assert cb_multi.calculate_completeness_score(ctx) == 0.0

    def test_full_score(self):
        ctx = {
            "profile": {"profile_complete": True},
            "pulse_entries": [{"rest": "Restorative"}],
            "metadata": {"notes_count": 3, "chat_message_count": 2},
        }
        assert cb_multi.calculate_completeness_score(ctx) == 1.0

    def test_partial_score(self):
        ctx = {
            "profile": {"profile_complete": True},
            "pulse_entries": [],
            "metadata": {"notes_count": 0, "chat_message_count": 5},
        }
        # profile(0.2) + chat(0.2) = 0.4
        assert cb_multi.calculate_completeness_score(ctx) == 0.4


# ===================================================================
# context_builder_multi_agent: get_context_summary
# ===================================================================


class TestContextSummary:
    def test_summary_format(self):
        ctx = {
            "metadata": {
                "date_range_start": "2026-02-01T00:00:00",
                "date_range_end": "2026-02-17T00:00:00",
                "has_profile": True,
                "pulse_entry_count": 10,
                "notes_count": 3,
                "chat_message_count": 5,
                "data_completeness_score": 0.8,
                "context_generated_at": "2026-02-17T12:00:00",
            }
        }
        summary = cb_multi.get_context_summary(ctx)
        assert "2026-02-01" in summary
        assert "Pulse Entries: 10" in summary
        assert "80%" in summary
