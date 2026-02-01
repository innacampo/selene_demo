import streamlit as st
from navigation import go_to_page


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
    st.markdown(
        '<div class="sub-header">LATE TRANSITION • HIGH VARIABILITY</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="italic-note">Fluctuations expected</div>', unsafe_allow_html=True
    )
    st.markdown(
        '<div class="main-message">'
        "Sleep disruptions are common as estrogen levels<br>"
        "fluctuate during this stage."
        "</div>",
        unsafe_allow_html=True,
    )

    # Bottom button
    left, center, right = st.columns([1.45, 1, 1.45])
    with center:
        if st.button("Log Today's Pulse", key="btn_pulse"):
            go_to_page("pulse")
            st.rerun()

    # Demo notice
    st.markdown(
        """
        <div class="demo-notice">
            <p>
                This is a working prototype demonstrating SELENE architecture.
                <br>
            </p>
            <a href="https://github.com/innacampo/selene" 
               class="github-link" 
               target="_blank">
                <span>View on GitHub</span>
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )
