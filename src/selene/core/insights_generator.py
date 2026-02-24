"""
Insights Report Generator for SELENE (Enhanced Single-LLM Version)

Improvements:
- Robust error handling with detailed diagnostics
- Context validation before LLM call
- Report quality metrics
- Better logging and debugging
- Configurable retry logic
"""

import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from selene import settings
from selene.core.context_builder_multi_agent import build_complete_context, get_context_summary
from selene.core.deterministic_analysis import (
    DeterministicAnalyzer,
    format_pattern_summary,
    format_statistics_summary,
)

logger = logging.getLogger(__name__)


@dataclass
class ReportMetrics:
    """Quality metrics for generated report."""

    word_count: int
    section_count: int
    has_all_sections: bool
    generation_time_seconds: float
    context_completeness: float


def validate_context(context: dict) -> tuple[bool, str]:
    """
    Validate context before report generation.

    Returns:
        (is_valid, error_message)
    """
    # Check pulse data
    if not context.get("pulse_entries"):
        return False, "No pulse data available for this period"

    if len(context["pulse_entries"]) < 3:
        return (
            False,
            f"Insufficient data: only {len(context['pulse_entries'])} entries (minimum 3 required)",
        )

    # Check completeness
    completeness = context["metadata"].get("data_completeness_score", 0)
    if completeness < 0.4:
        return False, f"Data completeness too low: {completeness * 100:.0f}% (minimum 40% required)"

    logger.debug(
        f"Context validation passed: {len(context['pulse_entries'])} entries, "
        f"{completeness * 100:.0f}% complete"
    )
    return True, ""


def calculate_report_metrics(
    report_text: str, generation_time: float, context: dict
) -> ReportMetrics:
    """Calculate quality metrics for the generated report."""
    word_count = len(report_text.split())

    # Check for required sections
    required_sections = [
        "### How You've Been",
        "### What Your Body Is Telling You",
        "### Patterns & Connections",
        "### For Your Provider",
    ]

    section_count = sum(1 for section in required_sections if section in report_text)
    has_all_sections = section_count == len(required_sections)

    return ReportMetrics(
        word_count=word_count,
        section_count=section_count,
        has_all_sections=has_all_sections,
        generation_time_seconds=round(generation_time, 2),
        context_completeness=context["metadata"].get("data_completeness_score", 0),
    )


def clean_report_text(report_text: str) -> str:
    """
    Remove common LLM preambles and postambles from report text.

    Args:
        report_text: Raw LLM output

    Returns:
        Cleaned report text starting with first markdown header
    """
    # Common preamble patterns to remove
    preamble_patterns = [
        "Okay, SELENE is ready",
        "Here is your personalized",
        "Here's your personalized",
        "Let me provide",
        "I'll provide",
        "Based on your data",
        "Alright,",
        "Okay,",
        "Sure,",
        "***",
        "---",
    ]

    lines = report_text.split("\n")
    start_idx = 0

    # Find the first line that contains a markdown header (###)
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("###"):
            start_idx = idx
            break
        # Also check if any preamble pattern is in this line
        if any(pattern.lower() in stripped.lower() for pattern in preamble_patterns):
            continue
        # If we hit substantial content before a header, start there
        elif (
            stripped
            and len(stripped) > 20
            and not any(p in stripped for p in ["*", "-", "ready", "provide"])
        ):
            start_idx = idx
            break

    # Rejoin from the start index
    cleaned = "\n".join(lines[start_idx:])

    # Remove common postambles
    postamble_patterns = [
        "I hope this",
        "Please let me know",
        "Feel free to",
        "Don't hesitate",
        "Remember, I'm here",
    ]

    lines = cleaned.split("\n")
    end_idx = len(lines)

    # Scan backwards for postambles
    for idx in range(len(lines) - 1, -1, -1):
        stripped = lines[idx].strip()
        if any(pattern.lower() in stripped.lower() for pattern in postamble_patterns):
            end_idx = idx
        elif stripped and "###" in stripped:
            # Stop at last valid section
            break

    cleaned = "\n".join(lines[:end_idx])

    # Clean up extra whitespace
    cleaned = "\n".join(line for line in cleaned.split("\n") if line.strip() or "")

    return cleaned.strip()


def validate_report_quality(report_text: str, context: dict) -> tuple[bool, list[str]]:
    """
    Check for common quality issues in generated report.

    Returns:
        (is_valid, list_of_issues)
    """
    issues = []

    # Check for vague language
    vague_phrases = [
        "some positive shifts",
        "areas needing attention",
        "quite",
        "somewhat",
        "a bit",
        "rather",
        "fairly",
        "pretty much",
    ]
    for phrase in vague_phrases:
        if phrase.lower() in report_text.lower():
            issues.append(f"Contains vague phrase: '{phrase}'")

    # Check for specific date references if notes exist
    has_dates = any(
        month in report_text
        for month in [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
    )

    if context["metadata"]["notes_count"] > 0 and not has_dates:
        issues.append("No specific dates referenced from user notes")

    # Check for direct quotes if notes exist
    if context["metadata"]["notes_count"] > 0 and '"' not in report_text:
        issues.append("No direct quotes from user's notes (adds authenticity)")

    # Check all required sections present
    required_sections = [
        "### How You've Been",
        "### What Your Body Is Telling You",
        "### Patterns & Connections",
        "### For Your Provider",
    ]
    missing_sections = [s for s in required_sections if s not in report_text]
    if missing_sections:
        issues.append(f"Missing sections: {', '.join(missing_sections)}")

    # Check for scale mentions (should explain what scores mean)
    if "/10" not in report_text:
        issues.append("No score explanations found (should reference X/10 scale)")

    return len(issues) == 0, issues


def sanitize_user_input(text: str, max_length: int = 5000) -> str:
    """Sanitize user-provided text before LLM prompt injection.

    Truncates to *max_length*, strips control characters, and escapes
    delimiters that could be interpreted as prompt structure.
    """
    if not text:
        return text
    text = text[:max_length]
    # Keep printable chars plus newlines/tabs
    text = "".join(c for c in text if c.isprintable() or c in "\n\t")
    # Escape markdown headers that could confuse section parsing
    text = text.replace("###", "\\#\\#\\#")
    # Escape XML-like angle brackets
    text = text.replace("</", "&lt;/")
    text = text.replace("<", "&lt;")
    return text.strip()


def generate_insights_report(
    model: str = settings.LLM_MODEL,
    timeout: int = 240,
    save_full_report: bool = False,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    retry_on_failure: bool = True,
    max_retries: int = 2,
) -> tuple[bool, str, dict | None]:
    """
    Generate a personal insights report with enhanced error handling.

    Returns:
        Tuple[bool, str, Optional[Dict]]: (success, report_or_error, metadata)
    """
    generation_start = time.time()

    try:
        # === 1. Build enriched context ===
        logger.info("Building enriched context")
        context = build_complete_context(start_date=start_date, end_date=end_date)

        # Log context summary
        logger.debug(get_context_summary(context))

        # Validate context
        is_valid, error_msg = validate_context(context)
        if not is_valid:
            logger.error(f"Context validation failed: {error_msg}")
            return False, error_msg, None

        logger.info(
            f"Context ready: {len(context['pulse_entries'])} entries, "
            f"{context['metadata']['notes_count']} notes, "
            f"{context['metadata']['chat_message_count']} messages"
        )

        # === 2. Deterministic analysis ===
        logger.info("Running deterministic analysis")
        analyzer = DeterministicAnalyzer()

        # Symptom statistics
        rest_stats = analyzer.analyze_symptom_statistics(context["pulse_entries"], "rest")
        climate_stats = analyzer.analyze_symptom_statistics(context["pulse_entries"], "climate")
        clarity_stats = analyzer.analyze_symptom_statistics(context["pulse_entries"], "clarity")

        stats_block = ""
        if rest_stats:
            stats_block += format_statistics_summary(rest_stats, "Rest Quality") + "\n\n"
        if climate_stats:
            stats_block += format_statistics_summary(climate_stats, "Hot Flashes") + "\n\n"
        if clarity_stats:
            stats_block += format_statistics_summary(clarity_stats, "Mental Clarity") + "\n\n"

        # Pattern detection
        patterns = analyzer.detect_patterns(context["pulse_entries"])
        patterns_block = format_pattern_summary(patterns)

        # Risk assessment
        risk = analyzer.assess_risk_level(context["pulse_entries"])
        risk_block = (
            f"Risk Level: {risk['level'].upper()} (score {risk['score']}/10)\n"
            f"Flags: {', '.join(risk['flags']) if risk['flags'] else 'None'}\n"
            f"{risk.get('rationale', '')}"
        )

        logger.info(
            f"Analysis complete: Risk={risk['level']}, "
            f"Patterns={len(patterns.__dict__ if hasattr(patterns, '__dict__') else {})}"
        )

        # === 3. Compose LLM prompt ===
        profile = context.get("profile", {})
        all_notes = sanitize_user_input(context.get("all_notes", "No notes."))
        sanitize_user_input(context.get("chat_context", "No chat messages."))

        system_instruction = """You are SELENE, a clinical AI for menopause.
ROLE: Clinical Analyst.
TONE: Empathetic but precise. Avoid vague "good/bad" conversational fillers.

SEVERITY SCALE (0-10):
- 0 = Optimal/None (The goal)
- 10 = Critical/Severe (Maximum symptoms)

LABELING RULES:
- 0-3.9: Mild
- 4-6.9: Moderate
- 7-10: Severe

VOCABULARY RULES (CRITICAL):
- Never use the word "Stable" for scores above 7.0/10. Use "Persistently Severe" or "Concerningly High".
- Never use the word "Decreased" to describe a lower severity score. Use "Improved".
- Mental Clarity at 9/10 is NOT good. It is a SEVERE clinical symptom. Frame it as "extreme distress" or "severe cognitive impact".

TREND LOGIC:
- Score went down (e.g. 7.1 -> 6.8): Framing = IMPROVEMENT.
- Score went up (e.g. 4.4 -> 7.0): Framing = WORSENING.

ABSOLUTE RULES:
1. Start immediately with '### How You've Been'.
2. Use double newlines between sections.
3. For Section 4, copy the Risk Level and Flags exactly as written in the input.
4. Use bullet points for lists."""

        examples = """
✅ GOOD (Improvement framing):
"Your rest quality improved slightly (7.1 -> 6.8), though overall severity remains high."

✅ GOOD (Persistent Severity framing):
"Your mental clarity remains concerningly high at 9.0/10, showing no relief from severe brain fog."
"""

        # === USER PROMPT ===
        prompt = f"""
### INPUT DATA (Verified)
<STATISTICS>
{stats_block}
</STATISTICS>

<PATTERN_ANALYSIS>
{patterns_block}
</PATTERN_ANALYSIS>

<RISK_ASSESSMENT>
{risk_block}
</RISK_ASSESSMENT>

<USER_NOTES>
{all_notes}
</USER_NOTES>

---

### STRUCTURE REQUIREMENTS

### How You've Been
Summarize the period. Reference 2 quotes from <USER_NOTES>.
Frame a drop in score (7.1 to 6.8) as an IMPROVEMENT.
Frame a high score (9.0) as a SEVERE CONCERN, never as "stable" or "good".

### What Your Body Is Telling You
Analyze each symptom on a single line. Do NOT output the word "(Label)", replace it with Mild, Moderate, or Severe:
- **[Symptom]**: Avg Severity X.X/10 [Label]. Trend: [Improved if score decreased, Worsening if score increased, Persistently Severe if stable > 7]. Note: [Quote].

### Patterns & Connections
Describe patterns from <PATTERN_ANALYSIS>.

### For Your Provider
- **Risk Level**: [Copy LEVEL from <RISK_ASSESSMENT>]
- **Risk Flags**: [Copy FLAGS from <RISK_ASSESSMENT>]
- [Bullet point: Compare current average vs previous average. Use the word "Improvement" if current is LOWER.]
- [Bullet point: Highlight scores > 7.0/10 as "Clinically Severe Priority".]

- **Clinical Questions for Your Next Visit:**
Synthesize the statistics and user notes to create 3-5 specific, first-person questions for a doctor. Use reasoning to determine the most urgent topics.
- **Tone**: First person ("Could we...", "I'm concerned about...").
- **Constraint**: Do not use placeholders. Synthesize the actual symptom names and trends from the data.
- **Objective 1 (Medical)**: Target the symptom with the highest increase in severity. Ask about medication or HRT adjustments.
- **Objective 2 (Diagnostic)**: Target the most persistent high score (e.g., Brain Fog). Ask about ruling out metabolic or nutritional causes.
- **Objective 3 (Lifestyle)**: Ask about non-pharmacological interventions for the specific pattern (e.g., night-time cooling if rest and climate are correlated).
- **Objective 4 (Environmental)**: Link any patterns (like weekly cycles or climate shifts) to a request for management strategies.

---
{examples}
"""

        # === 4. LLM call via local transformers model with retry logic ===
        logger.info(f"Calling LLM ({model}) via local transformers")

        from selene.core.med_logic import _get_model

        report_text = None
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt}/{max_retries}")
                    time.sleep(2**attempt)  # Exponential backoff

                import torch

                llm_model, processor = _get_model()
                messages = [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt},
                ]
                inputs = processor.apply_chat_template(
                    messages,
                    add_generation_prompt=True,
                    tokenize=True,
                    return_dict=True,
                    return_tensors="pt",
                ).to(llm_model.device, dtype=torch.bfloat16)
                input_len = inputs["input_ids"].shape[-1]
                with torch.inference_mode():
                    generation = llm_model.generate(
                        **inputs,
                        max_new_tokens=1024,
                        do_sample=True,
                        temperature=0.3,
                        top_p=0.9,
                    )
                report_text = processor.decode(
                    generation[0][input_len:], skip_special_tokens=True
                )
                if not report_text or not report_text.strip():
                    last_error = "LLM returned empty response"
                    if not retry_on_failure or attempt == max_retries:
                        return False, last_error, None
                    continue

                # Clean unwanted preambles/postambles
                report_text = clean_report_text(report_text)

                # Success!
                break

            except Exception as e:
                last_error = f"LLM call failed: {type(e).__name__}: {e}"
                logger.error(last_error)
                if not retry_on_failure or attempt == max_retries:
                    return False, last_error, None

        if not report_text:
            return False, last_error or "Unknown error", None

        generation_time = time.time() - generation_start
        logger.info(f"Report generated: {len(report_text)} chars in {generation_time:.1f}s")

        # Calculate metrics
        metrics = calculate_report_metrics(report_text, generation_time, context)
        logger.info(
            f"Report metrics: {metrics.word_count} words, "
            f"{metrics.section_count}/4 sections, "
            f"completeness: {metrics.context_completeness * 100:.0f}%"
        )

        # Validate report quality
        is_quality, quality_issues = validate_report_quality(report_text, context)
        if not is_quality:
            logger.warning(f"Report quality issues detected: {quality_issues}")
        else:
            logger.info("Report passed quality validation")

        # === 5. Optional: save full report JSON ===
        if save_full_report:
            report_dir = Path("reports")
            report_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = report_dir / f"selene_report_{timestamp}.json"

            # Convert patterns to JSON-serializable format
            patterns_dict = None
            if patterns:
                if hasattr(patterns, "__dict__"):
                    patterns_dict = asdict(patterns)
                elif isinstance(patterns, dict):
                    patterns_dict = patterns
                else:
                    patterns_dict = str(patterns)

            full_report = {
                "generated_at": datetime.now().isoformat(),
                "model": model,
                "user_stage": profile.get("stage_title", "Unknown"),
                "deterministic": {
                    "rest_stats": asdict(rest_stats) if rest_stats else None,
                    "climate_stats": asdict(climate_stats) if climate_stats else None,
                    "clarity_stats": asdict(clarity_stats) if clarity_stats else None,
                    "patterns": patterns_dict,
                    "risk": risk,
                },
                "context_metadata": context["metadata"],
                "report_text": report_text,
                "metrics": asdict(metrics),
            }

            try:
                with open(report_path, "w", encoding="utf-8") as f:
                    json.dump(full_report, f, indent=2, ensure_ascii=False, default=str)
                logger.info(f"Full report saved to {report_path}")
            except TypeError as e:
                logger.error(f"Failed to save full report: {e}")
                # Save without the problematic data
                try:
                    full_report["deterministic"]["patterns"] = str(patterns)
                    with open(report_path, "w", encoding="utf-8") as f:
                        json.dump(full_report, f, indent=2, ensure_ascii=False)
                    logger.info(f"Full report saved (patterns as string) to {report_path}")
                except Exception as e2:
                    logger.error(f"Failed to save report even with fallback: {e2}")

        return True, report_text, asdict(metrics)

    except Exception as e:
        logger.exception("Unexpected error in generate_insights_report")
        return False, f"Error generating report: {str(e)}", None


def format_report_for_pdf(
    report_text: str, user_profile: dict, metrics: dict | None = None
) -> dict:
    """Structure report for PDF generation with metrics."""
    result = {
        "title": "SELENE Insights Report",
        "generated_date": datetime.now().strftime("%B %d, %Y"),
        "user_stage": user_profile.get("stage_title", "Unknown"),
        "report_content": report_text,
        "disclaimer": (
            "This report is generated based on your tracked data and is for "
            "informational purposes only. It is not medical advice. Please "
            "discuss these insights with your healthcare provider."
        ),
    }

    if metrics:
        result["metrics"] = metrics

    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SELENE Insights Generator (Enhanced)")
    parser.add_argument("--model", default=settings.LLM_MODEL, help="HF model ID")
    parser.add_argument("--days", type=int, default=30, help="Days to analyze")
    parser.add_argument("--no-retry", action="store_true", help="Disable retry on failure")

    args = parser.parse_args()

    success, report, metrics = generate_insights_report(
        model=args.model,
        save_full_report=True,
        retry_on_failure=not args.no_retry,
    )

    if success:
        print("\n" + report)
        if metrics:
            print("\n--- Metrics ---")
            print(f"Words: {metrics['word_count']}")
            print(f"Sections: {metrics['section_count']}/4")
            print(f"Generation time: {metrics['generation_time_seconds']}s")
    else:
        print(f"\n Error: {report}")
