import os
import streamlit as st

# --- Environment Fix for LaTeX on macOS ---
# This must be at the very top. It tells the script where to find the 'xelatex' engine.
# The standard path for MacTeX is /Library/TeX/texbin.
latex_path = '/Library/TeX/texbin'
if latex_path not in os.environ['PATH']:
    os.environ['PATH'] = latex_path + ':' + os.environ['PATH']
# --- End of Environment Fix ---

from data_loader import load_financial_data
from ui import display_html_report
from llm_handler import generate_summary_with_gemini, generate_waterfall_explanation, generate_budget_proposal

# Initialize session state for view management
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = 'data_explorer' # or 'report_view'
if 'uploaded_report' not in st.session_state:
    st.session_state.uploaded_report = None
if 'uploaded_image' not in st.session_state:
    st.session_state.uploaded_image = None
if 'generated_blockquote' not in st.session_state:
    st.session_state.generated_blockquote = "Der Markt erlebte im letzten Quartal eine beispiellose Liquidität..."
if 'generated_summary' not in st.session_state:
    st.session_state.generated_summary = "Dank eines günstigen wirtschaftlichen Umfelds..."
if 'waterfall_explanation' not in st.session_state:
    st.session_state.waterfall_explanation = "Explanation of the waterfall chart will be generated here."
if 'generated_budget' not in st.session_state:
    st.session_state.generated_budget = "Budget proposal will be generated here."


def main():
    st.set_page_config(layout="wide")
    st.title("LELIA Reporting")

    # Inject custom CSS for sidebar color
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {
            background-color: #ff6b00; /* LeliaOrange */
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # --- Sidebar Setup ---
    st.sidebar.image("../templates/LELIA_LOGO_L_W.png", width=200)
    st.sidebar.title("Navigation")
    st.sidebar.header("Ansicht")

    # --- View Switching Logic ---
    if st.session_state.view_mode == 'data_explorer':
        col1, col2 = st.columns(2)
        
        with col1:
            st.header("1. Excel-Report hochladen")
            uploaded_report = st.file_uploader("Wählen Sie eine XLSX-Datei", type="xlsx", key="report_uploader")
            if uploaded_report:
                st.session_state.uploaded_report = uploaded_report
                financial_data = load_financial_data(uploaded_report)
                st.session_state['full_financial_data'] = financial_data
                st.success("Datei erfolgreich geladen und verarbeitet.")
                if "Erfolgsrechnung" in financial_data:
                    st.dataframe(financial_data["Erfolgsrechnung"].head())

        with col2:
            st.header("2. Deckblatt-Bild hochladen")
            uploaded_image = st.file_uploader("Wählen Sie ein Bild", type=["png", "jpg", "jpeg"], key="image_uploader")
            if uploaded_image:
                st.session_state.uploaded_image = uploaded_image
                st.image(uploaded_image, caption="Vorschau des Deckblatt-Bildes", width=300)

        st.header("3. Anmerkungen für die Zusammenfassung")
        user_notes = st.text_area("Fügen Sie hier Ihre Notizen ein:", height=150, key="summary_notes")

        st.header("4. Budget für das kommende Jahr")
        budget_notes = st.text_area("Fügen Sie hier Ihre Budgetvorschläge ein:", height=150, key="budget_notes")

        if st.sidebar.button("Bericht erstellen"):
            if st.session_state.uploaded_report and st.session_state.uploaded_image:
                with st.spinner("Generiere Zusammenfassung mit Gemini..."):
                    financial_data = st.session_state.get('full_financial_data', {})
                    blockquote, summary = generate_summary_with_gemini(user_notes, financial_data)
                    st.session_state.generated_blockquote = blockquote
                    st.session_state.generated_summary = summary
                    
                    aufwand_data = financial_data.get('Aufwand', {})
                    st.session_state.waterfall_explanation = generate_waterfall_explanation(aufwand_data)

                    st.session_state.generated_budget = generate_budget_proposal(budget_notes, financial_data)

                st.session_state.view_mode = 'report_view'
                st.rerun()
            else:
                st.warning("Bitte laden Sie sowohl einen Excel-Report als auch ein Bild hoch.")

    elif st.session_state.view_mode == 'report_view':
        if st.sidebar.button("Zurück zum Daten-Explorer"):
            st.session_state.view_mode = 'data_explorer'
            st.rerun()

        report_file = st.session_state.get('uploaded_report')
        image_file = st.session_state.get('uploaded_image')

        if report_file and image_file:
            full_financial_data = st.session_state.get('full_financial_data', {})
            display_html_report(report_file.name, image_file, full_financial_data)
        else:
            st.warning("Keine Dateien gefunden. Bitte gehen Sie zurück und laden Sie die Dateien hoch.")
            if st.button("Zurück zum Daten-Explorer"):
                st.session_state.view_mode = 'data_explorer'
                st.rerun()

if __name__ == "__main__":
    main()
