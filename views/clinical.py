import streamlit as st
from fpdf import FPDF
import json
from navigation import render_header_with_back


def _get_dynamic_summary_cards():
    """Generate dynamic summary cards based on user profile."""
    # Load stage data
    try:
        with open("metadata/stages.json", "r") as f:
            stages_data = json.load(f)
    except Exception:
        stages_data = {"stages": {}}

    # Get user's current stage
    user_profile = st.session_state.get("user_profile", {})
    current_stage_key = user_profile.get("stage", "late_transition")
    stage_info = stages_data.get("stages", {}).get(current_stage_key, {})

    stage_title = stage_info.get("title", "Unknown Stage")
    stage_desc = f"Based on your symptom patterns and cycle history, you appear to be in the {stage_info.get('title', 'transition phase')}. "

    summary_cards = [
        {
            "title": "Current Stage",
            "content": f"<strong>{stage_title}</strong><br>{stage_desc}",
        },
        {
            "title": "Key Symptoms Tracked",
            "content": """
# TODO: Get user's symptoms
            """,
        },
        {
            "title": "Recommendations",
            "content": """
# TODO: Get user's recommendations
            """,
        },
    ]
    return summary_cards


def _clean_html_content(content: str) -> str:
    """Remove HTML tags and convert to plain text."""
    content = content.replace("<strong>", "").replace("</strong>", "")
    content = content.replace("<br>", "\n")
    content = content.replace("•", "-")
    return content.strip()


def generate_pdf(summary_cards: list) -> bytes:
    """Generate PDF from summary cards."""
    pdf = FPDF()
    pdf.add_page()

    # Title
    pdf.set_font("Arial", "B", 20)
    pdf.cell(0, 15, "Clinical Summary", ln=True, align="C")
    pdf.ln(5)

    # Date
    from datetime import datetime

    pdf.set_font("Arial", "I", 10)
    pdf.cell(
        0, 10, f"Generated: {datetime.now().strftime('%B %d, %Y')}", ln=True, align="C"
    )
    pdf.ln(10)

    # Summary cards
    for card in summary_cards:
        # Card title
        pdf.set_font("Arial", "B", 14)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 10, card["title"], ln=True, fill=True)

        # Card content
        pdf.set_font("Arial", "", 11)
        content = _clean_html_content(card["content"])
        pdf.multi_cell(0, 7, content)
        pdf.ln(8)

    # Footer
    pdf.ln(10)
    pdf.set_font("Arial", "I", 9)
    pdf.cell(
        0,
        10,
        "This summary is for informational purposes. Please consult your healthcare provider.",
        ln=True,
        align="C",
    )

    return bytes(pdf.output())


def _render_summary_card(title: str, content: str):
    """Render a single summary card."""
    st.markdown(
        f"""
        <div class="summary-card">
            <div class="summary-title">{title}</div>
            <div class="summary-content">{content}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_clinical():
    """Render the clinical summary page."""
    render_header_with_back("back_clinical")

    st.markdown(
        '<div class="page-title">Clinical Summary</div>', unsafe_allow_html=True
    )
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Get dynamic cards
    summary_cards = _get_dynamic_summary_cards()

    # Render all summary cards
    for card in summary_cards:
        _render_summary_card(card["title"], card["content"])

    # Export button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        pdf_bytes = generate_pdf(summary_cards)
        st.download_button(
            label="Export for Doctor",
            data=pdf_bytes,
            file_name="clinical_summary.pdf",
            mime="application/pdf",
            on_click="ignore",
            use_container_width=True,
        )
