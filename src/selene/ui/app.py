"""
SELENE Main Application Entry Point.

This script initializes the Streamlit application, configures the environment, 
and handles top-level routing between the home dashboard, chat interface, 
pulse tracking, and clinical reports. It also manages the initial 
user onboarding workflow.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from selene import settings
import streamlit as st


@st.cache_resource
def _setup_logging():
    """Configure root logger once — cached to avoid duplicate handlers on rerun."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.DEBUG))

    formatter = logging.Formatter(settings.LOG_FORMAT, datefmt=settings.LOG_DATEFMT)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.DEBUG))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Optional rotating file handler
    if settings.LOG_TO_FILE:
        log_path = Path(settings.LOG_FILE_PATH)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            str(log_path), maxBytes=settings.LOG_MAX_BYTES, backupCount=settings.LOG_BACKUP_COUNT
        )
        file_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.DEBUG))
        file_handler.setFormatter(formatter)

        root_logger.addHandler(file_handler)
        root_logger.info(f"File logging enabled: {log_path} (maxBytes={settings.LOG_MAX_BYTES}, backups={settings.LOG_BACKUP_COUNT})")

    # Reduce noisiness from watchdog internals
    try:
        logging.getLogger("watchdog").setLevel(logging.WARNING)
        logging.getLogger("watchdog.observers").setLevel(logging.WARNING)
        logging.getLogger("watchdog.events").setLevel(logging.WARNING)
    except Exception:
        pass

    return root_logger


_setup_logging()

from selene.config import init_page_config, init_session_state
from selene.ui.styles import load_css
from selene.ui.views import render_home, render_chat, render_clinical, render_pulse
from selene.ui.onboarding import render_onboarding


# ----------------------------
# Page Router
# ----------------------------
PAGE_ROUTES = {
    "home": render_home,
    "chat": render_chat,
    "clinical": render_clinical,
    "pulse": render_pulse,
}


def main() -> None:
    """
    Primary application loop.
    
    Coordinates:
    - Onboarding check: redirects to onboarding if profile is incomplete.
    - Page routing: renders the active view based on session state.
    - Fallback logic: ensures users are returned to 'home' if state is corrupted.
    
    init_page_config, init_session_state, and load_css are called here
    (not at module level) because Streamlit re-executes the entry script
    on every interaction but only imports this module once. Placing them
    inside main() guarantees they run on every rerun cycle.
    """
    init_page_config()
    init_session_state()
    load_css()

    # Check if onboarding is complete
    if not st.session_state.get("onboarding_complete", False):
        render_onboarding()
        return
    
    # Normal app flow
    current_page = st.session_state.get("page", "home")

    if current_page in PAGE_ROUTES:
        PAGE_ROUTES[current_page]()
    else:
        # Fallback to home if unknown page
        render_home()


if __name__ == "__main__":
    main()
