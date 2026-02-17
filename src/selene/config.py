"""
Global Configuration & State Management.

Handles Streamlit page setup and initializes the persistent session state.
Syncs local profile data with runtime state to ensure cross-view consistency.
"""

import logging
import streamlit as st
import json

from selene import settings


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
        if settings.PROFILE_PATH.exists():
            try:
                with open(settings.PROFILE_PATH, "r", encoding="utf-8") as f:
                    st.session_state.user_profile = json.load(f)
                st.session_state.onboarding_complete = True
            except (json.JSONDecodeError, IOError) as e:
                logging.getLogger(__name__).warning(
                    f"Corrupted profile, restarting onboarding: {e}"
                )
                st.session_state.onboarding_complete = False
        else:
            st.session_state.onboarding_complete = False
