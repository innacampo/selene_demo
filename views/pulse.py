import streamlit as st
from navigation import render_header_with_back


def render_pulse():
    """Render the pulse logging page."""
    render_header_with_back("back_pulse")

    st.markdown(
        '<div class="page-title">Log Today\'s Pulse</div>', unsafe_allow_html=True
    )
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Sleep quality
    st.markdown(
        '<div class="form-label">How did you sleep last night?</div>',
        unsafe_allow_html=True,
    )
    sleep_quality = st.select_slider(
        "Sleep",
        options=["Poor", "Fair", "Good", "Excellent"],
        value="Fair",
        label_visibility="collapsed",
    )

    # Energy level
    st.markdown('<div class="form-label">Energy Level</div>', unsafe_allow_html=True)
    energy = st.select_slider(
        "Energy",
        options=["Very Low", "Low", "Moderate", "High", "Very High"],
        value="Moderate",
        label_visibility="collapsed",
    )

    # Mood
    st.markdown('<div class="form-label">Mood</div>', unsafe_allow_html=True)
    mood = st.select_slider(
        "Mood",
        options=["😢", "😕", "😐", "🙂", "😊"],
        value="😐",
        label_visibility="collapsed",
    )

    # Hot flashes
    st.markdown(
        '<div class="form-label">Hot Flashes Today</div>', unsafe_allow_html=True
    )
    hot_flashes = st.number_input(
        "Hot Flashes", min_value=0, max_value=20, value=0, label_visibility="collapsed"
    )

    # Notes
    st.markdown(
        '<div class="form-label">Notes (Optional)</div>', unsafe_allow_html=True
    )
    notes = st.text_area(
        "Notes",
        placeholder="Any additional symptoms or observations...",
        label_visibility="collapsed",
    )

    # Save button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("Save Entry", key="save_pulse", use_container_width=True):
            # TODO: Save data to database/storage
            st.success("Today's pulse logged successfully!")
