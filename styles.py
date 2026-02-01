import streamlit as st


def load_css():
    """Load all CSS styles for the application."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600&display=swap');

        .stApp {
            background-color: #FDFAFA;
            font-family: 'Montserrat', sans-serif;
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
            background-color: #8DA4C2 !important;
            color: white !important;
            border: none !important;
            border-radius: 50px !important;
            padding: 12px 32px !important;
            font-size: 15px !important;
            font-weight: 500 !important;
            font-family: 'Montserrat', sans-serif !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.06) !important;
            transition: all 0.25s ease !important;
            min-width: 180px !important;
            width: auto !important;
        }

        .stButton > button:hover {
            background-color: #7a93b3 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 10px rgba(0,0,0,0.08) !important;
        }

        /* Typography */
        .selene-header {
            text-align: center;
            font-size: 26px;
            letter-spacing: 5px;
            color: #4A4A4A;
            margin-bottom: 30px;
            font-weight: 400;
            text-transform: uppercase;
        }

        .page-title {
            text-align: center;
            font-size: 18px;
            letter-spacing: 3px;
            color: #4A4A4A;
            margin-bottom: 30px;
            font-weight: 400;
            text-transform: uppercase;
        }

        .divider {
            border-bottom: 1px solid #EAEAEA;
            margin-bottom: 30px;
        }

        .sub-header {
            text-align: center;
            font-size: 11px;
            letter-spacing: 1.5px;
            color: #777;
            text-transform: uppercase;
            font-weight: 600;
            margin-top: 20px;
        }

        .italic-note {
            text-align: center;
            font-size: 14px;
            color: #999;
            font-style: italic;
            font-family: serif;
            margin-bottom: 20px;
        }

        .main-message {
            text-align: center;
            font-size: 18px;
            color: #555;
            font-weight: 300;
            line-height: 1.5;
            margin-bottom: 20px;
        }

        /* Demo notice styles */
        .demo-notice {
            background: linear-gradient(135deg, #f8f9fa 0%, #fff 100%);
            border: 1px solid #EAEAEA;
            border-radius: 10px;
            padding: 15px 20px;
            margin-top: 10px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.03);
        }

        .demo-badge {
            display: inline-block;
            background-color: #8DA4C2;
            color: white;
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
            background-color: #24292e;
            color: white !important;
            padding: 12px 24px;
            border-radius: 50px;
            text-decoration: none;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.25s ease;
        }

        .github-link:hover {
            background-color: #3a3f44;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }

        /* Chat styles */
        .chat-container {
            background-color: #fff;
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
            background-color: #8DA4C2;
            color: white;
            margin-left: auto;
            text-align: right;
        }

        .bot-message {
            background-color: #EAEAEA;
            color: #4A4A4A;
            margin-right: auto;
        }

        /* Streamlit native chat message styling - default */
        [data-testid="stChatMessage"] {
            border-radius: 25px !important;
            padding: 16px 20px !important;
            margin: 8px 0 !important;
            font-family: 'Montserrat', sans-serif !important;
        }

        [data-testid="stChatMessage"] p {
            font-family: 'Montserrat', sans-serif !important;
            color: #4A4A4A !important;
            line-height: 1.6 !important;
        }

        /* Hide default avatar icons */
        [data-testid="stChatMessage"] [data-testid="stChatMessageAvatarUser"],
        [data-testid="stChatMessage"] [data-testid="stChatMessageAvatarAssistant"] {
            display: none !important;
        }

        /* Assistant message styling - lightest blue */
        .stChatMessage:has([data-testid="stChatMessageAvatarAssistant"]),
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
            background-color: #E8F0F8 !important;
            border: 1px solid #d0dff0 !important;
        }

        /* User message styling - WHITE background - MUST be last to override */
        .stChatMessage:has([data-testid="stChatMessageAvatarUser"]),
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
            background-color: #ffffff !important;
            border: 1px solid #EAEAEA !important;
        }

        /* Info box styling - remove all nested containers and borders */
        [data-testid="stAlert"] {
            background-color: #E8F0F8 !important;
            border: 1px solid #d0dff0 !important;
            border-radius: 25px !important;
            padding: 16px 20px !important;
            font-family: 'Montserrat', sans-serif !important;
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
            font-family: 'Montserrat', sans-serif !important;
            color: #4A4A4A !important;
            line-height: 1.6 !important;
            background-color: transparent !important;
            border: none !important;
        }

        /* Hide default info icon */
        [data-testid="stAlert"] svg {
            display: none !important;
        }

        /* Chat input - full width to match messages */
        [data-testid="stChatInput"] {
            max-width: 100% !important;
            width: 100% !important;
        }

        [data-testid="stChatInput"] > div {
            max-width: 100% !important;
            width: 100% !important;
        }

        /* Chat input send button - prevent red */
        [data-testid="stChatInput"] button,
        [data-testid="stChatInput"] button:hover,
        [data-testid="stChatInput"] button:focus,
        [data-testid="stChatInput"] button:active {
            background-color: #8DA4C2 !important;
            border-color: #8DA4C2 !important;
        }

        /* Hide status/spinner messages */
        [data-testid="stStatusWidget"],
        .stSpinner,
        [data-testid="stCacheSpinner"] {
            display: none !important;
        }

        /* Summary card styles */
        .summary-card {
            background-color: #fff;
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }

        .summary-title {
            font-size: 14px;
            letter-spacing: 1px;
            color: #8DA4C2;
            text-transform: uppercase;
            font-weight: 600;
            margin-bottom: 10px;
        }

        .summary-content {
            font-size: 14px;
            color: #555;
            line-height: 1.6;
        }

        /* Form label */
        .form-label {
            font-size: 12px;
            letter-spacing: 1px;
            color: #777;
            text-transform: uppercase;
            font-weight: 600;
            margin-bottom: 10px;
            margin-top: 10px;
        }

        /* Hide Streamlit elements */
        div[data-testid="stToolbar"] {visibility: hidden;}
        div[data-testid="stDecoration"] {visibility: hidden;}
        div[data-testid="stStatusWidget"] {visibility: hidden;}
        #MainMenu {visibility: hidden;}

        /* Style inputs */
        .stTextInput > div > div > input {
            border-radius: 25px !important;
            border: 1px solid #EAEAEA !important;
            padding: 12px 18px !important;
            font-family: 'Montserrat', sans-serif !important;
        }

        /* Chat input styling */
        .stChatInput > div {
            border-radius: 25px !important;
            border: 1px solid #EAEAEA !important;
        }

        .stChatInput textarea {
            font-family: 'Montserrat', sans-serif !important;
        }

        .stChatInput > div:focus-within {
            border-color: #8DA4C2 !important;
            box-shadow: 0 0 0 1px #8DA4C2 !important;
        }

        /* Remove red outline from all inputs */
        *:focus {
            outline: none !important;
        }

        textarea:focus, input:focus {
            border-color: #8DA4C2 !important;
            box-shadow: none !important;
        }
        
        </style>
        """,
        unsafe_allow_html=True,
    )
