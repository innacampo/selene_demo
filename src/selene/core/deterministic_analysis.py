"""
Deterministic Inference Engine.

Provides zero-latency, reproducible statistical analysis to supplement
LLM reasoning. This module handles:
1. Label Normalization: Mapping qualitative symptom labels to numeric scales.
2. Time-Series Analysis: Trend detection, cycle identification, and correlation.
3. Signal Processing: Autocorrelation for period detection (weekly/monthly).
4. Safety Guardrails: Rule-based risk scoring for urgent clinical flags.
"""

import logging
from dataclasses import dataclass
from datetime import datetime

import numpy as np
from scipy import stats

from selene.constants import SYMPTOM_SEVERITY_MAP

logger = logging.getLogger(__name__)


@dataclass
class SymptomStatistics:
    """Statistical summary of a symptom."""

    mean: float
    median: float
    std_dev: float
    min_val: float
    max_val: float
    trend: str  # "improving", "declining", "stable"
    trend_slope: float
    recent_avg: float  # Last 7 days
    previous_avg: float  # Previous 7 days
    percent_change: float


@dataclass
class PatternAnalysis:
    """Results from pattern detection algorithms."""

    has_weekly_cycle: bool
    weekly_confidence: float
    has_monthly_cycle: bool
    monthly_confidence: float
    correlations: dict[str, float]  # e.g., {"rest-climate": -0.45}
    trend_direction: str
    trend_strength: float
    outlier_dates: list[str]
    change_points: list[str]


class DeterministicAnalyzer:
    """
    Core Statistical Engine for SELENE.

    This class implements the 'Math Layer' of the hybrid multi-agent system.
    By performing calculations in pure Python/NumPy/SciPy, we avoid LLM
    hallucinations in data processing and significantly reduce token costs.
    """

    def __init__(self):
        self.min_data_points = 7  # Minimum for meaningful analysis
        self.score_map = SYMPTOM_SEVERITY_MAP  # 0 = no symptoms, 10 = severe
        logger.debug(f"DeterministicAnalyzer.__init__: min_data_points={self.min_data_points}")

    def _map_symptom_to_score(self, value: any) -> float | None:
        """Convert qualitative labels or numeric strings to float scores."""
        if value is None:
            logger.debug("_map_symptom_to_score: value is None -> None")
            return None

        if isinstance(value, (int, float)):
            logger.debug(f"_map_symptom_to_score: numeric input -> {float(value)}")
            return float(value)

        if isinstance(value, str):
            # Check if it's a known mapping
            if value in self.score_map:
                mapped = float(self.score_map[value])
                logger.debug(f"_map_symptom_to_score: mapped '{value}' -> {mapped}")
                return mapped

            # Check if it's a numeric string
            try:
                num = float(value)
                logger.debug(f"_map_symptom_to_score: numeric_str '{value}' -> {num}")
                return num
            except ValueError:
                logger.debug(f"_map_symptom_to_score: unrecognized string '{value}' -> None")
                return None

        logger.debug(f"_map_symptom_to_score: unsupported type {type(value)} -> None")
        return None

    # ========================================================================
    # Symptom Statistics
    # ========================================================================

    def analyze_symptom_statistics(
        self,
        entries: list[dict],
        symptom_key: str,  # "rest", "climate", or "clarity"
    ) -> SymptomStatistics | None:
        """
        Calculate comprehensive statistics for a single symptom.

        Args:
            entries: List of pulse entries
            symptom_key: Which symptom to analyze

        Returns:
            SymptomStatistics object or None if insufficient data
        """
        logger.debug(
            f"analyze_symptom_statistics: ENTER symptom_key={symptom_key} entries={len(entries)}"
        )
        # Extract and map values
        raw_values = [e.get(symptom_key) for e in entries if symptom_key in e]
        values = [self._map_symptom_to_score(v) for v in raw_values]
        values = [v for v in values if v is not None]

        logger.debug(f"analyze_symptom_statistics: mapped_values_count={len(values)}")
        if len(values) < self.min_data_points:
            logger.info(
                f"analyze_symptom_statistics: insufficient data ({len(values)} < {self.min_data_points})"
            )
            return None

        values = np.array(values)

        # Basic statistics
        mean = np.mean(values)
        median = np.median(values)
        std_dev = np.std(values)
        min_val = np.min(values)
        max_val = np.max(values)

        # Trend analysis (compare recent vs previous period)
        mid_point = len(values) // 2
        recent_values = values[mid_point:]
        previous_values = values[:mid_point]

        recent_avg = np.mean(recent_values)
        previous_avg = np.mean(previous_values)
        percent_change = (
            ((recent_avg - previous_avg) / previous_avg * 100) if previous_avg > 0 else 0
        )

        # Linear regression for trend
        x = np.arange(len(values))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, values)

        # Determine trend direction
        # Higher scores = worse symptoms, so positive slope = worsening
        if slope > 0.05:
            trend = "worsening"
        elif slope < -0.05:
            trend = "improving"
        else:
            trend = "stable"

        stats_out = SymptomStatistics(
            mean=round(mean, 2),
            median=round(median, 2),
            std_dev=round(std_dev, 2),
            min_val=round(min_val, 2),
            max_val=round(max_val, 2),
            trend=trend,
            trend_slope=round(slope, 4),
            recent_avg=round(recent_avg, 2),
            previous_avg=round(previous_avg, 2),
            percent_change=round(percent_change, 2),
        )
        logger.debug(f"analyze_symptom_statistics: EXIT stats={stats_out}")
        return stats_out

    # ========================================================================
    # Pattern Detection
    # ========================================================================

    def detect_patterns(self, entries: list[dict]) -> PatternAnalysis:
        """
        Detect temporal patterns and correlations in symptom data.
        Uses statistical methods instead of LLM.

        Args:
            entries: List of pulse entries

        Returns:
            PatternAnalysis object
        """

        # Extract and map symptom arrays
        def get_mapped_values(key):
            raw = [e.get(key) for e in entries]
            mapped = [self._map_symptom_to_score(v) for v in raw]
            # Replace None with midpoint default (neutral on 0-10 scale)
            default = 5
            return np.array([v if v is not None else default for v in mapped])

        rest_values = get_mapped_values("rest")
        climate_values = get_mapped_values("climate")
        clarity_values = get_mapped_values("clarity")

        # Ensure all arrays have same length (use minimum)
        min_len = min(len(rest_values), len(climate_values), len(clarity_values))
        rest_values = rest_values[:min_len]
        climate_values = climate_values[:min_len]
        clarity_values = clarity_values[:min_len]

        logger.debug(f"detect_patterns: min_len={min_len}")
        if min_len < self.min_data_points:
            logger.info("detect_patterns: insufficient data for pattern detection")
            return self._empty_pattern_analysis()

        # 1. Cyclical pattern detection using autocorrelation
        has_weekly, weekly_conf = self._detect_cycle(rest_values, period=7)
        has_monthly, monthly_conf = self._detect_cycle(rest_values, period=28)

        logger.debug(
            f"detect_patterns: weekly={has_weekly} (conf={weekly_conf}), monthly={has_monthly} (conf={monthly_conf})"
        )
        # 2. Correlation analysis
        correlations = self._calculate_correlations(rest_values, climate_values, clarity_values)
        logger.debug(f"detect_patterns: correlations={correlations}")
        # 3. Trend analysis
        trend_dir, trend_strength = self._analyze_trend(rest_values)
        logger.debug(f"detect_patterns: trend={trend_dir}, strength={trend_strength}")
        # 4. Outlier detection
        outlier_dates = self._detect_outliers(entries, rest_values)
        logger.debug(f"detect_patterns: outliers={outlier_dates}")
        # 5. Change point detection
        change_points = self._detect_change_points(entries, rest_values)
        logger.debug(f"detect_patterns: change_points={change_points}")

        return PatternAnalysis(
            has_weekly_cycle=has_weekly,
            weekly_confidence=weekly_conf,
            has_monthly_cycle=has_monthly,
            monthly_confidence=monthly_conf,
            correlations=correlations,
            trend_direction=trend_dir,
            trend_strength=trend_strength,
            outlier_dates=outlier_dates,
            change_points=change_points,
        )

    def _detect_cycle(self, values: np.ndarray, period: int) -> tuple[bool, float]:
        """
        Detect if there's a cyclical pattern at given period.
        Uses autocorrelation.
        """
        if len(values) < period * 2:
            return False, 0.0

        # Calculate autocorrelation at the specified lag
        try:
            autocorr = np.correlate(values - np.mean(values), values - np.mean(values), mode="full")
            autocorr = autocorr[len(autocorr) // 2 :]
            baseline = autocorr[0]
            if np.isclose(baseline, 0.0):
                return False, 0.0
            autocorr = autocorr / baseline  # Normalize

            if len(autocorr) > period:
                cycle_strength = abs(autocorr[period])
                has_cycle = cycle_strength > 0.3  # Threshold for significance
                return has_cycle, round(cycle_strength, 3)
        except Exception:
            pass

        return False, 0.0

    def _calculate_correlations(
        self, rest: np.ndarray, climate: np.ndarray, clarity: np.ndarray
    ) -> dict[str, float]:
        """Calculate pairwise correlations between symptoms."""
        correlations = {}

        def _safe_corr(a, b):
            # If weight/variance is 0, correlation is undefined (but we'll return 0)
            if np.std(a) == 0 or np.std(b) == 0:
                return 0.0
            return float(np.corrcoef(a, b)[0, 1])

        try:
            # Pearson correlation coefficients
            if len(rest) > 2:
                correlations["rest-climate"] = round(_safe_corr(rest, climate), 3)
                correlations["rest-clarity"] = round(_safe_corr(rest, clarity), 3)
                correlations["climate-clarity"] = round(_safe_corr(climate, clarity), 3)
        except Exception:
            correlations = {
                "rest-climate": 0.0,
                "rest-clarity": 0.0,
                "climate-clarity": 0.0,
            }

        return correlations

    def _analyze_trend(self, values: np.ndarray) -> tuple[str, float]:
        """Analyze overall trend direction and strength."""
        if len(values) < self.min_data_points:
            return "unknown", 0.0

        x = np.arange(len(values))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, values)

        # Classify trend
        # Higher scores = worse symptoms, so positive slope = worsening
        if abs(slope) < 0.05:
            direction = "stable"
        elif slope > 0:
            direction = "worsening"
        else:
            direction = "improving"

        # R-squared as strength measure
        strength = round(r_value**2, 3)

        return direction, strength

    def _detect_outliers(self, entries: list[dict], values: np.ndarray) -> list[str]:
        """Detect outlier days using IQR method."""
        if len(values) < self.min_data_points:
            return []

        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        outliers = []
        for i, val in enumerate(values):
            if val < lower_bound or val > upper_bound:
                try:
                    date = datetime.fromisoformat(entries[i]["timestamp"]).strftime("%Y-%m-%d")
                    outliers.append(date)
                except (KeyError, ValueError, IndexError):
                    pass

        return outliers[:5]  # Limit to top 5

    def _detect_change_points(self, entries: list[dict], values: np.ndarray) -> list[str]:
        """Detect significant change points in the time series."""
        if len(values) < 14:  # Need at least 2 weeks
            return []

        change_points = []
        window = 7

        for i in range(window, len(values) - window):
            before = values[i - window : i]
            after = values[i : i + window]

            # T-test for significant difference
            t_stat, p_value = stats.ttest_ind(before, after)

            if p_value < 0.05:  # Significant change
                try:
                    date = datetime.fromisoformat(entries[i]["timestamp"]).strftime("%Y-%m-%d")
                    change_points.append(date)
                except (KeyError, ValueError, IndexError):
                    pass

        return change_points[:3]  # Limit to top 3

    def _empty_pattern_analysis(self) -> PatternAnalysis:
        """Return empty pattern analysis when insufficient data."""
        return PatternAnalysis(
            has_weekly_cycle=False,
            weekly_confidence=0.0,
            has_monthly_cycle=False,
            monthly_confidence=0.0,
            correlations={},
            trend_direction="unknown",
            trend_strength=0.0,
            outlier_dates=[],
            change_points=[],
        )

    # ========================================================================
    # Risk Assessment (Deterministic Rules)
    # ========================================================================

    def assess_risk_level(self, entries: list[dict]) -> dict:
        """
        Urgency Scoring & Trigger Logic.

        Analyzes the last 7-14 days of data for high-risk patterns:
        - Severe absolute scores (e.g., persistent 'Flashing' climate).
        - Rapid delta (e.g., sleep quality dropping >20% WoW).
        - Multi-symptom clusters (concomitant poor sleep and high climate).
        - Keyword detection in qualitative notes.

        Returns:
            Dict: {level: str, score: int, flags: List[str], rationale: str}
        """
        if len(entries) < 7:
            return {"level": "insufficient_data", "flags": [], "score": 0}

        recent = entries[-7:]  # Last week
        flags = []
        risk_score = 0

        # Flag 1: Persistent severe symptoms
        rest_values = [self._map_symptom_to_score(e.get("rest")) for e in recent]
        rest_values = [v for v in rest_values if v is not None]

        climate_values = [self._map_symptom_to_score(e.get("climate")) for e in recent]
        climate_values = [v for v in climate_values if v is not None]

        clarity_values = [self._map_symptom_to_score(e.get("clarity")) for e in recent]
        clarity_values = [v for v in clarity_values if v is not None]

        # Higher scores = worse symptoms (0 = no symptoms, 10 = severe)
        if rest_values and np.mean(rest_values) > 7:
            flags.append("persistent_poor_sleep")
            risk_score += 2

        if climate_values and np.mean(climate_values) > 7:
            flags.append("severe_hot_flashes")
            risk_score += 2

        if clarity_values and np.mean(clarity_values) > 7:
            flags.append("severe_brain_fog")
            risk_score += 1

        # Flag 2: Rapid deterioration
        if len(entries) >= 14:
            prev_week = entries[-14:-7]
            prev_rest_raw = [self._map_symptom_to_score(e.get("rest")) for e in prev_week]
            prev_rest_vals = [v for v in prev_rest_raw if v is not None]
            prev_rest = np.mean(prev_rest_vals) if prev_rest_vals else 0
            recent_rest = np.mean(rest_values) if rest_values else 0

            # Higher scores = worse; rising score = deterioration
            if recent_rest - prev_rest > 2:  # Increase of >2 points
                flags.append("rapid_deterioration")
                risk_score += 3

        # Flag 3: Multiple severe symptoms simultaneously
        # Higher scores = worse symptoms (0 = no symptoms, 10 = severe)
        severe_count = sum(
            [
                np.mean(rest_values) > 7 if rest_values else False,
                np.mean(climate_values) > 7 if climate_values else False,
                np.mean(clarity_values) > 7 if clarity_values else False,
            ]
        )

        if severe_count >= 2:
            flags.append("multiple_severe_symptoms")
            risk_score += 2

        # Flag 4: Concerning notes
        concerning_keywords = [
            "unbearable",
            "emergency",
            "extreme",
            "can't",
            "terrible",
            "awful",
        ]
        for entry in recent:
            note = entry.get("notes", "").lower()
            if any(keyword in note for keyword in concerning_keywords):
                flags.append("concerning_user_notes")
                risk_score += 1
                break

        # Classify risk level
        if risk_score >= 6:
            level = "high"
        elif risk_score >= 3:
            level = "moderate"
        else:
            level = "low"

        return {
            "level": level,
            "score": risk_score,
            "flags": flags,
            "rationale": self._generate_risk_rationale(level, flags, risk_score),
        }

    def _generate_risk_rationale(self, level: str, flags: list[str], score: int) -> str:
        """Generate human-readable rationale for risk level."""
        rationale_map = {
            "persistent_poor_sleep": "Sleep disruption severity above 7/10 for past week",
            "severe_hot_flashes": "Hot flash severity above 7/10 average",
            "severe_brain_fog": "Brain fog severity above 7/10 average",
            "rapid_deterioration": "Symptom severity increased by >2 points in past week",
            "multiple_severe_symptoms": "Two or more severe symptoms occurring simultaneously",
            "concerning_user_notes": "User notes indicate extreme distress",
        }

        rationales = [rationale_map.get(flag, flag) for flag in flags]

        return f"Risk level: {level.upper()} (score: {score}/10). " + "; ".join(rationales)


# ========================================================================
# Formatting Functions (Convert to Natural Language)
# ========================================================================


def format_statistics_summary(stats: SymptomStatistics, symptom_name: str) -> str:
    """Convert statistics to readable summary."""
    summary = f"""
**{symptom_name.upper()} ANALYSIS:**
- Average: {stats.mean}/10 (Range: {stats.min_val}-{stats.max_val})
- Trend: {stats.trend.upper()} (slope: {stats.trend_slope})
- Recent week: {stats.recent_avg}/10 (vs previous: {stats.previous_avg}/10)
- Change: {stats.percent_change:+.1f}%
- Variability: {stats.std_dev:.1f} (standard deviation)
    """.strip()

    return summary


def format_pattern_summary(patterns: PatternAnalysis) -> str:
    """Convert pattern analysis to readable summary."""
    summary_parts = ["**PATTERN ANALYSIS:**"]

    # Cycles
    if patterns.has_weekly_cycle:
        summary_parts.append(
            f"- Weekly cycle detected (confidence: {patterns.weekly_confidence:.0%})"
        )
    if patterns.has_monthly_cycle:
        summary_parts.append(
            f"- Monthly cycle detected (confidence: {patterns.monthly_confidence:.0%})"
        )

    # Correlations
    if patterns.correlations:
        summary_parts.append("- Symptom correlations:")
        for pair, corr in patterns.correlations.items():
            strength = "strong" if abs(corr) > 0.7 else "moderate" if abs(corr) > 0.4 else "weak"
            direction = "positive" if corr > 0 else "negative"
            summary_parts.append(f"  • {pair}: {strength} {direction} ({corr:+.2f})")

    # Trend
    summary_parts.append(
        f"- Overall trend: {patterns.trend_direction} (strength: {patterns.trend_strength:.0%})"
    )

    # Outliers
    if patterns.outlier_dates:
        summary_parts.append(f"- Outlier dates: {', '.join(patterns.outlier_dates)}")

    # Change points
    if patterns.change_points:
        summary_parts.append(
            f"- Significant changes detected on: {', '.join(patterns.change_points)}"
        )

    return "\n".join(summary_parts)
