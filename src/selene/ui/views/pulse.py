"""
Daily Attune (Pulse) View.

The primary data-entry portal for daily symptom logging.
Captures metrics across three core neuroendocrine pillars:
1. Rest (Sleep quality and patterns)
2. Internal Weather (Hot flash intensity)
3. Clarity (Cognitive state and fog)
"""

import streamlit as st
from selene.ui.navigation import render_header_with_back
from selene.storage.data_manager import save_pulse_entry


def render_pulse():
    """Render the pulse logging page."""
    render_header_with_back("back_pulse")

    st.markdown('<div class="page-title">Daily Attune</div>', unsafe_allow_html=True)
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # PILLAR 1: REST
    with st.container(border=True):
        st.markdown('<div class="selene-sub-header">Rest</div>', unsafe_allow_html=True)
        rest_option = st.segmented_control(
            "How was your sleep?",
            ["3 AM Awakening", "Fragmented", "Restorative"],
            selection_mode="single",
            label_visibility="visible",
        )

    # PILLAR 2: CLIMATE
    with st.container(border=True):
        st.markdown(
            '<div class="selene-sub-header">Internal Weather</div>',
            unsafe_allow_html=True,
        )
        # Using a selectbox or segmented control instead of a slider for 'Climate'
        climate_level = st.segmented_control(
            "Intensity of Hot Flashes", options=["Cool", "Warm", "Flashing", "Heavy"]
        )

    # PILLAR 3: CLARITY
    with st.container(border=True):
        st.markdown(
            '<div class="selene-sub-header">Clarity</div>', unsafe_allow_html=True
        )
        clarity_level = st.segmented_control(
            "Mental State",
            ["Brain Fog", "Neutral", "Focused"],
            selection_mode="single",
            label_visibility="visible",
        )

    # MIND DUMP
    st.markdown('<div class="selene-sub-header">Notes</div>', unsafe_allow_html=True)
    # Using markdown for header to apply Playfair font style

    notes = st.text_area(
        "Any additional symptoms or observations...",
        placeholder="e.g., unusual irritability at lunch...",
        label_visibility="visible",
    )

    if st.button("Save", use_container_width=True):
        if not rest_option or not climate_level or not clarity_level:
            st.warning("Please select an option for all three pillars.")
        else:
            entry = {
                "rest": rest_option,
                "climate": climate_level,
                "clarity": clarity_level,
                "notes": notes,
            }
            save_pulse_entry(entry)
            st.success("Daily Attune Captured.")
