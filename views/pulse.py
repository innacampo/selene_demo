import streamlit as st
from navigation import render_header_with_back


def render_pulse():
    """Render the pulse logging page."""
    render_header_with_back("back_pulse")

    st.markdown('<div class="page-title">Pulse</div>', unsafe_allow_html=True)
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

    if st.button("Save Entry", use_container_width=True):
        # TODO: Save logic would go here
        st.success("Attune Captured.")
