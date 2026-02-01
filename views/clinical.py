import streamlit as st
from navigation import render_header_with_back


SUMMARY_CARDS = [
    {
        "title": "Current Stage",
        "content": """
            <strong>Late Perimenopause</strong><br>
            Based on your symptom patterns and cycle history, you appear to be in 
            the late transition phase of perimenopause.
        """,
    },
    {
        "title": "Key Symptoms Tracked",
        "content": """
            • Sleep disruptions: 4-5 nights/week<br>
            • Hot flashes: 2-3 per day<br>
            • Mood changes: Moderate variability<br>
            • Energy levels: Low to moderate
        """,
    },
    {
        "title": "Recommendations",
        "content": """
            • Consider discussing HRT options with your healthcare provider<br>
            • Maintain sleep hygiene practices<br>
            • Continue tracking symptoms for pattern recognition<br>
            • Schedule routine health screenings
        """,
    },
]


def _render_summary_card(title: str, content: str):
    """Render a single summary card."""
    st.markdown(
        f"""
        <div class="summary-card">
            <div class="summary-title">{title}</div>
            <div class="summary-content">{content}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_clinical():
    """Render the clinical summary page."""
    render_header_with_back("back_clinical")

    st.markdown(
        '<div class="page-title">Clinical Summary</div>', unsafe_allow_html=True
    )
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Render all summary cards
    for card in SUMMARY_CARDS:
        _render_summary_card(card["title"], card["content"])

    # Export button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("Export for Doctor", key="export", use_container_width=True):
            st.success("Summary exported successfully!")
