"""
Unit tests for deterministic_analysis.py

Covers: DeterministicAnalyzer – symptom mapping, statistics, pattern detection,
risk assessment, and formatting helpers.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np
import pytest

from selene.core.deterministic_analysis import (
    DeterministicAnalyzer,
    SymptomStatistics,
    PatternAnalysis,
    format_statistics_summary,
    format_pattern_summary,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def analyzer():
    return DeterministicAnalyzer()


def _make_entries(
    rest_vals, climate_vals=None, clarity_vals=None, days_back=None, notes=None
):
    """Build a list of pulse entry dicts.

    If *days_back* is None, timestamps start today and go backwards one day
    per entry.
    """
    n = len(rest_vals)
    climate_vals = climate_vals or ["Cool"] * n
    clarity_vals = clarity_vals or ["Focused"] * n
    notes = notes or [""] * n
    if days_back is None:
        days_back = list(range(n - 1, -1, -1))

    entries = []
    for i in range(n):
        ts = (datetime.now() - timedelta(days=days_back[i])).isoformat()
        entries.append(
            {
                "rest": rest_vals[i],
                "climate": climate_vals[i],
                "clarity": clarity_vals[i],
                "notes": notes[i],
                "timestamp": ts,
            }
        )
    return entries


# ===================================================================
# _map_symptom_to_score
# ===================================================================


class TestSymptomMapping:
    def test_known_label_maps_correctly(self, analyzer):
        assert analyzer._map_symptom_to_score("Restorative") == 0.0
        assert analyzer._map_symptom_to_score("Fragmented") == 5.0
        assert analyzer._map_symptom_to_score("3 AM Awakening") == 9.0
        assert analyzer._map_symptom_to_score("Cool") == 0.0
        assert analyzer._map_symptom_to_score("Heavy") == 10.0
        assert analyzer._map_symptom_to_score("Brain Fog") == 9.0

    def test_numeric_passthrough(self, analyzer):
        assert analyzer._map_symptom_to_score(7) == 7.0
        assert analyzer._map_symptom_to_score(3.5) == 3.5

    def test_numeric_string(self, analyzer):
        assert analyzer._map_symptom_to_score("8") == 8.0
        assert analyzer._map_symptom_to_score("2.5") == 2.5

    def test_none_returns_none(self, analyzer):
        assert analyzer._map_symptom_to_score(None) is None

    def test_unknown_string_returns_none(self, analyzer):
        assert analyzer._map_symptom_to_score("garbage") is None

    def test_unsupported_type_returns_none(self, analyzer):
        assert analyzer._map_symptom_to_score([1, 2]) is None


# ===================================================================
# analyze_symptom_statistics
# ===================================================================


class TestSymptomStatistics:
    def test_returns_none_when_insufficient_data(self, analyzer):
        entries = _make_entries(["Restorative"] * 3)
        result = analyzer.analyze_symptom_statistics(entries, "rest")
        assert result is None

    def test_basic_statistics_stable_rest(self, analyzer):
        # All "Restorative" -> score 0.0 → stable trend
        entries = _make_entries(["Restorative"] * 10)
        stats = analyzer.analyze_symptom_statistics(entries, "rest")
        assert stats is not None
        assert stats.mean == 0.0
        assert stats.std_dev == 0.0
        assert stats.trend == "stable"

    def test_worsening_trend_detected(self, analyzer):
        # Slope upwards (low → high scores = worsening)
        rest_vals = ["Restorative"] * 5 + ["3 AM Awakening"] * 5
        entries = _make_entries(rest_vals)
        stats = analyzer.analyze_symptom_statistics(entries, "rest")
        assert stats is not None
        assert stats.trend == "worsening"
        assert stats.trend_slope > 0

    def test_improving_trend_detected(self, analyzer):
        rest_vals = ["3 AM Awakening"] * 5 + ["Restorative"] * 5
        entries = _make_entries(rest_vals)
        stats = analyzer.analyze_symptom_statistics(entries, "rest")
        assert stats is not None
        assert stats.trend == "improving"
        assert stats.trend_slope < 0

    def test_percent_change_calculation(self, analyzer):
        # First half: Fragmented (5), second half: 3 AM Awakening (9)
        rest_vals = ["Fragmented"] * 5 + ["3 AM Awakening"] * 5
        entries = _make_entries(rest_vals)
        stats = analyzer.analyze_symptom_statistics(entries, "rest")
        assert stats is not None
        assert stats.previous_avg == 5.0
        assert stats.recent_avg == 9.0
        assert stats.percent_change == 80.0

    def test_missing_symptom_key_returns_none(self, analyzer):
        entries = [{"climate": "Cool", "timestamp": datetime.now().isoformat()}] * 10
        result = analyzer.analyze_symptom_statistics(entries, "rest")
        assert result is None


# ===================================================================
# detect_patterns
# ===================================================================


class TestPatternDetection:
    def test_insufficient_data_returns_empty(self, analyzer):
        entries = _make_entries(["Restorative"] * 3)
        patterns = analyzer.detect_patterns(entries)
        assert patterns.trend_direction == "unknown"
        assert patterns.correlations == {}

    def test_stable_data_no_cycles(self, analyzer):
        entries = _make_entries(["Restorative"] * 20)
        patterns = analyzer.detect_patterns(entries)
        assert not patterns.has_weekly_cycle
        assert not patterns.has_monthly_cycle
        assert patterns.trend_direction == "stable"

    def test_correlations_computed(self, analyzer):
        # Correlated symptoms: high rest ↔ high climate
        rest = ["3 AM Awakening"] * 5 + ["Restorative"] * 5
        climate = ["Heavy"] * 5 + ["Cool"] * 5
        entries = _make_entries(rest, climate_vals=climate)
        patterns = analyzer.detect_patterns(entries)
        assert "rest-climate" in patterns.correlations
        # Expect a strong positive correlation
        assert patterns.correlations["rest-climate"] > 0.5

    def test_pattern_analysis_fields(self, analyzer):
        entries = _make_entries(["Fragmented"] * 10)
        p = analyzer.detect_patterns(entries)
        assert isinstance(p, PatternAnalysis)
        assert isinstance(p.outlier_dates, list)
        assert isinstance(p.change_points, list)


# ===================================================================
# _detect_cycle
# ===================================================================


class TestCycleDetection:
    def test_no_cycle_with_constant_data(self, analyzer):
        values = np.zeros(30)
        has_cycle, conf = analyzer._detect_cycle(values, period=7)
        assert not has_cycle

    def test_insufficient_length(self, analyzer):
        values = np.array([1, 2, 3])
        has_cycle, conf = analyzer._detect_cycle(values, period=7)
        assert not has_cycle
        assert conf == 0.0

    def test_strong_weekly_cycle_detected(self, analyzer):
        # Construct a clear 7-day sinusoidal signal
        x = np.arange(56)  # 8 weeks
        values = 5 + 4 * np.sin(2 * np.pi * x / 7)
        has_cycle, conf = analyzer._detect_cycle(values, period=7)
        assert has_cycle
        assert conf > 0.3


# ===================================================================
# assess_risk_level
# ===================================================================


class TestRiskAssessment:
    def test_insufficient_data(self, analyzer):
        entries = _make_entries(["Restorative"] * 3)
        result = analyzer.assess_risk_level(entries)
        assert result["level"] == "insufficient_data"
        assert result["score"] == 0

    def test_low_risk(self, analyzer):
        entries = _make_entries(["Restorative"] * 10)
        result = analyzer.assess_risk_level(entries)
        assert result["level"] == "low"
        assert result["score"] == 0
        assert result["flags"] == []

    def test_persistent_poor_sleep_flag(self, analyzer):
        # All "3 AM Awakening" (score 9 > 7 threshold)
        entries = _make_entries(["3 AM Awakening"] * 10)
        result = analyzer.assess_risk_level(entries)
        assert "persistent_poor_sleep" in result["flags"]
        assert result["score"] >= 2

    def test_severe_hot_flashes_flag(self, analyzer):
        entries = _make_entries(
            ["Restorative"] * 10,
            climate_vals=["Heavy"] * 10,
        )
        result = analyzer.assess_risk_level(entries)
        assert "severe_hot_flashes" in result["flags"]

    def test_multiple_severe_symptoms_flag(self, analyzer):
        entries = _make_entries(
            ["3 AM Awakening"] * 10,
            climate_vals=["Heavy"] * 10,
            clarity_vals=["Brain Fog"] * 10,
        )
        result = analyzer.assess_risk_level(entries)
        assert "multiple_severe_symptoms" in result["flags"]
        # With three severe symptoms we expect high risk
        assert result["level"] in ("moderate", "high")

    def test_concerning_notes_flag(self, analyzer):
        entries = _make_entries(
            ["Restorative"] * 10,
            notes=[""] * 9 + ["I feel unbearable pain"],
        )
        result = analyzer.assess_risk_level(entries)
        assert "concerning_user_notes" in result["flags"]

    def test_rapid_deterioration_flag(self, analyzer):
        # 14 entries: first 7 "Restorative" (0), next 7 "3 AM Awakening" (9)
        rest_vals = ["Restorative"] * 7 + ["3 AM Awakening"] * 7
        entries = _make_entries(rest_vals)
        result = analyzer.assess_risk_level(entries)
        assert "rapid_deterioration" in result["flags"]

    def test_high_risk_composite(self, analyzer):
        rest_vals = ["Restorative"] * 7 + ["3 AM Awakening"] * 7
        entries = _make_entries(
            rest_vals,
            climate_vals=["Cool"] * 7 + ["Heavy"] * 7,
            clarity_vals=["Focused"] * 7 + ["Brain Fog"] * 7,
            notes=[""] * 13 + ["unbearable"],
        )
        result = analyzer.assess_risk_level(entries)
        assert result["level"] == "high"
        assert result["score"] >= 6


# ===================================================================
# Formatting helpers
# ===================================================================


class TestFormatting:
    def test_format_statistics_summary(self):
        s = SymptomStatistics(
            mean=6.0,
            median=6.0,
            std_dev=1.5,
            min_val=3.0,
            max_val=9.0,
            trend="worsening",
            trend_slope=0.12,
            recent_avg=7.0,
            previous_avg=5.0,
            percent_change=40.0,
        )
        text = format_statistics_summary(s, "rest")
        assert "REST" in text
        assert "6.0" in text
        assert "WORSENING" in text.upper()

    def test_format_pattern_summary_empty(self):
        p = PatternAnalysis(
            has_weekly_cycle=False,
            weekly_confidence=0.0,
            has_monthly_cycle=False,
            monthly_confidence=0.0,
            correlations={},
            trend_direction="stable",
            trend_strength=0.0,
            outlier_dates=[],
            change_points=[],
        )
        text = format_pattern_summary(p)
        assert "stable" in text

    def test_format_pattern_summary_with_cycles(self):
        p = PatternAnalysis(
            has_weekly_cycle=True,
            weekly_confidence=0.8,
            has_monthly_cycle=True,
            monthly_confidence=0.6,
            correlations={"rest-climate": 0.75},
            trend_direction="worsening",
            trend_strength=0.55,
            outlier_dates=["2026-02-01"],
            change_points=["2026-01-15"],
        )
        text = format_pattern_summary(p)
        assert "Weekly cycle" in text
        assert "Monthly cycle" in text
        assert "rest-climate" in text
        assert "2026-02-01" in text
        assert "2026-01-15" in text
