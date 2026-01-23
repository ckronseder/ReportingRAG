import streamlit as st
import google.genai as genai
import google.genai.types as types
import re
import os

# --- Centralized API Configuration ---

# Define the model name as a constant to ensure consistency and ease of updates.
MODEL_NAME = 'gemini-2.5-flash'

def get_gemini_client():
    """Initializes and returns the Gemini client, handling errors."""
    api_key = os.environ.get("GEM_API") or st.secrets.get("GEM_API")
    if not api_key:
        st.error("GEMINI_API_KEY not found. Please set it in your environment or secrets.")
        return None
    try:
        client = genai.Client(api_key=api_key)
        return client
    except Exception as e:
        st.error(f"Failed to configure Gemini API: {e}")
        return None


def generate_summary_with_gemini(user_notes, financial_data):
    """Generates an executive summary and a blockquote using the Gemini API."""
    client = get_gemini_client()
    if not client:
        return "Fehler: API-Client konnte nicht initialisiert werden.", "Zusammenfassung konnte nicht generiert werden."

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
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=types.Part.from_text(text=prompt),
            config=types.GenerateContentConfig(
                temperature=0.1,
                top_p=0.95,
                top_k=20,
            ),
        )

        # Parse the response
        blockquote_match = re.search(r'\[BLOCKQUOTE\](.*?)\[END_BLOCKQUOTE\]', response.text, re.DOTALL)
        summary_match = re.search(r'\[EXECUTIVE_SUMMARY\](.*?)\[END_EXECUTIVE_SUMMARY\]', response.text, re.DOTALL)

        blockquote = blockquote_match.group(1).strip() if blockquote_match else "Konnte Zitat nicht analysieren."
        summary = summary_match.group(1).strip() if summary_match else "Konnte Zusammenfassung nicht analysieren."

        return blockquote, summary

    except Exception as e:
        st.error(f"An error occurred while calling the Gemini API: {e}")
        return "Fehler bei der Generierung.", str(e)

def generate_waterfall_explanation(aufwand_data):
    """
    Generates an explanation for the waterfall chart based on the Aufwand data.
    """
    client = get_gemini_client()
    if not client:
        return "Fehler bei der Generierung der Wasserfall-Erklärung."

    prompt = f"""
    You are a financial analyst for a Swiss real estate firm. Your task is to write a short, professional explanation for the waterfall chart based on the provided expense data.
    The entire response must be in German.

    The waterfall chart shows a breakdown of the total expenses ('Aufwände'). Please explain the main drivers of the expenses, highlighting the most significant categories.

    EXPENSE DATA (Aufwand):
    ---
    {aufwand_data}
    ---

    Please provide a concise, short, one-paragraph explanation and wrap your response in [EXPLANATION] and [END_EXPLANATION] tags.
    """

    try:
        # Generate the content
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=types.Part.from_text(text=prompt),
            config=types.GenerateContentConfig(
                temperature=0.1,
                top_p=0.95,
                top_k=20,
            ),
        )
        
        explanation_match = re.search(r'\[EXPLANATION\](.*?)\[END_EXPLANATION\]', response.text, re.DOTALL)
        explanation = explanation_match.group(1).strip() if explanation_match else "Konnte Erklärung nicht analysieren."
        
        return explanation
        
    except Exception as e:
        st.error(f"An error occurred while calling the Gemini API for the waterfall explanation: {e}")
        return "Fehler bei der Generierung der Wasserfall-Erklärung."

def generate_budget_proposal(budget_notes, financial_data):
    """
    Generates a budget proposal for the upcoming year.
    """
    client = get_gemini_client()
    if not client:
        return "Fehler bei der Generierung des Budgetvorschlags."

    prompt = f"""
    You are a strategic financial planner for a Swiss real estate firm. Your task is to create a budget proposal for the upcoming year.
    The entire response must be in German.

    Based on the user's notes and the financial data from the past period, generate a structured budget proposal. Do NOT invent any additional information, data or numbers. 

    USER NOTES FOR BUDGET:
    ---
    {budget_notes}
    ---

    PAST FINANCIAL DATA:
    ---
    Erträge (Income): {financial_data.get('Erträge', {})}
    Aufwände (Expenses): {financial_data.get('Aufwand', {})}
    ---

    Please provide a concise and short answer, and wrap your entire response in [BUDGET] and [END_BUDGET] tags.
    """

    try:
        # Generate the content
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=types.Part.from_text(text=prompt),
            config=types.GenerateContentConfig(
                temperature=0.1,
                top_p=0.95,
                top_k=20,
            ),
        )
        
        budget_match = re.search(r'\[BUDGET\](.*?)\[END_BUDGET\]', response.text, re.DOTALL)
        budget = budget_match.group(1).strip() if budget_match else "Konnte Budgetvorschlag nicht analysieren."
        
        return budget
    except Exception as e:
        st.error(f"Fehler bei der Generierung des Budgetvorschlags: {e}")
        return "Fehler bei der Generierung des Budgetvorschlags."
