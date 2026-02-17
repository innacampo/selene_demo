"""
SELENE — Streamlit entry point.

Usage: streamlit run app.py

All application logic lives in src/selene/.
This thin wrapper delegates to the internal UI module.
"""

from selene.ui.app import main

main()
