import streamlit as st

from config import init_page_config, init_session_state
from styles import load_css
from views import render_home, render_chat, render_clinical, render_pulse


# ----------------------------
# Initialize App
# ----------------------------
init_page_config()
init_session_state()
load_css()


# ----------------------------
# Page Router
# ----------------------------
PAGE_ROUTES = {
    "home": render_home,
    "chat": render_chat,
    "clinical": render_clinical,
    "pulse": render_pulse,
}


def main():
    """Main application entry point."""
    current_page = st.session_state.page

    if current_page in PAGE_ROUTES:
        PAGE_ROUTES[current_page]()
    else:
        # Fallback to home if unknown page
        render_home()


if __name__ == "__main__":
    main()
