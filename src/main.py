import os
import streamlit as st

from data_loader import load_financial_data
from ui import display_html_report
from llm_handler import generate_summary_with_gemini, generate_waterfall_explanation, generate_budget_proposal

# --- Session State Initialization ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'report_generated' not in st.session_state:
    st.session_state.report_generated = False
if 'full_financial_data' not in st.session_state:
    st.session_state.full_financial_data = None
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
if 'leerstand' not in st.session_state:
    st.session_state.leerstand = 0.0
if 'rendite_eigenkapital' not in st.session_state:
    st.session_state.rendite_eigenkapital = 0.0
if 'miete_pro_m2' not in st.session_state:
    st.session_state.miete_pro_m2 = 0.0


def authenticate_user(username, password):
    """Checks if the provided username and password match any in the secrets."""
    for user_creds in st.secrets["credentials"]:
        if user_creds["username"] == username and user_creds["password"] == password:
            return True
    return False

def login_page():
    """Displays the login form."""
    st.title("Login")
    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")
    if st.button("Login"):
        if authenticate_user(username, password):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Ungültiger Benutzername oder Passwort")

def logout():
    st.session_state.authenticated = False
    st.session_state.report_generated = False # Reset report view on logout
    st.rerun()

def update_summary():
    st.session_state.generated_summary = st.session_state.summary_input

def update_budget():
    st.session_state.generated_budget = st.session_state.budget_input

def update_leerstand():
    st.session_state.leerstand = st.session_state.leerstand_input

def update_rendite_eigenkapital():
    st.session_state.rendite_eigenkapital = st.session_state.rendite_eigenkapital_input

def update_miete_pro_m2():
    st.session_state.miete_pro_m2 = st.session_state.miete_pro_m2_input

def main():
    st.set_page_config(layout="wide")

    if not st.session_state.authenticated:
        login_page()
        return

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
    with st.sidebar:
        # Make path relative to the current script file for robustness
        script_dir = os.path.dirname(__file__)
        logo_path = os.path.join(script_dir, "..", "templates", "LELIA_LOGO_L_W.png")
        st.image(logo_path, width=200)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.title("Einstellungen")
        with col2:
            st.button("Logout", icon=":material/logout:", on_click=logout) # Added icon

        st.header("1. Dateien hochladen")
        uploaded_report = st.file_uploader("Excel-Report", type="xlsx", key="report_uploader")
        uploaded_image = st.file_uploader("Deckblatt-Bild", type=["png", "jpg", "jpeg"], key="image_uploader")

        if uploaded_report:
            st.session_state.full_financial_data = load_financial_data(uploaded_report)
        
        if uploaded_image:
            st.session_state.uploaded_image = uploaded_image

        st.header("2. Notizen für LLM")
        user_notes = st.text_area("Anmerkungen für die Zusammenfassung:", height=150, key="summary_notes")
        budget_notes = st.text_area("Anmerkungen für das Budget:", height=150, key="budget_notes")

        if st.button("Bericht generieren", icon=":material/build:"): # Changed text and added icon
            if st.session_state.full_financial_data and st.session_state.uploaded_image:
                with st.spinner("Generiere Texte mit Gemini..."):
                    financial_data = st.session_state.get('full_financial_data', {})
                    blockquote, summary = generate_summary_with_gemini(user_notes, financial_data)
                    st.session_state.generated_blockquote = blockquote
                    st.session_state.generated_summary = summary
                    
                    aufwand_data = financial_data.get('Aufwand', {})
                    st.session_state.waterfall_explanation = generate_waterfall_explanation(aufwand_data)

                    st.session_state.generated_budget = generate_budget_proposal(budget_notes, financial_data)
                
                st.session_state.report_generated = True
                st.success("Texte wurden generiert!")
            else:
                st.warning("Bitte laden Sie sowohl einen Excel-Report als auch ein Bild hoch.")


    # --- Main Content Layout (Editor & Preview) ---
    if st.session_state.report_generated:
        editor_col, preview_col = st.columns([1, 2])

        with editor_col:
            st.header("Texte bearbeiten")
            
            st.subheader("Zusammenfassung")
            st.text_area(
                "Zusammenfassung bearbeiten", 
                value=st.session_state.generated_summary, 
                height=300,
                key="summary_input",
                on_change=update_summary
            )

            st.subheader("Budgetvorschlag für das kommende Jahr")
            st.text_area(
                "Budget bearbeiten", 
                value=st.session_state.generated_budget, 
                height=300,
                key="budget_input",
                on_change=update_budget
            )

            st.subheader("Wichtige Kennzahlen (KPIs)")
            st.number_input(
                "Leerstand (%)",
                min_value=0.0,
                max_value=100.0,
                value=st.session_state.leerstand,
                format="%.2f",
                key="leerstand_input",
                on_change=update_leerstand
            )
            st.number_input(
                "Rendite auf Eigenkapital (%)",
                min_value=-100.0,
                max_value=100.0,
                value=st.session_state.rendite_eigenkapital,
                format="%.2f",
                key="rendite_eigenkapital_input",
                on_change=update_rendite_eigenkapital
            )
            st.number_input(
                "Durschnittliche Miete pro m2 (CHF)",
                min_value=0.0,
                value=st.session_state.miete_pro_m2,
                format="%.2f",
                key="miete_pro_m2_input",
                on_change=update_miete_pro_m2
            )


        with preview_col:
            st.header("Live-Vorschau")
            display_html_report(
                "Live Report", # report_title is no longer used in the same way
                st.session_state.uploaded_image, 
                st.session_state.full_financial_data
            )
    else:
        st.info("Bitte laden Sie einen Excel-Report und ein Deckblatt-Bild in der Seitenleiste hoch und klicken Sie auf 'Bericht generieren', um zu beginnen.")


if __name__ == "__main__":
    main()
