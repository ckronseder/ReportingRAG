import streamlit as st
import pandas as pd
from jinja2 import Environment, FileSystemLoader
import os
import base64
import locale
from datetime import datetime
import pypandoc
import tempfile
import re
import unicodedata # Import unicodedata
from visualizations import create_waterfall_chart
import markdown

def escape_latex(text):
    """
    Escape special LaTeX characters in a string meant for text content.
    Also normalizes Unicode to NFC.
    """
    if not isinstance(text, str):
        return text
    
    # Normalize to NFC to handle precomposed characters better
    text = unicodedata.normalize('NFC', text)

    conv = { # Corrected syntax here
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
        '\\': r'\textbackslash{}',
    }
    regex = re.compile('|'.join(re.escape(key) for key in sorted(conv.keys(), key=lambda item: - len(item))))
    return regex.sub(lambda match: conv[match.group()], text)

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

def _get_waterfall_chart_data(full_financial_data, for_latex=False):
    """
    Extracts data for the waterfall chart from the 'Aufwand' dictionary,
    showing a simplified, high-level breakdown.
    If for_latex is True, labels will be escaped for LaTeX.
    """
    waterfall_x = []
    waterfall_y = []
    waterfall_measure = []

    aufwand_data = full_financial_data.get("Aufwand", {})
    if not aufwand_data:
        st.warning("Aufwand data not available for waterfall chart.")
        return [], [], []

    # Define the keys for the main total and the final result
    AUFWANDE_KEY = "Aufwände"
    FINAL_RESULT_KEY = "Abschluss Erfolgsrechnung"

    # Ensure the main 'Aufwände' total exists
    if AUFWANDE_KEY not in aufwand_data:
        st.warning(f"'{AUFWANDE_KEY}' not found in Aufwand data.")
        return [], [], []

    # 1. Add the main "Aufwände" total as the starting absolute bar
    aufwande_total_value = aufwand_data[AUFWANDE_KEY]
    waterfall_x.append(escape_latex(AUFWANDE_KEY) if for_latex else AUFWANDE_KEY)
    waterfall_y.append(aufwande_total_value)
    waterfall_measure.append("absolute")

    # 2. Add the breakdown categories (keys without numbers) as relative bars
    for key, value in aufwand_data.items():
        # Skip the main total and the final result keys
        if key == AUFWANDE_KEY or key == FINAL_RESULT_KEY:
            continue
        
        # Add keys that do NOT contain numeric characters
        if not re.search(r'\d', key):
            waterfall_x.append(escape_latex(key) if for_latex else key)
            waterfall_y.append(-value) # Negative for breakdown
            waterfall_measure.append("relative")

    # 3. Add the final result bar
    if FINAL_RESULT_KEY in aufwand_data:
        final_result_value = aufwand_data[FINAL_RESULT_KEY]
        waterfall_x.append(escape_latex(FINAL_RESULT_KEY) if for_latex else FINAL_RESULT_KEY)
        waterfall_y.append(final_result_value)
        waterfall_measure.append("total")
    
    return waterfall_x, waterfall_y, waterfall_measure


def generate_pdf_with_pandoc(report_title, image_file, dynamic_date_range, dynamic_primary_market_area, full_financial_data):
    """Generates a full PDF report using Pandoc and a LaTeX template."""
    template_path = os.path.join('../templates', 'report_template.tex')
    logo_path = os.path.abspath(os.path.join('../templates', 'LELIA_LOGO_L_W.png'))
    
    temp_template_path = None
    chart_filename = None
    output_filename = None
    hero_image_path = None

    try:
        # Save uploaded image to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(image_file.name)[1]) as tmp_image:
            tmp_image.write(image_file.getbuffer())
            hero_image_path = tmp_image.name

        # --- Waterfall Chart Data Extraction ---
        waterfall_x, waterfall_y, waterfall_measure = _get_waterfall_chart_data(full_financial_data, for_latex=True)

        # --- Create and save the waterfall chart ---
        waterfall_fig = create_waterfall_chart(waterfall_x, waterfall_y, waterfall_measure)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_chart:
            chart_filename = tmp_chart.name
            waterfall_fig.write_image(chart_filename, scale=2)

        # --- Prepare Table LaTeX Strings using Pandas ---
        ertraege_data = full_financial_data.get('Erträge', {})
        aufwand_data = full_financial_data.get('Aufwand', {})
        aktiva_data = full_financial_data.get('Aktiva', {})
        passiva_data = full_financial_data.get('Passiva', {})

        def df_to_latex(df, column_format, numeric_columns):
            lines = []
            # Use tabularx for auto-wrapping text columns
            new_column_format = column_format.replace('l', 'X', 1)
            lines.append(f"\\begin{{tabularx}}{{\\linewidth}}{{{new_column_format}}}")
            
            header = " & ".join([f"\\textbf{{{escape_latex(col)}}}" for col in df.columns]) + " \\\\"
            lines.append("\\toprule")
            lines.append(header)
            lines.append("\\midrule")

            for i, row in df.iterrows():
                is_bold_row = isinstance(row.iloc[0], str) and not re.search(r'\d', row.iloc[0])
                if is_bold_row and i > 0:
                    lines.append("\\midrule")

                row_values = []
                for j, col_name in enumerate(df.columns):
                    cell_value = row.iloc[j]
                    formatted_cell = ''
                    if col_name in numeric_columns and pd.notna(cell_value):
                        formatted_cell = f"{cell_value:,.2f}"
                    elif pd.notna(cell_value):
                        formatted_cell = escape_latex(str(cell_value))
                    
                    if is_bold_row:
                        formatted_cell = f"{{\\bfseries {formatted_cell}}}"
                    row_values.append(formatted_cell)
                
                row_str = " & ".join(row_values) + " \\\\"
                if not is_bold_row:
                    row_str = f"\\small {row_str}"
                lines.append(row_str)

            lines.append("\\bottomrule")
            lines.append("\\end{tabularx}")
            return "\n".join(lines)

        ertraege_df = pd.DataFrame(list(ertraege_data.items()), columns=['Beschreibung', 'Betrag (CHF)'])
        aufwand_df = pd.DataFrame(list(aufwand_data.items()), columns=['Beschreibung', 'Betrag (CHF)'])
        aktiva_df = pd.DataFrame(list(aktiva_data.items()), columns=['Konto', 'Betrag (CHF)'])
        passiva_df = pd.DataFrame(list(passiva_data.items()), columns=['Konto', 'Betrag (CHF)'])

        ertraege_table_tex = df_to_latex(ertraege_df, "lr", ['Betrag (CHF)'])
        aufwand_table_tex = df_to_latex(aufwand_df, "lr", ['Betrag (CHF)'])
        aktiva_table_tex = df_to_latex(aktiva_df, "lr", ['Betrag (CHF)'])
        passiva_table_tex = df_to_latex(passiva_df, "lr", ['Betrag (CHF)'])

        # --- Pre-process Template ---
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()

        template_content = template_content.replace('$ertraege_table$', ertraege_table_tex)
        template_content = template_content.replace('$aufwand_table$', aufwand_table_tex)
        template_content = template_content.replace('$aktiva_table$', aktiva_table_tex)
        template_content = template_content.replace('$passiva_table$', passiva_table_tex)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.tex', mode='w', encoding='utf-8') as tmp_template:
            tmp_template.write(template_content)
            temp_template_path = tmp_template.name

        # --- Set up Pandoc Metadata (excluding tables) ---
        budget_proposal_latex = pypandoc.convert_text(
            st.session_state.get('generated_budget', "..."), 'latex', format='md', extra_args=['--wrap=none']
        )
        
        markdown_content = "" 
        metadata = {
            'title': escape_latex(dynamic_primary_market_area),
            'author': '',
            'date': escape_latex(dynamic_date_range),
            'logo': logo_path,
            'heroimage': hero_image_path,
            'blockquote': escape_latex(st.session_state.get('generated_blockquote', "Der Markt erlebte im letzten Quartal eine beispiellose Liquidität...")),
            'executivesummary': escape_latex(st.session_state.get('generated_summary', "Dank eines günstigen wirtschaftlichen Umfelds...")),
            'kpi1_title': escape_latex("Gesamtverkaufsvolumen"),
            'kpi1_value': escape_latex("CHF 1.2 Mrd."),
            'kpi1_desc': escape_latex("Bruttowert aller abgeschlossenen Transaktionen..."),
            'kpi2_title': escape_latex("J-O-J Volumenänderung"),
            'kpi2_value': escape_latex("+18.5%"),
            'kpi2_desc': escape_latex("Stärkstes Q4-Wachstum seit fünf Jahren."),
            'kpi3_title': escape_latex("Durchschnittspreis/m²"),
            'kpi3_value': escape_latex("CHF 1,850"),
            'kpi3_desc': escape_latex("Schlüsselindikator für Marktgesundheit..."),
            'waterfall_chart': chart_filename,
            'waterfall_explanation': escape_latex(st.session_state.get('waterfall_explanation', "...")),
            'budget_proposal': budget_proposal_latex,
        }
        
        pandoc_args = ['--template', temp_template_path, '--pdf-engine=pdflatex']
        for key, value in metadata.items():
            pandoc_args.extend([f'--metadata={key}:{value}'])

        # --- Generate PDF ---
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_pdf:
            output_filename = tmp_pdf.name

        pypandoc.convert_text(markdown_content, 'pdf', format='md', outputfile=output_filename, extra_args=pandoc_args)
        
        with open(output_filename, 'rb') as f:
            pdf_bytes = f.read()
            
        return pdf_bytes

    finally:
        # --- Cleanup ---
        if temp_template_path and os.path.exists(temp_template_path):
            os.remove(temp_template_path)
        if chart_filename and os.path.exists(chart_filename):
            os.remove(chart_filename)
        if output_filename and os.path.exists(output_filename):
            os.remove(output_filename)
        if hero_image_path and os.path.exists(hero_image_path):
            os.remove(hero_image_path)


def display_html_report(report_title, image_file, full_financial_data):
    """
    Displays the HTML report and provides a PDF download button using Pandoc.
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
    waterfall_x, waterfall_y, waterfall_measure = _get_waterfall_chart_data(full_financial_data, for_latex=False)

    waterfall_fig = create_waterfall_chart(waterfall_x, waterfall_y, waterfall_measure)
    waterfall_html = waterfall_fig.to_html(full_html=False, include_plotlyjs='cdn')

    template_dir = '../templates'
    
    logo_path = os.path.join(template_dir, 'LELIA_LOGO_L_W.png')
    css_path = os.path.join(template_dir, 'tailwind.css')

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
        'blockquote': st.session_state.get('generated_blockquote', "..."),
        'executivesummary': st.session_state.get('generated_summary', "..."),
        'waterfall_explanation_html': st.session_state.get('waterfall_explanation', "Explanation of the waterfall chart will be generated here."),
        'budget_proposal_html': st.session_state.get('generated_budget', "Budget proposal will be generated here."),
    }

    html_content = template.render(report_context)
    st.components.v1.html(html_content, height=800, scrolling=True)

    with st.sidebar:
        st.subheader("PDF Report Download")
        try:
            pdf_bytes = generate_pdf_with_pandoc(report_title, image_file, dynamic_date_range, dynamic_primary_market_area, full_financial_data)
            st.download_button(
                label="Download PDF Report",
                data=pdf_bytes,
                file_name="management_report.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"Error generating PDF: {e}")
