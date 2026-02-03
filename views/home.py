import streamlit as st
from navigation import go_to_page
import json


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

    # Middle text
    # Load stage data
    try:
        with open("metadata/stages.json", "r") as f:
            stages_data = json.load(f)
    except Exception as e:
        st.error(f"Error loading stages data: {e}")
        stages_data = {"stages": {}}

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

    st.markdown(
        f'<div class="selene-sub-header" style="text-align: center;">{ui_markup["sub_header"]}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="italic-note">{ui_markup["italic_note"]}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="main-message">{ui_markup["main_message"]}</div>',
        unsafe_allow_html=True,
    )

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
