"""
Clinical Summary & AI Insights View.

Generates and displays specialized medical insights using the multi-agent 
reasoning pipeline. Handles report streaming, historical analysis 
filtering, and high-fidelity PDF export.
"""

import io
import logging
import re
from datetime import datetime, timedelta

import markdown
import streamlit as st
from xhtml2pdf import pisa

from selene.core.insights_generator import format_report_for_pdf, generate_insights_report
from selene.ui.navigation import render_header_with_back

logger = logging.getLogger(__name__)

_PDF_CSS = """
@page {
    size: A4;
    margin: 2cm;
}
body {
    font-family: Helvetica, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.5;
    color: #1a1a1a;
}
.header {
    text-align: center;
    margin-bottom: 20px;
}
.header h1 {
    font-size: 22pt;
    margin-bottom: 4px;
    color: #2c3e50;
}
.header .stage {
    font-style: italic;
    font-size: 12pt;
    color: #555;
}
.header .date {
    font-style: italic;
    font-size: 10pt;
    color: #777;
}
hr {
    border: none;
    border-top: 1px solid #ccc;
    margin: 16px 0;
}
h1 { font-size: 18pt; color: #2c3e50; margin-top: 18px; }
h2 { font-size: 15pt; color: #2c3e50; margin-top: 14px; }
h3 { font-size: 13pt; color: #34495e; margin-top: 12px; }
ul, ol {
    margin-left: 18px;
    margin-bottom: 8px;
}
li {
    margin-bottom: 4px;
}
p {
    margin-bottom: 6px;
}
.disclaimer {
    margin-top: 30px;
    font-style: italic;
    font-size: 9pt;
    color: #888;
    border-top: 1px solid #ddd;
    padding-top: 10px;
}
"""


@st.cache_data(show_spinner=False)
def generate_insights_pdf(report_data: dict) -> bytes:
    """Generate a PDF from insights report by converting Markdown to HTML.

    Uses the *markdown* library to render the report content (which is
    Markdown) into HTML, wraps it with a styled template, and converts
    the whole document to PDF via *xhtml2pdf*.
    """

    logger.debug(
        "generate_insights_pdf: ENTER title=%s content_len=%d",
        report_data.get("title", ""),
        len(report_data.get("report_content", "")),
    )

    # Convert the markdown report body to HTML
    md_extensions = ["extra", "sane_lists", "smarty", "nl2br"]
    report_html = markdown.markdown(
        report_data["report_content"], extensions=md_extensions
    )

    # Build the full HTML document
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>{_PDF_CSS}</style>
</head>
<body>
    <div class="header">
        <h1>{report_data["title"]}</h1>
        <p class="stage">Stage: {report_data["user_stage"]}</p>
        <p class="date">Generated: {report_data["generated_date"]}</p>
    </div>
    <hr>
    {report_html}
    <div class="disclaimer">{report_data["disclaimer"]}</div>
</body>
</html>"""

    # Render HTML ➜ PDF
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(io.StringIO(html), dest=pdf_buffer)
    if pisa_status.err:
        logger.error("generate_insights_pdf: xhtml2pdf conversion failed err=%s", pisa_status.err)
        raise RuntimeError(f"xhtml2pdf conversion failed (errors: {pisa_status.err})")

    pdf_bytes = pdf_buffer.getvalue()
    logger.info("generate_insights_pdf: SUCCESS bytes=%d", len(pdf_bytes))
    return pdf_bytes

def _split_report_sections(report_text: str) -> list[tuple[str, str]]:
    """Split a markdown report into (header, body) pairs on ### boundaries."""
    parts = re.split(r"^###\s+", report_text, flags=re.MULTILINE)
    sections = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # First line is the header, rest is the body
        header, _, body = part.partition("\n")
        sections.append((header.strip(), body.strip()))
    logger.debug("_split_report_sections: sections=%d", len(sections))
    return sections


def render_clinical():
    """Render the clinical summary page with AI insights."""
    logger.debug("render_clinical: ENTER")
    render_header_with_back("back_clinical")

    st.markdown(
        '<div class="page-title">Clinical AI Summary</div>', unsafe_allow_html=True
    )
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Date Range Selector
    today = datetime.now()
    thirty_days_ago = today - timedelta(days=30)

    date_range = st.date_input(
        "Select Report Period",
        value=(thirty_days_ago.date(), today.date()),
        max_value=today.date(),
        key="clinical_date_range_picker",
    )

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date_dt = datetime.combine(date_range[0], datetime.min.time())
        end_date_dt = datetime.combine(date_range[1], datetime.max.time())
        logger.info("render_clinical: selected range %s -> %s", date_range[0], date_range[1])

        # Check if we need to regenerate
        last_range = st.session_state.get("last_clinical_range")
        current_range = (date_range[0], date_range[1])

        # Generate report if not exists or date range changed
        if (
            "clinical_report" not in st.session_state
            or last_range != current_range
        ):
            logger.debug(
                "render_clinical: generating report cached=%s range_changed=%s",
                "clinical_report" in st.session_state,
                last_range != current_range,
            )
            with st.spinner("Generating insights report..."):
                success, result, metrics = generate_insights_report(
                    start_date=start_date_dt,
                    end_date=end_date_dt
                )

                if success:
                    # Store with consistent key
                    st.session_state.clinical_report = result
                    st.session_state.last_clinical_range = current_range
                    st.session_state.clinical_metrics = metrics
                    logger.info(
                        "render_clinical: report generated chars=%d has_metrics=%s",
                        len(result),
                        metrics is not None,
                    )
                    st.success("Report generated successfully!")
                else:
                    logger.error("render_clinical: report generation failed error=%s", result)
                    st.error(f"{result}")
                    # Clear old report on error
                    if "clinical_report" in st.session_state:
                        del st.session_state.clinical_report

        # Display the report if it exists
        if "clinical_report" in st.session_state:
            report_text = st.session_state.clinical_report

            """ # Optional: Display metrics
            if "clinical_metrics" in st.session_state:
                metrics = st.session_state.clinical_metrics
                with st.expander("Report Quality Metrics"):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Words", metrics['word_count'])
                    with col2:
                        st.metric("Sections", f"{metrics['section_count']}/4")
                    with col3:
                        st.metric("Generation", f"{metrics['generation_time_seconds']}s")
                    with col4:
                        completeness_pct = int(metrics['context_completeness'] * 100)
                        st.metric("Data Quality", f"{completeness_pct}%") """

            # Display the report split into visual blocks per section
            st.markdown("---")
            sections = _split_report_sections(report_text)
            logger.debug("render_clinical: rendering sections=%d", len(sections))


            for header, body in sections:
                with st.container(border=True):
                    st.markdown(f"### {header}")
                    st.markdown(body)

            st.markdown("---")

            # Export button (Centered)
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                # Prepare PDF for export
                user_profile = st.session_state.get("user_profile", {})

                # Pass metrics to PDF formatter if available
                metrics_for_pdf = st.session_state.get("clinical_metrics")
                report_data = format_report_for_pdf(
                    report_text,
                    user_profile,
                    metrics_for_pdf
                )

                # Update date range in title for the PDF
                report_data["title"] = f"Clinical Summary ({date_range[0]} to {date_range[1]})"
                pdf_bytes = generate_insights_pdf(report_data)
                logger.info("render_clinical: PDF prepared bytes=%d", len(pdf_bytes))

                st.download_button(
                    label="Export PDF",
                    data=pdf_bytes,
                    file_name=f"clinical_summary_{date_range[0]}_{date_range[1]}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
        else:
            st.info("Select a date range above to generate your clinical insights report.")

    else:
        logger.debug("render_clinical: incomplete date range selected")
        st.info("Please select a complete date range (Start and End date).")
