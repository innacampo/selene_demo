import streamlit as st


def init_page_config():
    """Initialize Streamlit page configuration."""
    st.set_page_config(page_title="SELENE", layout="centered")


def init_session_state():
    """Initialize session state variables."""
    if "page" not in st.session_state:
        st.session_state.page = "home"

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
