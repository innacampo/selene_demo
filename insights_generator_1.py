"""
Insights Report Generator for SELENE
Uses local MedGemma to analyze user history and generate personalized insights report.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
import requests
from context_builder import get_profile_context, get_pulse_pattern_analysis, format_pulse_analysis_for_llm


# ============================================================================
# Narrative Builder
# ============================================================================


def build_complete_narrative() -> str:
    """
    Build a comprehensive narrative from all available user data sources.
    This is the "story" that MedGemma will analyze.
    
    Returns:
        Multi-section narrative string
    """
    sections = []
    
    # Section 1: Profile & Stage
    profile_ctx = get_profile_context()
    if profile_ctx:
        sections.append(profile_ctx)
    
    # Section 2: Pulse Pattern Analysis (30 days)
    analysis = get_pulse_pattern_analysis(days=30)
    if analysis:
        pulse_narrative = format_pulse_analysis_for_llm(analysis)
        sections.append(pulse_narrative)
    
    # Section 3: Recent Pulse Entries (raw data for context)
    pulse_path = Path("user_data/pulse_history.json")
    if pulse_path.exists():
        try:
            with open(pulse_path, "r") as f:
                history = json.load(f)
            
            if history:
                sections.append("=== RECENT DAILY ATTUNE ENTRIES ===")
                # Include last 10 entries
                recent_entries = history[-10:] if len(history) > 10 else history
                
                for entry in recent_entries:
                    try:
                        ts = datetime.fromisoformat(entry["timestamp"]).strftime("%b %d")
                    except (KeyError, ValueError):
                        ts = "recent"
                    
                    entry_text = f"{ts}: Rest={entry.get('rest', 'N/A')}, Climate={entry.get('climate', 'N/A')}, Clarity={entry.get('clarity', 'N/A')}"
                    if entry.get("notes"):
                        entry_text += f", Notes: {entry['notes']}"
                    sections.append(entry_text)
        
        except (json.JSONDecodeError, FileNotFoundError):
            pass
    
    if not sections:
        return "No user data available for analysis."
    
    return "\n\n".join(sections)


# ============================================================================
# MedGemma Report Generator
# ============================================================================


def generate_insights_report(
    ollama_base_url: str = "http://localhost:11434",
    model: str = "tiny-medgemma",
    timeout: int = 120
) -> tuple[str, str]:
    """
    Generate a comprehensive insights report using local MedGemma.
    
    Args:
        ollama_base_url: URL for Ollama API
        model: Model name (default: tiny-medgemma)
        timeout: Request timeout in seconds
    
    Returns:
        Tuple of (success: bool, report_text: str or error_message: str)
    """
    
    # Build the narrative
    narrative = build_complete_narrative()
    
    # Define the analysis prompt
    system_instruction = """You are Dr. Selene, an empathetic menopause specialist creating a comprehensive insights report.

Your task: Analyze the user's complete history and generate a personalized report with:

1. **Pattern Recognition:** Identify trends in symptoms over time
2. **Key Observations:** Highlight significant changes or consistent patterns
3. **Stage-Specific Insights:** Relate patterns to the user's menopause stage
4. **Actionable Recommendations:** Suggest concrete next steps

Format your response as a professional report with clear sections. Be supportive, clinical, and evidence-based."""

    prompt = f"""Based on the following comprehensive user history, generate a detailed insights report:

{narrative}

---

Please create a report with these sections:

**Symptom Pattern Analysis:**
- What patterns do you observe across Rest, Climate (hot flashes), and Clarity?
- Are there any concerning trends?

**Stage-Specific Insights:**
- How do these patterns relate to the user's current menopause stage?
- What is typical vs. unusual for this stage?

**Key Observations:**
- What stands out as most significant?
- Any correlations between different symptom categories?

**Recommendations:**
- What should the user discuss with their healthcare provider?
- What lifestyle or tracking adjustments might help?
- What warning signs to watch for?

Keep the tone supportive and empowering. Focus on patterns, not isolated incidents."""

    payload = {
        "model": model,
        "prompt": prompt,
        "system": system_instruction,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
        },
    }

    try:
        response = requests.post(
            f"{ollama_base_url}/api/generate",
            json=payload,
            timeout=timeout,
        )

        if response.status_code == 200:
            report_text = response.json().get("response", "No response generated.")
            return True, report_text
        else:
            return False, f"Error: Ollama returned status {response.status_code}"

    except requests.exceptions.Timeout:
        return False, "Request timed out. The model may be overloaded."
    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to Ollama. Is it running?"
    except Exception as e:
        return False, f"Error generating report: {str(e)}"


# ============================================================================
# Report Formatting
# ============================================================================


def format_report_for_pdf(report_text: str, user_profile: dict) -> dict:
    """
    Structure the report for PDF generation.
    
    Args:
        report_text: Raw report text from MedGemma
        user_profile: User profile dict
    
    Returns:
        Dict with structured sections for PDF rendering
    """
    return {
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
