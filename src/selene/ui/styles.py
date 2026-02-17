"""
Centralized Design System & CSS Injections.

Implements the SELENE aesthetic:
- Typography: Montserrat & Playfair Display
- Palette: HSL-tailored accents (#8DA4C2)
- Layout: Glassmorphic containers and sleek rounded interactions.
"""

import streamlit as st


def load_css():
    """Load all CSS styles for the application."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600&display=swap');

        :root {
            /* Palette */
            --bg-color: #FDFAFA;
            --text-primary: #4A4A4A;
            --text-secondary: #555555;
            --text-tertiary: #777777;
            --text-placeholder: #999999;
            --text-auth-header: #8DA4C2; /* User requested blue */
            
            --primary-accent: #8DA4C2;
            --primary-accent-hover: #2b3e57;
            
            --border-light: #EAEAEA;
            --white: #ffffff;
            
            --bot-msg-bg: #E8F0F8;
            --bot-msg-border: #d0dff0;
            --user-msg-bg: #ffffff;
            --user-msg-border: #EAEAEA;
            
            --github-bg: #24292e;
            --github-hover: #3a3f44;
            
            --font-main: 'Montserrat', sans-serif;
        }

        .stApp {
            background-color: var(--bg-color);
            font-family: var(--font-main);
        }

        header, footer {visibility: hidden;}

        .block-container {
            max-width: 800px;
            padding-top: 1rem;
        }

        /* Button styles */
        .stButton {
            display: flex !important;
            justify-content: center !important;
        }
        
        .stButton > button {
            background-color: var(--primary-accent) !important;
            color: var(--white) !important;
            border: none !important;
            border-radius: 50px !important;
            padding: 12px 32px !important;
            font-size: 15px !important;
            font-weight: 500 !important;
            font-family: var(--font-main) !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.06) !important;
            transition: all 0.25s ease !important;
            min-width: 180px !important;
            width: auto !important;
        }

        /* Target download buttons */
        .stDownloadButton button {
            background-color: var(--primary-accent) !important;
            color: var(--white) !important;
            border: none !important;
            border-radius: 50px !important;
            padding: 12px 32px !important;
            font-size: 15px !important;
            font-weight: 500 !important;
            font-family: var(--font-main) !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.06) !important;
            transition: all 0.25s ease !important;
            min-width: 180px !important;
            width: auto !important;
        }

        .stButton > button:hover {
            background-color: var(--primary-accent-hover) !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 10px rgba(0,0,0,0.08) !important;
        }

        div.stButton > button:first-child:hover, .stDownloadButton button:hover {
            background-color: var(--primary-accent-hover) !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 10px rgba(0,0,0,0.08) !important;
        }

        /* Typography */
        .selene-header {
            text-align: center;
            font-size: 26px;
            letter-spacing: 5px;
            color: var(--text-primary);
            margin-bottom: 50px;
            font-weight: 400;
            text-transform: uppercase;
        }

        .page-title {
            text-align: center;
            font-size: 18px;
            letter-spacing: 3px;
            color: var(--text-auth-header);
            margin-bottom: 30px;
            font-weight: 400;
            text-transform: uppercase;
        }

        .divider {
            border-bottom: 1px solid var(--border-light);
            margin-bottom: 50px;
        }

        .selene-sub-header {
            font-size: 14px;
            letter-spacing: 1px;
            color: var(--primary-accent);
            text-transform: uppercase;
            font-weight: 600;
            margin-bottom: 25px;
        }

        .italic-note {
            text-align: center;
            font-size: 14px;
            color: var(--text-placeholder);
            font-style: italic;
            font-family: serif;
            margin-bottom: 30px;
        }

        .main-message {
            text-align: center;
            font-size: 18px;
            color: var(--text-secondary);
            font-weight: 300;
            line-height: 1.5;
            margin-bottom: 40px;
        }

        /* Demo notice styles */
        .demo-notice {
            background: linear-gradient(135deg, #f8f9fa 0%, #fff 100%);
            border: 1px solid var(--border-light);
            border-radius: 10px;
            padding: 15px 20px;
            margin-top: 10px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.03);
        }

        .demo-badge {
            display: inline-block;
            background-color: var(--primary-accent);
            color: var(--white);
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 2px;
            padding: 4px 12px;
            border-radius: 10px;
            margin-bottom: 10px;
        }

        .demo-notice p {
            color: #666;
            font-size: 14px;
            line-height: 1.6;
            margin-bottom: 10px;
        }

        .github-link {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background-color: var(--github-bg);
            color: var(--white) !important;
            padding: 12px 24px;
            border-radius: 50px;
            text-decoration: none;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.25s ease;
        }

        .github-link:hover {
            background-color: var(--github-hover);
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }

        /* Chat styles */
        .chat-container {
            background-color: var(--white);
            border-radius: 10px;
            padding: 10px;
            margin: 10px 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            min-height: 300px;
            max-height: 400px;
            overflow-y: auto;
        }

        .chat-message {
            padding: 12px 18px;
            border-radius: 18px;
            margin: 6px 0;
            max-width: 80%;
            font-size: 14px;
            line-height: 1.5;
        }

        .user-message {
            background-color: var(--primary-accent);
            color: var(--white);
            margin-left: auto;
            text-align: right;
        }

        .bot-message {
            background-color: var(--border-light);
            color: var(--text-primary);
            margin-right: auto;
        }

        /* Streamlit native chat message styling - default */
        [data-testid="stChatMessage"] {
            border-radius: 25px !important;
            padding: 16px 20px !important;
            margin: 8px 0 !important;
            font-family: var(--font-main) !important;
        }

        [data-testid="stChatMessage"] p {
            font-family: var(--font-main) !important;
            color: var(--text-primary) !important;
            line-height: 1.6 !important;
        }

        /* Hide default avatar icons */
        [data-testid="stChatMessage"] [data-testid="stChatMessageAvatarUser"],
        [data-testid="stChatMessage"] [data-testid="stChatMessageAvatarAssistant"] {
            display: none !important;
        }

        /* Assistant message styling */
        .stChatMessage:has([data-testid="stChatMessageAvatarAssistant"]),
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
            background-color: var(--bot-msg-bg) !important;
            border: 1px solid var(--bot-msg-border) !important;
        }

        /* User message styling */
        .stChatMessage:has([data-testid="stChatMessageAvatarUser"]),
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
            background-color: var(--user-msg-bg) !important;
            border: 1px solid var(--user-msg-border) !important;
        }

        /* Info box styling */
        [data-testid="stAlert"] {
            background-color: var(--bot-msg-bg) !important;
            border: 1px solid var(--bot-msg-border) !important;
            border-radius: 25px !important;
            padding: 16px 20px !important;
            font-family: var(--font-main) !important;
        }

        /* Remove all inner container styling */
        [data-testid="stAlert"] > div,
        [data-testid="stAlert"] [class*="AlertContent"],
        [data-testid="stAlert"] [class*="st-emotion-cache"] {
            background-color: transparent !important;
            border: none !important;
            padding: 0 !important;
            margin: 0 !important;
        }

        [data-testid="stAlert"] p,
        [data-testid="stAlert"] div,
        [data-testid="stAlert"] span {
            font-family: var(--font-main) !important;
            color: var(--text-primary) !important;
            line-height: 1.6 !important;
            background-color: transparent !important;
            border: none !important;
        }

        /* Hide default info icon */
        [data-testid="stAlert"] svg {
            display: none !important;
        }

        /* ============================================
           CHAT INPUT STYLING - NO INNER BORDER
           ============================================ */
        
        /* Chat input - full width to match messages */
        [data-testid="stChatInput"] {
            max-width: 100% !important;
            width: 100% !important;
        }

        [data-testid="stChatInput"] > div {
            max-width: 100% !important;
            width: 100% !important;
            border-radius: 25px !important;
            border: 1px solid var(--border-light) !important;
            background-color: var(--white) !important;
        }

        /* Remove inner border/outline from chat input */
        [data-testid="stChatInput"] textarea,
        [data-testid="stChatInput"] input {
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
            font-family: var(--font-main) !important;
        }

        [data-testid="stChatInput"] [data-baseweb="base-input"],
        [data-testid="stChatInput"] [data-baseweb="input"],
        [data-testid="stChatInput"] [data-baseweb="textarea"] {
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
            background-color: transparent !important;
        }

        [data-testid="stChatInput"] > div > div {
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
        }

        /* Chat input focus state - only outer border changes */
        [data-testid="stChatInput"] > div:focus-within {
            border-color: var(--primary-accent) !important;
            box-shadow: 0 0 0 1px var(--primary-accent) !important;
        }

        [data-testid="stChatInput"] > div:focus-within textarea,
        [data-testid="stChatInput"] > div:focus-within input,
        [data-testid="stChatInput"] > div:focus-within [data-baseweb="base-input"],
        [data-testid="stChatInput"] > div:focus-within [data-baseweb="input"],
        [data-testid="stChatInput"] > div:focus-within [data-baseweb="textarea"] {
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
        }

        /* Chat input send button */
        [data-testid="stChatInput"] button,
        [data-testid="stChatInput"] button:hover,
        [data-testid="stChatInput"] button:focus,
        [data-testid="stChatInput"] button:active {
            background-color: var(--primary-accent) !important;
            border-color: var(--primary-accent) !important;
            border: none !important;
            outline: none !important;
        }


        /* Summary card styles */
        .summary-card {
            background-color: var(--white);
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }

        .summary-title {
            font-size: 14px;
            letter-spacing: 1px;
            color: var(--primary-accent);
            text-transform: uppercase;
            font-weight: 600;
            margin-bottom: 10px;
        }

        .summary-content {
            font-size: 14px;
            color: var(--text-secondary);
            line-height: 1.6;
        }

        /* Form label */
        .form-label {
            font-size: 12px;
            letter-spacing: 1px;
            color: var(--text-tertiary);
            text-transform: uppercase;
            font-weight: 600;
            margin-bottom: 10px;
            margin-top: 10px;
        }

        /* Hide Streamlit elements */
        div[data-testid="stToolbar"] {visibility: hidden;}
        div[data-testid="stDecoration"] {visibility: hidden;}
        #MainMenu {visibility: hidden;}

        /* Style inputs */
        .stTextInput > div > div > input {
            border-radius: 25px !important;
            border: 1px solid var(--border-light) !important;
            padding: 12px 18px !important;
            font-family: var(--font-main) !important;
        }

        /* ============================================
           PULSE VIEW SPECIFIC STYLES
           ============================================ */
        
        /* Segmented Control Styling */
        [data-testid="stSegmentedControl"] {
            border: none !important;
            background-color: transparent !important;
        }

        [data-testid="stSegmentedControl"] > div {
            background-color: #ffffff !important;
            border: 1px solid var(--border-light) !important;
            border-radius: 12px !important;
            padding: 5px !important;
            gap: 5px !important;
        }

        /* Individual segments */
        [data-testid="stSegmentedControl"] button {
            border: 1px solid var(--border-light) !important;
            color: var(--text-tertiary) !important; 
            border-radius: 8px !important;
            font-family: var(--font-main) !important;
            font-weight: 500 !important;
            transition: all 0.3s ease !important;
            background-color: var(--white) !important;
        }

        [data-testid="stSegmentedControl"] button:hover:not([data-selected="true"]) {
            background-color: #f8f9fa !important;
        }
        
        </style>

        """,
        unsafe_allow_html=True,
    )
