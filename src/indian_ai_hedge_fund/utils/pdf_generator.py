import logging
import re # Import regular expression module
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table as ReportlabTable, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib import colors
from reportlab.lib.units import inch
import pandas as pd
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# --- PDF Generation Function ---

def generate_pdf_report(holdings_data: Any, analyst_reports: Dict[str, Any], final_synthesis: str | None, filename: str):
    """Generates a PDF report with holdings, analyst reports, and final synthesis."""
    logger.info(f"Generating PDF report: {filename}")
    doc = SimpleDocTemplate(filename)
    styles = getSampleStyleSheet()
    story = []

    # --- Title ---
    title = "Indian AI Hedge Fund Analysis Report"
    story.append(Paragraph(title, styles['h1']))
    story.append(Spacer(1, 0.2*inch))
    report_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    story.append(Paragraph(f"Report generated on: {report_date}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))

    # --- Holdings ---
    story.append(Paragraph("Current Portfolio Holdings", styles['h2']))
    story.append(Spacer(1, 0.1*inch))

    holdings_table_data = []
    if isinstance(holdings_data, pd.DataFrame) and not holdings_data.empty:
        # Select a subset of columns for the PDF report
        pdf_columns = ['tradingsymbol', 'quantity', 'average_price', 'last_price', 'pnl']
        display_columns = [col for col in pdf_columns if col in holdings_data.columns]

        if not display_columns:
             holdings_table_data.append([Paragraph("Relevant holding columns not found.", styles['Normal'])])
        else:
            # Prepare header row with selected columns
            headers = [Paragraph(f"<b>{col}</b>", styles['Normal']) for col in display_columns]
            holdings_table_data.append(headers)
            # Add data rows for selected columns
            for index, row in holdings_data[display_columns].iterrows():
                holdings_table_data.append([Paragraph(str(item).replace('\n', '<br/>'), styles['Normal']) for item in row])

    elif isinstance(holdings_data, list) and holdings_data:
        # Attempt to handle list of dicts, but might be less reliable without known keys
        if isinstance(holdings_data[0], dict):
            # Try to find common keys or a subset - this is less robust
            # For simplicity, maybe just show the first few keys or specific known ones
            potential_keys = list(holdings_data[0].keys())
            # Example: Prioritize similar keys if found
            list_keys_subset = [k for k in ['tradingsymbol', 'quantity', 'average_price', 'last_price', 'pnl'] if k in potential_keys]
            if not list_keys_subset:
                 list_keys_subset = potential_keys[:5] # Fallback: first 5 keys

            if list_keys_subset:
                headers = [Paragraph(f"<b>{key}</b>", styles['Normal']) for key in list_keys_subset]
                holdings_table_data.append(headers)
                for item_dict in holdings_data:
                     holdings_table_data.append([Paragraph(str(item_dict.get(key, 'N/A')).replace('\n', '<br/>'), styles['Normal']) for key in list_keys_subset])
            else:
                 holdings_table_data.append([Paragraph("Could not determine columns for list data.", styles['Normal'])])
        else:
            # Fallback for simple list - no headers, single column
            holdings_table_data.append([Paragraph("<b>Value</b>", styles['Normal'])]) # Add a generic header
            for item in holdings_data:
                 holdings_table_data.append([Paragraph(str(item).replace('\n', '<br/>'), styles['Normal'])])
    else:
         # Added a case for when holdings_data is None or empty non-list/df
         holdings_table_data.append([Paragraph("No holdings data available or in an unrecognized format.", styles['Normal'])])


    if len(holdings_table_data) > 1: # Check if there's more than just the header or placeholder
        holdings_table = ReportlabTable(holdings_table_data, hAlign='LEFT')
        holdings_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(holdings_table)
    else:
        # Display the placeholder message if table is empty/invalid
        story.append(holdings_table_data[0][0])

    story.append(Spacer(1, 0.3*inch))

    # --- Analyst Reports ---
    story.append(Paragraph("Individual Analyst Reports", styles['h2']))
    story.append(Spacer(1, 0.1*inch))

    if analyst_reports:
        for name, report in analyst_reports.items():
            story.append(Paragraph(f"Report from {name}", styles['h3']))
            story.append(Spacer(1, 0.05*inch))
            if isinstance(report, dict):
                # Format dict reports (like Technical Analyst) as a table
                report_table_data = []
                # Header Row
                headers = ["Ticker", "Signal", "Confidence (%)", "Reasoning"]
                report_table_data.append([Paragraph(f"<b>{h}</b>", styles['Normal']) for h in headers])
                # Data Rows
                for ticker, analysis in report.items():
                    signal = getattr(analysis, 'signal', 'N/A')
                    confidence = getattr(analysis, 'confidence', 'N/A')
                    reasoning = getattr(analysis, 'reasoning', 'N/A')
                    conf_str = f"{confidence:.1f}" if isinstance(confidence, (float, int)) else str(confidence)
                    # Replace \n with <br/> for table cell paragraphs
                    report_table_data.append([
                        Paragraph(str(ticker).replace('\n', '<br/>'), styles['Normal']),
                        Paragraph(str(signal).replace('\n', '<br/>'), styles['Normal']),
                        Paragraph(conf_str.replace('\n', '<br/>'), styles['Normal']),
                        Paragraph(str(reasoning).replace('\n', '<br/>'), styles['BodyText']) # Use BodyText for longer reasoning
                    ])

                if len(report_table_data) > 1:
                    report_table = ReportlabTable(report_table_data, colWidths=[1*inch, 1*inch, 1*inch, 3.5*inch], hAlign='LEFT')
                    report_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
                        ('GRID', (0, 0), (-1, -1), 1, colors.darkgrey),
                        ('ALIGN', (3, 1), (3, -1), 'LEFT'), # Align Reasoning left
                    ]))
                    story.append(report_table)
                else:
                    story.append(Paragraph("Report data is empty.", styles['Normal']))

            elif isinstance(report, str):
                # Handle string reports - use Paragraph with justification
                # Replace markdown-like elements using regex for proper tag matching
                report_text = report.replace('\n', '<br/>')
                report_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', report_text) # Handle **bold**
                # Add more substitutions here if needed (e.g., for *italic*)
                p = Paragraph(report_text, styles['BodyText'])
                p.style.alignment = TA_JUSTIFY
                story.append(p)
            else:
                # Fallback for other types
                story.append(Paragraph(str(report), styles['Normal']))

            story.append(Spacer(1, 0.2*inch))
    else:
        story.append(Paragraph("No analyst reports were generated or available.", styles['Normal']))

    story.append(Spacer(1, 0.3*inch))

    # --- Final Synthesis ---
    story.append(Paragraph("Synthesized Analysis Results", styles['h2']))
    story.append(Spacer(1, 0.1*inch))

    if final_synthesis:
        # Replace newlines and basic markdown for PDF paragraphs using regex
        synthesis_text = final_synthesis.replace('\n', '<br/>')
        synthesis_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', synthesis_text) # Handle **bold**
        # Add more substitutions here if needed
        p = Paragraph(synthesis_text, styles['BodyText'])
        p.style.alignment = TA_JUSTIFY
        story.append(p)
    else:
        story.append(Paragraph("Final synthesis was not generated (possibly due to errors).", styles['Normal']))

    # --- Build PDF ---
    try:
        doc.build(story)
        logger.info(f"Successfully generated PDF: {filename}")
    except Exception as e:
        logger.error(f"Failed to build PDF '{filename}': {e}")
        # Consider specific error handling or logging details here
        raise # Re-raise the exception to be caught in main

# --- End PDF Generation Function ---