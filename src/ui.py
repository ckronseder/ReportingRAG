import streamlit as st
import pandas as pd
from jinja2 import Environment, FileSystemLoader
import os
import base64
import locale
from datetime import datetime
from visualizations import create_waterfall_chart
import markdown
import re
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import landscape, A4
import tempfile

def image_to_base64(path):
    """Converts an image file to a Base64 string."""
    try:
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except FileNotFoundError:
        return None

def format_currency(value):
    """Formats a number as CHF currency."""
    try:
        locale.setlocale(locale.LC_ALL, 'de_CH.UTF-8')
        return locale.currency(float(value), grouping=True, symbol='CHF')
    except (ValueError, TypeError):
        return value

def _get_waterfall_chart_data(full_financial_data):
    """
    Extracts data for a P&L waterfall chart, flowing from income to net result.
    """
    waterfall_x = []
    waterfall_y = []
    waterfall_measure = []

    ertraege_data = full_financial_data.get("Erträge", {})
    aufwand_data = full_financial_data.get("Aufwand", {})

    # Define the keys for the main totals and the final result
    POSSIBLE_ERTRAEGE_KEYS = [
        "Erträge aus Vermietung ohne MWST",
        "Erträge aus Vermietung",
        "Erträge"
    ]
    AUFWANDE_KEY = "Aufwände"
    FINAL_RESULT_KEY = "Abschluss Erfolgsrechnung"

    # 1. Find and start with Total Income
    ertraege_key_found = None
    for key in POSSIBLE_ERTRAEGE_KEYS:
        if key in ertraege_data:
            ertraege_key_found = key
            break
    
    if ertraege_key_found is None:
        st.warning(f"Could not find a valid income key in Erträge data. Cannot build waterfall chart.")
        return [], [], []

    # Ensure the starting income value is positive
    ertraege_total_value = abs(ertraege_data[ertraege_key_found])
    waterfall_x.append("Erträge") # Renamed label
    waterfall_y.append(ertraege_total_value)
    waterfall_measure.append("absolute")

    # 2. Subtract main expense categories from "Aufwand"
    if not aufwand_data:
        st.warning("Aufwand data not available for waterfall chart.")
    else:
        for key, value in aufwand_data.items():
            # Skip the main total and the final result keys
            if key == AUFWANDE_KEY or key == FINAL_RESULT_KEY:
                continue
            
            # Only subtract main expense categories (those without a 4-digit code)
            if not re.search(r'[0-9]{4}', key):
                waterfall_x.append(key)
                waterfall_y.append(-value) # Negative for breakdown
                waterfall_measure.append("relative")

    # 3. Add the final result bar
    if FINAL_RESULT_KEY in aufwand_data:
        final_result_value = aufwand_data[FINAL_RESULT_KEY]
        waterfall_x.append("Gewinn") # Renamed label
        waterfall_y.append(final_result_value)
        waterfall_measure.append("total")
    else:
        st.warning(f"'{FINAL_RESULT_KEY}' not found in Aufwand data. Waterfall chart will be incomplete.")

    return waterfall_x, waterfall_y, waterfall_measure

def _create_financial_table(data_dict, headers, table_width, styles):
    """Creates a styled ReportLab table from a financial data dictionary."""
    table_data = []
    
    # Prepare header row with Paragraphs
    header_row = [Paragraph(headers[0], styles['TableHeaderLeft']), Paragraph(headers[1], styles['TableHeaderRight'])]
    table_data.append(header_row)

    for key, value in data_dict.items():
        formatted_value = format_currency(value)
        
        # Condition for bolding: if the key does NOT contain a sequence of four digits
        is_bold = not bool(re.search(r'[0-9]{4}', key))
        
        # Special condition for "Abschluss Erfolgsrechnung"
        if key == "Abschluss Erfolgsrechnung":
            key_paragraph = Paragraph(key, styles['OrangeBodyBoldSmallLeft'])
            value_paragraph = Paragraph(formatted_value, styles['OrangeBodyBoldSmallRight'])
        elif is_bold:
            key_paragraph = Paragraph(key, styles['BodyBoldSmallLeft'])
            value_paragraph = Paragraph(formatted_value, styles['BodyBoldSmallRight'])
        else:
            key_paragraph = Paragraph(key, styles['BodySmallLeft'])
            value_paragraph = Paragraph(formatted_value, styles['BodySmallRight'])
        
        table_data.append([key_paragraph, value_paragraph])
    
    col_widths = [table_width * 0.66, table_width * 0.34]
    
    table = Table(table_data, colWidths=col_widths)
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.white), # Entire table background white
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('LEFTPADDING', (0, 1), (-1, -1), 2),
        ('RIGHTPADDING', (0, 1), (-1, -1), 2),
        ('TOPPADDING', (0, 1), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 2),
        ('LINEBELOW', (0,0), (-1,0), 1, colors.black), # Line below header
    ])
    table.setStyle(style)
    return table

def _add_page_footer(canvas, doc, logo_path):
    """Adds a footer with logo and page number to each page."""
    canvas.saveState()
    
    # Draw separator line
    line_y = doc.bottomMargin + 0.1 * inch
    canvas.setStrokeColorRGB(0, 0, 0)
    canvas.line(doc.leftMargin, line_y, doc.width + doc.leftMargin, line_y)

    # Draw logo on the left, below the line
    if os.path.exists(logo_path):
        canvas.drawImage(logo_path, doc.leftMargin, 0.1 * inch, width=0.6*inch, height=0.6*inch, preserveAspectRatio=True, mask='auto')

    # Draw page number on the right
    canvas.setFont('Helvetica', 9)
    page_number_text = f"Seite {doc.page}"
    canvas.drawRightString(doc.width + doc.leftMargin, 0.2 * inch, page_number_text)
    
    canvas.restoreState()

def markdown_to_flowables(md_text, styles):
    """Converts a markdown string to a list of ReportLab Flowables."""
    flowables = []
    for line in md_text.split('\n'):
        line = line.strip()
        if line.startswith('- '):
            # Use the existing 'Bullet' style and remove the markdown character
            flowables.append(Paragraph(line[2:], styles['Bullet']))
        elif line.startswith('**') and line.endswith('**'):
            # Use <b> tags for bold
            flowables.append(Paragraph(f"<b>{line[2:-2]}</b>", styles['Body']))
        elif line.startswith('*') and line.endswith('*'):
            # Use <i> tags for italic
            flowables.append(Paragraph(f"<i>{line[1:-1]}</i>", styles['Body']))
        elif line: # Handle non-empty lines
            flowables.append(Paragraph(line, styles['Body']))
    return flowables

def pdf_from_reportlab(image_file, full_financial_data, dynamic_date_range, dynamic_primary_market_area):
    """Generates a PDF report using ReportLab."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=inch/2, leftMargin=inch/2, topMargin=inch/2, bottomMargin=inch/2)
    
    styles = getSampleStyleSheet()
    
    # Define LeliaOrange
    LeliaOrange = colors.HexColor('#ff6b00')

    # Modify existing Title style
    styles['Title'].fontName = 'Helvetica-Bold'
    styles['Title'].fontSize = 24
    styles['Title'].alignment = TA_CENTER
    styles['Title'].spaceAfter = 14

    # Add custom styles
    styles.add(ParagraphStyle(name='Date', fontName='Helvetica', fontSize=12, alignment=TA_CENTER, spaceAfter=20))
    styles.add(ParagraphStyle(name='H1', fontName='Helvetica-Bold', fontSize=18, spaceBefore=20, spaceAfter=10))
    styles.add(ParagraphStyle(name='H2', fontName='Helvetica-Bold', fontSize=14, spaceBefore=10, spaceAfter=5))
    styles.add(ParagraphStyle(name='Body', fontName='Helvetica', fontSize=10, leading=14))
    styles.add(ParagraphStyle(name='Quote', fontName='Helvetica-BoldOblique', fontSize=12, leading=14, leftIndent=20, rightIndent=20, spaceBefore=10, spaceAfter=10))
    
    # New styles for financial tables
    styles.add(ParagraphStyle(name='BodySmallLeft', fontName='Helvetica', fontSize=8, leading=10, alignment=TA_LEFT))
    styles.add(ParagraphStyle(name='BodyBoldSmallLeft', fontName='Helvetica-Bold', fontSize=8, leading=10, alignment=TA_LEFT))
    styles.add(ParagraphStyle(name='BodySmallRight', fontName='Helvetica', fontSize=8, leading=10, alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name='BodyBoldSmallRight', fontName='Helvetica-Bold', fontSize=8, leading=10, alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name='TableHeaderLeft', fontName='Helvetica-Bold', fontSize=10, textColor=LeliaOrange, alignment=TA_LEFT))
    styles.add(ParagraphStyle(name='TableHeaderRight', fontName='Helvetica-Bold', fontSize=10, textColor=LeliaOrange, alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name='KpiValue', fontName='Helvetica-Bold', fontSize=24, textColor=LeliaOrange, alignment=TA_LEFT))
    styles.add(ParagraphStyle(name='KpiTitle', fontName='Helvetica', fontSize=10, alignment=TA_LEFT, spaceBefore=10))
    styles.add(ParagraphStyle(name='OrangeBodyBoldSmallLeft', fontName='Helvetica-Bold', fontSize=8, leading=10, alignment=TA_LEFT, textColor=LeliaOrange))
    styles.add(ParagraphStyle(name='OrangeBodyBoldSmallRight', fontName='Helvetica-Bold', fontSize=8, leading=10, alignment=TA_RIGHT, textColor=LeliaOrange))


    story = []
    chart_filename = None
    hero_image_path = None

    try:
        # --- Robust Path Construction ---
        script_dir = os.path.dirname(__file__)
        templates_dir = os.path.abspath(os.path.join(script_dir, '..', 'templates'))
        logo_path = os.path.join(templates_dir, 'LELIA_LOGO_L_O.png')

        # --- Title Page ---
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=3*inch, height=1.5*inch)
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 0.25*inch))

        story.append(Paragraph(dynamic_primary_market_area, styles['Title'])) # Use dynamic_primary_market_area as the main title
        story.append(Paragraph(dynamic_date_range, styles['Date']))

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_image:
            tmp_image.write(image_file.getvalue())
            hero_image_path = tmp_image.name
        
        hero_image = Image(hero_image_path, width=7*inch, height=3.75*inch)
        hero_image.hAlign = 'CENTER'
        story.append(hero_image)
        story.append(PageBreak())

        # --- Executive Summary & KPIs ---
        story.append(Paragraph("Zusammenfassung & KPIs", styles['H1']))
        story.append(Spacer(1, 0.2*inch))

        # Create KPI column
        kpi_story = []
        kpi_story.append(Paragraph("Leerstand (%)", styles['KpiTitle']))
        kpi_story.append(Paragraph(f"{st.session_state.leerstand:.2f}%", styles['KpiValue']))
        kpi_story.append(Spacer(1, 0.2*inch))
        kpi_story.append(Paragraph("Rendite auf Eigenkapital (%)", styles['KpiTitle']))
        kpi_story.append(Paragraph(f"{st.session_state.rendite_eigenkapital:.2f}%", styles['KpiValue']))
        kpi_story.append(Spacer(1, 0.2*inch))
        kpi_story.append(Paragraph("Durschnittliche Miete pro m2 (CHF)", styles['KpiTitle']))
        kpi_story.append(Paragraph(f"{st.session_state.miete_pro_m2:.2f}", styles['KpiValue']))

        # Create Summary column
        summary_story = []
        summary_story.append(Paragraph(st.session_state.get('generated_blockquote', "..."), styles['Quote']))
        summary_story.append(Spacer(1, 0.2*inch))
        summary_story.extend(markdown_to_flowables(st.session_state.generated_summary, styles))

        # Combine into a two-column table
        summary_table_data = [[summary_story, kpi_story]]
        summary_table = Table(summary_table_data, colWidths=[doc.width * 0.7, doc.width * 0.3])
        summary_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.25*inch))


        # --- Financial Tables ---
        ertraege_data = full_financial_data.get('Erträge', {})
        aufwand_data = full_financial_data.get('Aufwand', {})
        aktiva_data = full_financial_data.get('Aktiva', {})
        passiva_data = full_financial_data.get('Passiva', {})

        # Calculate available width for two tables side-by-side
        available_width = doc.width # This is the content width of the page
        table_half_width = (available_width - 0.25*inch) / 2 # Subtract some space for gap between tables

        # --- Erfolgsrechnung Section ---
        story.append(PageBreak())
        story.append(Paragraph("Erfolgsrechnung", styles['H1']))
        story.append(Spacer(1, 0.2*inch)) # Added spacer

        # Create individual tables with calculated widths
        ertraege_table = _create_financial_table(ertraege_data, ['Beschreibung', 'Betrag (CHF)'], table_half_width, styles)
        aufwand_table = _create_financial_table(aufwand_data, ['Beschreibung', 'Betrag (CHF)'], table_half_width, styles)

        # Create a table to hold the H2 titles
        h2_titles_data_erfolgsrechnung = [
            [Paragraph("Erträge", styles['H2']), Paragraph("Aufwand", styles['H2'])]
        ]
        h2_titles_table_erfolgsrechnung = Table(h2_titles_data_erfolgsrechnung, colWidths=[table_half_width, table_half_width])
        h2_titles_table_erfolgsrechnung.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (0,0), 0),
            ('RIGHTPADDING', (0,0), (0,0), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(h2_titles_table_erfolgsrechnung)
        story.append(Spacer(1, 0.1*inch)) # Small spacer between H2 titles and tables

        # Create a table to hold the two financial tables side-by-side
        combined_erfolgsrechnung_data = [[ertraege_table, aufwand_table]]
        combined_erfolgsrechnung_table = Table(combined_erfolgsrechnung_data, colWidths=[table_half_width, table_half_width])
        combined_bilanz_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (0,0), 0),
            ('RIGHTPADDING', (0,0), (0,0), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(combined_bilanz_table)
        story.append(Spacer(1, 0.25*inch))

        # --- Waterfall Chart ---
        story.append(PageBreak())
        story.append(Paragraph("Finanzanalyse", styles['H1']))
        waterfall_x, waterfall_y, waterfall_measure = _get_waterfall_chart_data(full_financial_data)
        waterfall_fig = create_waterfall_chart(waterfall_x, waterfall_y, waterfall_measure)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_chart:
            chart_filename = tmp_chart.name
            waterfall_fig.write_image(chart_filename, scale=2)
        
        chart_image = Image(chart_filename, width=7*inch, height=4*inch)
        chart_image.hAlign = 'CENTER'
        story.append(chart_image)
        story.append(Spacer(1, 0.25*inch))
        story.append(Paragraph("Detaillierte Erklärung", styles['H2']))
        story.extend(markdown_to_flowables(st.session_state.waterfall_explanation, styles))

        # --- Budget Proposal ---
        story.append(PageBreak())
        story.append(Paragraph("Budgetvorschlag für das kommende Jahr", styles['H1']))
        story.append(Spacer(1, 0.2*inch)) # Added spacer
        story.extend(markdown_to_flowables(st.session_state.generated_budget, styles))

        doc.build(story, onFirstPage=lambda c, d: None, onLaterPages=lambda c, d: _add_page_footer(c, d, logo_path))
    finally:
        # Clean up temporary files
        if hero_image_path and os.path.exists(hero_image_path):
            os.remove(hero_image_path)
        if chart_filename and os.path.exists(chart_filename):
            os.remove(chart_filename)

    buffer.seek(0)
    return buffer.getvalue()


def display_html_report(report_title, image_file, full_financial_data):
    """
    Displays the HTML report.
    """
    dynamic_date_range = "Daten nicht verfügbar"
    if "Erfolgsrechnung" in full_financial_data and not full_financial_data["Erfolgsrechnung"].empty:
        try:
            date_range_value = full_financial_data["Erfolgsrechnung"].iloc[1, 1]
            if isinstance(date_range_value, str):
                dynamic_date_range = date_range_value
        except (IndexError, KeyError):
            st.warning("Could not extract date range from Erfolgsrechnung. Using default.")

    dynamic_primary_market_area = "Daten nicht verfügbar"
    if "Erfolgsrechnung" in full_financial_data and not full_financial_data["Erfolgsrechnung"].empty:
        try:
            primary_market_area_value = full_financial_data["Erfolgsrechnung"].iloc[2, 1]
            if isinstance(primary_market_area_value, str):
                dynamic_primary_market_area = primary_market_area_value
        except (IndexError, KeyError):
            st.warning("Could not extract primary market area from Erfolgsrechnung. Using default.")

    # --- Waterfall Chart Data Extraction for HTML ---
    waterfall_x, waterfall_y, waterfall_measure = _get_waterfall_chart_data(full_financial_data)

    waterfall_fig = create_waterfall_chart(waterfall_x, waterfall_y, waterfall_measure)
    waterfall_html = waterfall_fig.to_html(full_html=False, include_plotlyjs='cdn')

    # --- Robust Path Construction ---
    script_dir = os.path.dirname(__file__)
    templates_dir = os.path.abspath(os.path.join(script_dir, '..', 'templates'))
    
    logo_path = os.path.join(templates_dir, 'LELIA_LOGO_L_W.png')
    css_path = os.path.join(templates_dir, 'tailwind.css')

    logo_base64 = image_to_base64(logo_path)
    hero_image_base64 = base64.b64encode(image_file.getbuffer()).decode()
    
    try:
        with open(css_path) as f:
            css_content = f.read()
    except FileNotFoundError:
        css_content = ""
        st.warning("tailwind.css not found.")

    def markdown_to_html(md):
        return markdown.markdown(md)

    env = Environment(loader=FileSystemLoader(template_dir))
    env.filters['currency'] = format_currency
    env.filters['markdown'] = markdown_to_html
    template = env.get_template('mgmtreporting.html')

    ertraege_data = full_financial_data.get('Erträge', {})
    aufwand_data = full_financial_data.get('Aufwand', {})
    aktiva_data = full_financial_data.get('Aktiva', {})
    passiva_data = full_financial_data.get('Passiva', {})

    report_context = {
        'report_title': dynamic_primary_market_area,
        'primary_market_area': '',
        'date_range': dynamic_date_range,
        'logo_base64': logo_base64,
        'hero_image_base64': hero_image_base64,
        'css_content': css_content,
        'ertraege': ertraege_data,
        'aufwand': aufwand_data,
        'aktiva': aktiva_data,
        'passiva': passiva_data,
        'current_year': datetime.now().year,
        'waterfall_chart_html': waterfall_html,
        'blockquote': st.session_state.generated_blockquote,
        'executivesummary': st.session_state.generated_summary,
        'waterfall_explanation_html': st.session_state.waterfall_explanation,
        'budget_proposal_html': st.session_state.generated_budget,
        'leerstand': st.session_state.leerstand,
        'rendite_eigenkapital': st.session_state.rendite_eigenkapital,
        'miete_pro_m2': st.session_state.miete_pro_m2,
    }

    html_content = template.render(report_context)
    st.components.v1.html(html_content, height=800, scrolling=True)

    with st.sidebar:
        st.subheader("PDF Report Download")
        try:
            pdf_bytes = pdf_from_reportlab(image_file, full_financial_data, dynamic_date_range, dynamic_primary_market_area)
            st.download_button(
                label="Download PDF Report",
                icon=":material/build:",
                data=pdf_bytes,
                file_name="management_report.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"Error generating PDF: {e}")
