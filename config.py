import streamlit as st
from pathlib import Path
import json


def init_page_config():
    """Initialize Streamlit page configuration."""
    st.set_page_config(page_title="SELENE", layout="centered")


def init_session_state():
    """Initialize session state variables."""
    if "page" not in st.session_state:
        st.session_state.page = "home"

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Check if onboarding is complete
    if "onboarding_complete" not in st.session_state:
        profile_path = Path("user_data/user_profile.json")
        if profile_path.exists():
            # Load existing profile into session state
            with open(profile_path, "r") as f:
                st.session_state.user_profile = json.load(f)
            st.session_state.onboarding_complete = True
        else:
            st.session_state.onboarding_complete = False
