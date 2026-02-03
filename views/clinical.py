import streamlit as st
from fpdf import FPDF
import json
from datetime import datetime, timedelta
from navigation import render_header_with_back
from data_manager import get_filtered_pulse_history
from insights_generator import generate_insights_report, format_report_for_pdf


def _get_dynamic_summary_cards(filtered_data: list):
    """Generate dynamic summary cards based on user profile and pulse data."""
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

    # 1. Process Symptoms from filtered_data
    sleep_disruptions = 0
    hot_flashes = 0
    brain_fog = 0
    total_days = len(filtered_data)

    for entry in filtered_data:
        # Sleep
        if entry.get("rest") in ["3 AM Awakening", "Fragmented"]:
            sleep_disruptions += 1
        # Climate (Hot Flashes)
        if entry.get("climate") in ["Warm", "Flashing", "Heavy"]:
            hot_flashes += 1
        # Clarity
        if entry.get("clarity") == "Brain Fog":
            brain_fog += 1

    symptoms_content = (
        f"""
        • Sleep disruptions: {sleep_disruptions} nights in this period<br>
        • Hot flash intensity tracked: {hot_flashes} times<br>
        • Brain fog episodes: {brain_fog}
    """
        if total_days > 0
        else "No data tracked for this period."
    )

    # 2. Basic Recommendations logic
    recommendations = ["• Continue tracking symptoms for pattern recognition"]
    if sleep_disruptions > total_days / 2 and total_days > 0:
        recommendations.append("• Maintain strict sleep hygiene practices")
    if hot_flashes > 0:
        recommendations.append(
            "• Consider layering clothing and maintaining a cool environment"
        )
    if total_days > 0:
        recommendations.append(
            "• Schedule routine health screenings to discuss these patterns"
        )

    # Format recommendations as HTML
    recommendations_content = "<br>".join(recommendations)

    summary_cards = [
        {
            "title": "Current Stage",
            "content": f"<strong>{stage_title}</strong><br>{stage_desc}",
        },
        {
            "title": "Key Symptoms Tracked",
            "content": symptoms_content,
        },
        {
            "title": "Recommendations",
            "content": recommendations_content,
        },
    ]
    return summary_cards


def _clean_html_content(content: str) -> str:
    """Remove HTML tags and convert to plain text."""
    content = content.replace("<strong>", "").replace("</strong>", "")
    content = content.replace("<br>", "\n")
    content = content.replace("•", "-")
    return content.strip()


def generate_pdf(summary_cards: list, start_date, end_date) -> bytes:
    """Generate PDF from summary cards."""
    pdf = FPDF()
    pdf.add_page()

    # Title
    pdf.set_font("Arial", "B", 20)
    pdf.cell(0, 15, "Clinical Summary", ln=True, align="C")

    # Date Range
    pdf.set_font("Arial", "I", 12)
    pdf.cell(
        0,
        10,
        f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
        ln=True,
        align="C",
    )
    pdf.ln(5)

    # Generated Date
    pdf.set_font("Arial", "I", 8)
    pdf.cell(
        0,
        10,
        f"Generated on: {datetime.now().strftime('%B %d, %Y')}",
        ln=True,
        align="R",
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


def generate_insights_pdf(report_data: dict) -> bytes:
    """Generate PDF from insights report."""
    pdf = FPDF()
    pdf.add_page()

    # Title
    pdf.set_font("Arial", "B", 22)
    pdf.cell(0, 15, report_data["title"], ln=True, align="C")
    pdf.ln(5)

    # Stage
    pdf.set_font("Arial", "I", 12)
    pdf.cell(0, 10, f"Stage: {report_data['user_stage']}", ln=True, align="C")
    pdf.ln(3)

    # Generated Date
    pdf.set_font("Arial", "I", 10)
    pdf.cell(0, 10, f"Generated: {report_data['generated_date']}", ln=True, align="C")
    pdf.ln(10)

    # Report Content
    pdf.set_font("Arial", "", 11)

    # Split content into lines and handle text wrapping
    content = report_data["report_content"]
    lines = content.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            pdf.ln(5)
            continue

        # Check if it's a header (starts with ** or #)
        if line.startswith("**") and line.endswith("**"):
            # Bold header
            pdf.set_font("Arial", "B", 13)
            header_text = line.strip("*").strip()
            pdf.multi_cell(0, 7, header_text)
            pdf.set_font("Arial", "", 11)
            pdf.ln(2)
        elif line.startswith("###"):
            # Subheader
            pdf.set_font("Arial", "B", 11)
            header_text = line.strip("#").strip()
            pdf.multi_cell(0, 7, header_text)
            pdf.set_font("Arial", "", 11)
            pdf.ln(2)
        elif line.startswith("-") or line.startswith("*"):
            # Bullet point
            pdf.multi_cell(0, 6, f"  {line}")
        else:
            # Regular text
            pdf.multi_cell(0, 6, line)

        pdf.ln(2)

    # Disclaimer
    pdf.ln(10)
    pdf.set_font("Arial", "I", 9)
    pdf.multi_cell(0, 5, report_data["disclaimer"])

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

    # Date Range Selector
    today = datetime.now()
    thirty_days_ago = today - timedelta(days=30)

    date_range = st.date_input(
        "Select Report Period",
        value=(thirty_days_ago.date(), today.date()),
        max_value=today.date(),
        key="clinical_date_range",
    )

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date_dt = datetime.combine(date_range[0], datetime.min.time())
        end_date_dt = datetime.combine(date_range[1], datetime.max.time())

        # Get filtered data
        filtered_data = get_filtered_pulse_history(start_date_dt, end_date_dt)

        # Get dynamic cards
        summary_cards = _get_dynamic_summary_cards(filtered_data)

        # Render all summary cards
        for card in summary_cards:
            _render_summary_card(card["title"], card["content"])

        # Export button
        col1, col2, col3 = st.columns([1, 1, 1])

        # Insights Report button
        st.markdown("<br>", unsafe_allow_html=True)
        with col1:
            pdf_bytes = generate_pdf(summary_cards, start_date_dt, end_date_dt)
            st.download_button(
                label="Export for Doctor",
                data=pdf_bytes,
                file_name="clinical_summary.pdf",
                mime="application/pdf",
                on_click="ignore",
                use_container_width=True,
            )
        with col2:
            if st.button(
                "Generate Insights Report", key="insights_btn", use_container_width=True
            ):
                with st.spinner("Analyzing your complete history with MedGemma..."):
                    success, result = generate_insights_report()

                    if success:
                        # Display the report
                        st.markdown("---")
                        st.markdown("### 📊 Your Personalized Insights")
                        st.markdown(result)
                        st.markdown("---")

                        # Generate PDF download
                        user_profile = st.session_state.get("user_profile", {})
                        report_data = format_report_for_pdf(result, user_profile)
                        insights_pdf = generate_insights_pdf(report_data)

                        st.download_button(
                            label="Download Insights Report (PDF)",
                            data=insights_pdf,
                            file_name=f"selene_insights_{datetime.now().strftime('%Y%m%d')}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                        )
                    else:
                        st.error(f"Failed to generate report: {result}")
    else:
        st.info("Please select a complete date range (Start and End date).")
