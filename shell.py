import streamlit as st

# ----------------------------
# Page config
# ----------------------------
st.set_page_config(page_title="SELENE", layout="centered")

# ----------------------------
# Session state for navigation
# ----------------------------
if "action" not in st.session_state:
    st.session_state.action = None

# ----------------------------
# CSS
# ----------------------------
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
        padding-top: 2rem;
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

    .divider {
        border-bottom: 1px solid #EAEAEA;
        margin-bottom: 40px;
    }

    .sub-header {
        text-align: center;
        font-size: 11px;
        letter-spacing: 1.5px;
        color: #777;
        text-transform: uppercase;
        font-weight: 600;
        margin-top: 40px;
    }

    .italic-note {
        text-align: center;
        font-size: 14px;
        color: #999;
        font-style: italic;
        font-family: serif;
        margin-bottom: 40px;
    }

    .main-message {
        text-align: center;
        font-size: 18px;
        color: #555;
        font-weight: 300;
        line-height: 1.5;
        margin-bottom: 40px;
    }

    /* Button base */
    .selene-btn {
        border: none;
        border-radius: 50px;
        padding: 12px 20px;
        font-size: 15px;
        font-weight: 500;
        color: white;
        width: 100%;
        cursor: pointer;
        box-shadow: 0 4px 6px rgba(0,0,0,0.06);
        transition: all 0.25s ease;
    }

    .selene-btn:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 10px rgba(0,0,0,0.08);
    }

    /* Variants */
    .btn-chat { background-color: #8DA4C2; }
    .btn-clinical { background-color: #8DA4C2; }
    .btn-pulse {
        background-color: #8DA4C2;
        width: 220px;  /* Fixed width */
        margin: 0 auto;
        display: block;
    }

    /* Layout helpers */

    .top-buttons {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 24px;
        margin-bottom: 40px;
        flex-wrap: wrap; /* Allows wrapping on small screens */
    }

    .top-buttons .selene-btn {
        width: 220px;
        min-width: 180px;
    }

    .center-row {
        display: grid;
        grid-template-columns: 1fr 2fr 1fr;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------
# Button click handler (JS → Streamlit)
# ----------------------------
def html_button(label, action, css_class):
    st.markdown(
        f"""
        <button class="selene-btn {css_class}"
                onclick="window.location.search='?action={action}'">
            {label}
        </button>
        """,
        unsafe_allow_html=True,
    )


# ----------------------------
# Capture POST action
# ----------------------------
query_params = st.query_params
if "action" in query_params:
    st.session_state.action = query_params["action"][0]
    st.query_params  # clear

# ----------------------------
# Layout
# ----------------------------
st.markdown('<div class="selene-header">SELENE</div>', unsafe_allow_html=True)
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# Top buttons (side by side) - FIXED
st.markdown(
    f"""
    <div class="top-buttons">
        <button class="selene-btn btn-chat"
                onclick="window.location.search='?action=chat'">
            Chat with Selene
        </button>
        <button class="selene-btn btn-clinical"
                onclick="window.location.search='?action=clinical'">
            Clinical Summary
        </button>
    </div>
    """,
    unsafe_allow_html=True,
)
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
# Bottom button - FIXED
st.markdown(
    """
    <div style="display: flex; justify-content: center;">
        <button class="selene-btn btn-pulse"
                onclick="window.location.search='?action=pulse'">
            Log Today's Pulse
        </button>
    </div>
    """,
    unsafe_allow_html=True,
)

# ----------------------------
# App logic based on state
# ----------------------------
if st.session_state.action == "chat":
    st.info("Chat with Selene selected")

elif st.session_state.action == "clinical":
    st.info("Clinical Summary selected")

elif st.session_state.action == "pulse":
    st.info("Log Today’s Pulse selected")
