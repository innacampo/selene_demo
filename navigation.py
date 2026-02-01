import streamlit as st


def go_to_page(page_name: str):
    """Navigate to a specific page."""
    st.session_state.page = page_name


def go_home():
    """Navigate back to home page."""
    st.session_state.page = "home"


def render_back_button(key: str):
    """Render a back button that returns to home."""
    if st.button("← Back", key=key):
        go_home()
        st.rerun()


def render_header_with_back(key: str):
    """Render header row with back button and SELENE title."""
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        render_back_button(key)

    with col2:
        st.markdown('<div class="selene-header">SELENE</div>', unsafe_allow_html=True)

    return col1, col2, col3
