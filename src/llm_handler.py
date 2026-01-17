import streamlit as st
import google.genai as genai
import re

def generate_summary_with_gemini(user_notes, financial_data):
    """
    Generates an executive summary and a blockquote using the Gemini API, ensuring the output is in German.
    """
    # Configure the Gemini API
    try:
        genai.configure(api_key=st.secrets["GEM_API"])
    except (KeyError, AttributeError):
        st.error("Gemini API key not found. Please add it to your Streamlit secrets.")
        return "Error: API Key not configured.", "Could not generate summary."

    # Create the model
    model = genai.GenerativeModel('gemini-pro')

    # Construct the prompt
    prompt = f"""
    You are a financial analyst for a Swiss real estate firm. Your task is to write a professional executive summary for a property management report.
    The entire response must be in German.

    Based on the user's notes and the financial data provided, please generate two pieces of text:
    1.  A short, impactful quote for the blockquote section (in German).
    2.  A detailed paragraph for the main executive summary (in German).

    USER NOTES:
    ---
    {user_notes}
    ---

    FINANCIAL DATA:
    ---
    Erträge (Income): {financial_data.get('Erträge', {})}
    Aufwände (Expenses): {financial_data.get('Aufwand', {})}
    Aktiva (Assets): {financial_data.get('Aktiva', {})}
    Passiva (Liabilities): {financial_data.get('Passiva', {})}
    ---

    Please format your response exactly as follows, with no additional text or explanations:

    [BLOCKQUOTE]
    Your generated German quote here.
    [END_BLOCKQUOTE]

    [EXECUTIVE_SUMMARY]
    Your generated German summary paragraph here.
    [END_EXECUTIVE_SUMMARY]
    """

    try:
        # Generate the content
        response = model.generate_content(prompt)
        
        # Parse the response
        blockquote_match = re.search(r'\[BLOCKQUOTE\](.*?)\[END_BLOCKQUOTE\]', response.text, re.DOTALL)
        summary_match = re.search(r'\[EXECUTIVE_SUMMARY\](.*?)\[END_EXECUTIVE_SUMMARY\]', response.text, re.DOTALL)

        blockquote = blockquote_match.group(1).strip() if blockquote_match else "Konnte Zitat nicht analysieren."
        summary = summary_match.group(1).strip() if summary_match else "Konnte Zusammenfassung nicht analysieren."

        return blockquote, summary

    except Exception as e:
        st.error(f"An error occurred while calling the Gemini API: {e}")
        return "Fehler bei der Generierung.", str(e)
