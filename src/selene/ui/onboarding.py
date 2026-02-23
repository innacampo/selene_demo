"""
User Onboarding & Baseline Profiling.

Handles the initial user journey:
1. Stage Mapping: Helping the user identify where they sit on the transition timeline.
2. Neuro-Check: Capturing baseline cognitive and behavioral traits.
3. Persistence: Saving the foundational 'User Profile' for lifelong context injection.
"""

import json
import logging
from datetime import datetime

import streamlit as st

from selene import settings

logger = logging.getLogger(__name__)


# ============================================================================
# Profile Storage
# ============================================================================

PROFILE_PATH = settings.PROFILE_PATH


def save_profile(profile_data: dict):
    """Save user profile to JSON file."""
    logger.debug(f"save_profile: ENTER profile_keys={list(profile_data.keys())}")
    profile_data["created_at"] = datetime.now().isoformat()
    profile_data["last_updated"] = datetime.now().isoformat()

    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(profile_data, f, indent=2)

    # Also store in session state for runtime access
    st.session_state.user_profile = profile_data
    st.session_state.onboarding_complete = True

    # Invalidate user context cache so new profile is used immediately
    from selene.core.med_logic import invalidate_user_context_cache

    invalidate_user_context_cache()
    logger.info("save_profile: Profile saved and user context cache invalidated")


def load_profile() -> dict | None:
    """Load user profile from JSON file."""
    logger.debug("load_profile: ENTER")
    if PROFILE_PATH.exists():
        try:
            with open(PROFILE_PATH, encoding="utf-8") as f:
                profile = json.load(f)
                logger.debug(f"load_profile: loaded profile keys={list(profile.keys())}")
                return profile
        except Exception as e:
            logger.warning(f"load_profile: failed to read profile file: {e}")
            return None
    logger.debug("load_profile: profile file not found")
    return None


def profile_exists() -> bool:
    """Check if user has completed onboarding."""
    exists = PROFILE_PATH.exists()
    logger.debug(f"profile_exists: {exists}")
    return exists


# ============================================================================
# Stage Definitions
# ============================================================================


@st.cache_data(show_spinner=False)
def _load_stages_metadata() -> dict:
    """Load stage definitions from the centralized metadata file (cached)."""
    try:
        with open(settings.STAGES_METADATA_PATH, encoding="utf-8") as f:
            data = json.load(f)
            logger.debug(f"_load_stages_metadata: loaded {len(data.get('stages', {}))} stages")
            return data.get("stages", {})
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"_load_stages_metadata: failed to load stages metadata: {e}")
        return {}


from selene.constants import NEURO_SYMPTOM_DESCRIPTIONS as NEURO_SYMPTOMS  # noqa: E402

# ============================================================================
# Onboarding UI
# ============================================================================


def render_onboarding() -> None:
    """
    Render the multi-step onboarding UI.

    This view collects the essential 'Baseline' data needed to personalize
    the insight engine. It guides users through an educational stage-selection
    process and an optional neuro-symptom audit.
    """

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

    stages_metadata = _load_stages_metadata()
    stage_choice = st.radio(
        "Stage",
        options=list(stages_metadata.keys()),
        format_func=lambda x: stages_metadata[x]["title"],
        label_visibility="collapsed",
        key="stage_radio",
    )

    # Display details for selected stage
    if stage_choice:
        stage = stages_metadata[stage_choice]
        st.markdown(
            f"""
            <div style="background-color: #E8F0F8; border: 1px solid #d0dff0;
                        border-radius: 15px; padding: 20px; margin: 20px 0;">
                <p style="color: #555; margin: 0 0 10px 0; font-size: 14px;">
                    <strong>Cycle Pattern:</strong> {stage.get("cycle_description", "N/A")}
                </p>
                <p style="color: #555; margin: 0; font-size: 14px;">
                    <strong>The Science:</strong> {stage.get("neuro_science", "N/A")}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # st.markdown("<br>", unsafe_allow_html=True)

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

    st.markdown("<br>", unsafe_allow_html=True)

    # Save button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button(
            "Continue",
            key="save_profile",
            use_container_width=True,
        ):
            logger.debug("render_onboarding: Save button clicked")
            profile = {
                "stage": stage_choice,
                "stage_title": stages_metadata[stage_choice]["title"],
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

    stages_metadata = _load_stages_metadata()
    stage_key = profile.get("stage", "")
    stage_info = stages_metadata.get(stage_key, {})

    lines = [
        "USER PROFILE:",
        f"Stage: {profile.get('stage_title', 'Unknown')}",
        f"Cycle Pattern: {stage_info.get('cycle_description', 'N/A')}",
    ]

    neuro = profile.get("neuro_symptoms", [])
    if neuro:
        symptoms = [NEURO_SYMPTOMS.get(s, s).split(":")[0] for s in neuro]
        lines.append(f"Neuro Symptoms: {', '.join(symptoms)}")

    return "\n".join(lines)
