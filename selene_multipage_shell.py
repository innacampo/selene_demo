import streamlit as st

# ----------------------------
# Page config
# ----------------------------
st.set_page_config(page_title="SELENE", layout="centered")

# ----------------------------
# Session state for navigation
# ----------------------------
if "page" not in st.session_state:
    st.session_state.page = "home"

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


# ----------------------------
# CSS (shared across all pages)
# ----------------------------
def load_css():
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
            margin-bottom: 20px;
            font-weight: 400;
            text-transform: uppercase;
        }

        .page-title {
            text-align: center;
            font-size: 18px;
            letter-spacing: 3px;
            color: #4A4A4A;
            margin-bottom: 10px;
            font-weight: 400;
            text-transform: uppercase;
        }

        .divider {
            border-bottom: 1px solid #EAEAEA;
            margin-bottom: 20px;
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
            margin-top: 20px;
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
            border-radius: 20px;
            margin-bottom: 15px;
        }

        .demo-notice p {
            color: #666;
            font-size: 14px;
            line-height: 1.6;
            margin-bottom: 20px;
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
            margin-bottom: 15px;
            margin-top: 15px;
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

        .stTextArea > div > div > textarea {
            border-radius: 15px !important;
            border: 1px solid #EAEAEA !important;
            font-family: 'Montserrat', sans-serif !important;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


# ----------------------------
# Navigation functions
# ----------------------------
def go_to_page(page_name):
    st.session_state.page = page_name


def go_home():
    st.session_state.page = "home"


# ----------------------------
# Page: Home
# ----------------------------
def render_home():
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
            <div class="demo-badge">The MedGemma Impact Challenge</div>
            <p>
                This is a working prototype demonstrating SELENE architecture.
                <br>
            </p>
            <a href="https://github.com/yourusername/selene-menopause-assistant" 
               class="github-link" 
               target="_blank">
                <span>View on GitHub</span>
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ----------------------------
# Page: Chat with Selene
# ----------------------------
def render_chat():
    # Header with back button
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if st.button("← Back", key="back_chat"):
            go_home()
            st.rerun()

    with col2:
        st.markdown('<div class="selene-header">SELENE</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="page-title">Chat with Selene</div>', unsafe_allow_html=True
    )
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Chat messages container
    chat_html = '<div class="chat-container">'

    if not st.session_state.chat_history:
        chat_html += """
            <div class="chat-message bot-message">
                Hello! I'm Selene, your menopause wellness companion. 
                How can I help you today?
            </div>
        """
    else:
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                chat_html += (
                    f'<div class="chat-message user-message">{message["content"]}</div>'
                )
            else:
                chat_html += (
                    f'<div class="chat-message bot-message">{message["content"]}</div>'
                )

    chat_html += "</div>"
    st.markdown(chat_html, unsafe_allow_html=True)

    # Chat input
    user_input = st.text_input(
        "Type your message...",
        key="chat_input",
        label_visibility="collapsed",
        placeholder="Type your message...",
    )

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("Send", key="send_message", use_container_width=True):
            if user_input:
                st.session_state.chat_history.append(
                    {"role": "user", "content": user_input}
                )

                bot_response = get_bot_response(user_input)
                st.session_state.chat_history.append(
                    {"role": "bot", "content": bot_response}
                )

                st.rerun()


def get_bot_response(user_message):
    """Placeholder for bot response - connect to your AI here."""
    responses = {
        "sleep": "Sleep disruptions are very common during perimenopause. Try maintaining a cool bedroom temperature and establishing a consistent bedtime routine.",
        "hot flash": "Hot flashes affect up to 80% of women during menopause. Layered clothing, staying hydrated, and avoiding triggers like spicy foods can help.",
        "mood": "Mood changes during menopause are normal due to hormonal fluctuations. Regular exercise, adequate sleep, and stress management techniques can help.",
    }

    user_lower = user_message.lower()
    for keyword, response in responses.items():
        if keyword in user_lower:
            return response

    return "Thank you for sharing. I'm here to support you through your menopause journey. Could you tell me more about what you're experiencing?"


# ----------------------------
# Page: Clinical Summary
# ----------------------------
def render_clinical():
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if st.button("← Back", key="back_clinical"):
            go_home()
            st.rerun()

    with col2:
        st.markdown('<div class="selene-header">SELENE</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="page-title">Clinical Summary</div>', unsafe_allow_html=True
    )
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="summary-card">
            <div class="summary-title">Current Stage</div>
            <div class="summary-content">
                <strong>Late Perimenopause</strong><br>
                Based on your symptom patterns and cycle history, you appear to be in 
                the late transition phase of perimenopause.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="summary-card">
            <div class="summary-title">Key Symptoms Tracked</div>
            <div class="summary-content">
                • Sleep disruptions: 4-5 nights/week<br>
                • Hot flashes: 2-3 per day<br>
                • Mood changes: Moderate variability<br>
                • Energy levels: Low to moderate
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="summary-card">
            <div class="summary-title">Recommendations</div>
            <div class="summary-content">
                • Consider discussing HRT options with your healthcare provider<br>
                • Maintain sleep hygiene practices<br>
                • Continue tracking symptoms for pattern recognition<br>
                • Schedule routine health screenings
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("Export for Doctor", key="export", use_container_width=True):
            st.success("Summary exported successfully!")


# ----------------------------
# Page: Log Today's Pulse
# ----------------------------
def render_pulse():
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if st.button("← Back", key="back_pulse"):
            go_home()
            st.rerun()

    with col2:
        st.markdown('<div class="selene-header">SELENE</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="page-title">Log Today\'s Pulse</div>', unsafe_allow_html=True
    )
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="form-label">How did you sleep last night?</div>',
        unsafe_allow_html=True,
    )
    sleep_quality = st.select_slider(
        "Sleep",
        options=["Poor", "Fair", "Good", "Excellent"],
        value="Fair",
        label_visibility="collapsed",
    )

    st.markdown('<div class="form-label">Energy Level</div>', unsafe_allow_html=True)
    energy = st.select_slider(
        "Energy",
        options=["Very Low", "Low", "Moderate", "High", "Very High"],
        value="Moderate",
        label_visibility="collapsed",
    )

    st.markdown('<div class="form-label">Mood</div>', unsafe_allow_html=True)
    mood = st.select_slider(
        "Mood",
        options=["😢", "😕", "😐", "🙂", "😊"],
        value="😐",
        label_visibility="collapsed",
    )

    st.markdown(
        '<div class="form-label">Hot Flashes Today</div>', unsafe_allow_html=True
    )
    hot_flashes = st.number_input(
        "Hot Flashes", min_value=0, max_value=20, value=0, label_visibility="collapsed"
    )

    st.markdown(
        '<div class="form-label">Notes (Optional)</div>', unsafe_allow_html=True
    )
    notes = st.text_area(
        "Notes",
        placeholder="Any additional symptoms or observations...",
        label_visibility="collapsed",
    )

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("Save Entry", key="save_pulse", use_container_width=True):
            st.success("Today's pulse logged successfully!")
            st.balloons()


# ----------------------------
# Main App
# ----------------------------
load_css()

if st.session_state.page == "home":
    render_home()
elif st.session_state.page == "chat":
    render_chat()
elif st.session_state.page == "clinical":
    render_clinical()
elif st.session_state.page == "pulse":
    render_pulse()
