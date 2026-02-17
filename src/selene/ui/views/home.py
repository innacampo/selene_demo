"""
Home Dashboard View.

The landing interface for SELENE. It dynamically adapts its messaging 
and layout based on the user's identified menopause stage and profile.
"""

import json
from html import escape as html_escape

import streamlit as st

from selene import settings
from selene.ui.navigation import go_to_page


@st.cache_data(show_spinner=False)
def _load_stages_data() -> dict:
    """Load stages metadata from JSON file (cached)."""
    try:
        with open(settings.STAGES_METADATA_PATH) as f:
            return json.load(f)
    except Exception:
        return {"stages": {}}


def render_home():
    """Render the home page."""
    st.markdown('<div class="selene-header">SELENE</div>', unsafe_allow_html=True)
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Top buttons - centered and close together
    left_spacer, btn1, btn2, right_spacer = st.columns([1.2, 1.4, 1.4, 1.2])

    with btn1:
        if st.button("Chat with Selene", key="btn_chat"):
            go_to_page("chat")
            st.rerun()

    with btn2:
        if st.button("Clinical Summary", key="btn_clinical"):
            go_to_page("clinical")
            st.rerun()

    st.write("")
    st.write("")

    # Middle text
    stages_data = _load_stages_data()

    # Get user's current stage
    user_profile = st.session_state.get("user_profile", {})
    current_stage = user_profile.get("stage", "late_transition")

    # Get markup for this stage
    stage_info = stages_data["stages"].get(current_stage, {})
    ui_markup = stage_info.get(
        "ui_markup",
        {
            "sub_header": "LATE TRANSITION • HIGH VARIABILITY",
            "italic_note": "Fluctuations expected",
            "main_message": "Sleep disruptions are common as estrogen levels<br>fluctuate during this stage.",
        },
    )

    safe_sub = html_escape(ui_markup["sub_header"])
    safe_italic = html_escape(ui_markup["italic_note"])
    # Allow only <br> tags from stages.json; escape everything else
    safe_main = html_escape(ui_markup["main_message"]).replace("&lt;br&gt;", "<br>")

    st.markdown(
        f'<div class="selene-sub-header" style="text-align: center;">{safe_sub}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="italic-note">{safe_italic}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="main-message">{safe_main}</div>',
        unsafe_allow_html=True,
    )

    st.write("")
    st.write("")

    # Bottom button
    left, center, right = st.columns([1.45, 1, 1.45])
    with center:
        if st.button("Daily Attune", key="btn_pulse"):
            go_to_page("pulse")
            st.rerun()

    # # Demo notice
    # st.markdown(
    #     """
    #     <div class="demo-notice">
    #         <p>
    #             This is a working prototype demonstrating SELENE architecture.
    #             <br>
    #         </p>
    #         <a href="https://github.com/innacampo/selene"
    #            class="github-link"
    #            target="_blank">
    #             <span>View on GitHub</span>
    #         </a>
    #     </div>
    #     """,
    #     unsafe_allow_html=True,
    # )
