import streamlit as st
import json
from pathlib import Path
from datetime import datetime


# ============================================================================
# Profile Storage
# ============================================================================

PROFILE_PATH = Path("./user_profile.json")


def save_profile(profile_data: dict):
    """Save user profile to JSON file."""
    profile_data["created_at"] = datetime.now().isoformat()
    profile_data["last_updated"] = datetime.now().isoformat()

    with open(PROFILE_PATH, "w") as f:
        json.dump(profile_data, f, indent=2)

    # Also store in session state for runtime access
    st.session_state.user_profile = profile_data
    st.session_state.onboarding_complete = True


def load_profile() -> dict | None:
    """Load user profile from JSON file."""
    if PROFILE_PATH.exists():
        with open(PROFILE_PATH, "r") as f:
            return json.load(f)
    return None


def profile_exists() -> bool:
    """Check if user has completed onboarding."""
    return PROFILE_PATH.exists()


# ============================================================================
# Stage Definitions
# ============================================================================

STAGES = {
    "steady_state": {
        "title": "The Steady State (Late Reproductive)",
        "cycle": "Your periods are still regular, but you may notice subtle changes (e.g., the cycle is 2-3 days shorter than it used to be).",
        "science": "Ovarian reserve is beginning to decline. Your brain is working harder to signal the ovaries, leading to early spikes in FSH (Follicle-Stimulating Hormone).",
    },
    "early_transition": {
        "title": "The Great Fluctuation (Early Transition)",
        "cycle": "You've noticed a persistent difference in cycle length (7 days or more difference between consecutive cycles). You might have skipped one period.",
        "science": 'This is the onset of "true" perimenopause. Estrogen is no longer declining smoothly; it is fluctuating wildly, often causing "estrogen dominance" symptoms like breast tenderness or irritability.',
    },
    "late_transition": {
        "title": "The Gap (Late Transition)",
        "cycle": "You have gone 60 days or more without a period, or you are skipping multiple cycles.",
        "science": 'Your HPO (Hypothalamic-Pituitary-Ovarian) axis is beginning to "power down." This is the peak "window of vulnerability" for brain fog and hot flashes as the brain\'s thermostat (the hypothalamus) loses its steady estrogen supply.',
    },
    "early_postmenopause": {
        "title": "The Milestone (Early Postmenopause)",
        "cycle": "It has been more than 12 consecutive months since your last period.",
        "science": "You have reached the official milestone of menopause. Your body is now adapting to a new, lower-estrogen baseline.",
    },
    "late_postmenopause": {
        "title": "The New Plateau (Late Postmenopause)",
        "cycle": "Permanent amenorrhea (no periods).",
        "science": 'Beginning roughly 5-8 years after your final period, the endocrine system stabilizes. While hot flashes typically subside, the focus shifts to long-term "somatic" health—protecting the brain, bones, and cardiovascular system.',
    },
}


NEURO_SYMPTOMS = {
    "3am_wakeup": "The 3 AM Wakeup: Feeling wide awake and anxious in the middle of the night.",
    "word_search": "The Word Search: Difficulty finding common words or losing your train of thought.",
    "short_fuse": "The Short Fuse: A new, intense irritability that feels chemical rather than situational.",
}


# ============================================================================
# Onboarding UI
# ============================================================================


def render_onboarding():
    """Render the SELENE onboarding screen."""

    st.markdown('<div class="selene-header">SELENE</div>', unsafe_allow_html=True)
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Header
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 40px;">
            <h2 style="color: #8DA4C2; font-size: 22px; font-weight: 400; 
                       letter-spacing: 2px; margin-bottom: 15px;">
                Finding Your Place on the Map
            </h2>
            <p style="color: #555; font-size: 16px; line-height: 1.7; 
                      max-width: 650px; margin: 0 auto; font-weight: 300;">
                Menopause is not a single event; it is a multi-year neuroendocrine 
                transition. To tailor your insights, we need to understand where your 
                system currently sits on the physiological timeline.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Stage selection
    st.markdown(
        '<div class="form-label">Please select the description that most closely aligns with your experience over the last 6 months:</div>',
        unsafe_allow_html=True,
    )

    stage_choice = st.radio(
        "Stage",
        options=list(STAGES.keys()),
        format_func=lambda x: STAGES[x]["title"],
        label_visibility="collapsed",
        key="stage_radio",
    )

    # Display details for selected stage
    if stage_choice:
        stage = STAGES[stage_choice]
        st.markdown(
            f"""
            <div style="background-color: #E8F0F8; border: 1px solid #d0dff0; 
                        border-radius: 15px; padding: 20px; margin: 20px 0;">
                <p style="color: #555; margin: 0 0 10px 0; font-size: 14px;">
                    <strong>Cycle Pattern:</strong> {stage["cycle"]}
                </p>
                <p style="color: #555; margin: 0; font-size: 14px;">
                    <strong>The Science:</strong> {stage["science"]}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Neuro-check section
    st.markdown(
        """
        <div style="text-align: center; margin: 40px 0 20px 0;">
            <h3 style="color: #8DA4C2; font-size: 16px; font-weight: 500; 
                       letter-spacing: 1.5px;">
                Optional: The "Neuro-Check"
            </h3>
            <p style="color: #777; font-size: 14px; margin-top: 10px;">
                Beyond your cycle, are you noticing "internal" shifts?
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Symptom checkboxes
    neuro_selected = []
    for key, label in NEURO_SYMPTOMS.items():
        if st.checkbox(label, key=f"neuro_{key}"):
            neuro_selected.append(key)

    st.markdown("<br><br>", unsafe_allow_html=True)

    # Save button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button(
            "Save Local Baseline & Continue",
            key="save_profile",
            use_container_width=True,
        ):
            profile = {
                "stage": stage_choice,
                "stage_title": STAGES[stage_choice]["title"],
                "neuro_symptoms": neuro_selected,
            }
            save_profile(profile)
            st.success("✓ Profile saved!")
            st.rerun()


# ============================================================================
# Helper: Get readable profile summary for LLM context
# ============================================================================


def get_profile_summary() -> str:
    """
    Returns a human-readable summary of the user's profile for injection
    into LLM prompts. This gives the model personalized context.
    """
    profile = load_profile()
    if not profile:
        return ""

    stage_key = profile.get("stage", "")
    stage_info = STAGES.get(stage_key, {})

    lines = [
        "USER PROFILE:",
        f"Stage: {profile.get('stage_title', 'Unknown')}",
        f"Cycle Pattern: {stage_info.get('cycle', 'N/A')}",
    ]

    neuro = profile.get("neuro_symptoms", [])
    if neuro:
        symptoms = [NEURO_SYMPTOMS[s].split(":")[0] for s in neuro]
        lines.append(f"Neuro Symptoms: {', '.join(symptoms)}")

    return "\n".join(lines)
