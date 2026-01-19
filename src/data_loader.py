import pandas as pd
import os
import re

def parse_iso_currency(value):
    """
    If a string contains an ISO 4217 currency code, this function extracts the
    adjacent number (positive or negative), converts it to a float rounded to 2 decimal places, 
    and returns the float. Otherwise, it returns the original value.
    """
    if not isinstance(value, str):
        return value

    # Regex to find an ISO 4217 code and an adjacent number that may be negative.
    iso_pattern = r'\b([A-Z]{3})\b'
    # The number pattern now allows an optional leading hyphen and spaces.
    number_pattern = r'-?\s*[\d\',.]+'

    match = re.search(fr'{iso_pattern}\s*({number_pattern})', value)
    if match:
        number_str = match.group(2)
    else:
        match = re.search(fr'({number_pattern})\s*{iso_pattern}', value)
        if match:
            number_str = match.group(1)
        else:
            return value

    # Clean and convert the extracted number string.
    number_str = number_str.strip()
    try:
        # Attempt 1: US/Swiss format. Remove spaces between sign and number.
        cleaned_str = number_str.replace("'", "").replace(",", "").replace(" ", "")
        return round(float(cleaned_str), 2)
    except ValueError:
        # Attempt 2: European format.
        try:
            cleaned_str = number_str.replace("'", "").replace(".", "").replace(",", ".").replace(" ", "")
            return round(float(cleaned_str), 2)
        except (ValueError, TypeError):
            return value

def parse_erfolgsrechnung(df):
    """
    Parses the Erfolgsrechnung DataFrame to extract Erträge and Aufwand dictionaries.
    """
    ertraege_dict = {}
    aufwand_dict = {}
    
    # Find start rows and columns for "Erträge" and "Aufwände" independently
    loc_ertraege = {'row': -1, 'col': -1}
    loc_aufwand = {'row': -1, 'col': -1}

    for row_idx in range(len(df)):
        for col_idx in range(len(df.columns)):
            cell_value = df.iloc[row_idx, col_idx]
            if isinstance(cell_value, str):
                if "Erträge" in cell_value:
                    loc_ertraege['row'] = row_idx
                    loc_ertraege['col'] = col_idx
                elif "Aufwände" in cell_value:
                    loc_aufwand['row'] = row_idx
                    loc_aufwand['col'] = col_idx

    def extract_data(start_row, start_col_index, data_dict):
        if start_row == -1 or start_col_index == -1:
            return

        last_was_numeric = False
        for i in range(start_row, len(df)):
            cell_content = df.iloc[i, start_col_index]
            
            # Stopping condition
            if pd.isna(cell_content) or cell_content == '':
                if last_was_numeric:
                    break
                else:
                    continue

            # Rule A: Alphanumeric labels
            if isinstance(cell_content, str) and not cell_content.strip().isdigit():
                key = cell_content.strip()
                value_cell = df.iloc[i, start_col_index + 3]
                try:
                    data_dict[key] = float(value_cell)
                except (ValueError, TypeError):
                    pass # Or handle error appropriately
                last_was_numeric = False

            # Rule B: 4-digit numeric codes
            elif isinstance(cell_content, str) and cell_content.strip().isdigit() and len(cell_content.strip()) == 4:
                key = df.iloc[i, start_col_index + 1].strip()
                value_cell = df.iloc[i, start_col_index + 3]
                try:
                    data_dict[key] = float(value_cell)
                except (ValueError, TypeError):
                    pass # Or handle error appropriately
                last_was_numeric = True
            
            # Handle cases where numeric codes might be read as integers
            elif isinstance(cell_content, (int, float)) and 1000 <= cell_content < 10000:
                key = df.iloc[i, start_col_index + 1].strip()
                value_cell = df.iloc[i, start_col_index + 3]
                try:
                    data_dict[key] = float(value_cell)
                except (ValueError, TypeError):
                    pass # Or handle error appropriately
                last_was_numeric = True

    if loc_ertraege['row'] != -1:
        extract_data(loc_ertraege['row'], loc_ertraege['col'], ertraege_dict)
    if loc_aufwand['row'] != -1:
        extract_data(loc_aufwand['row'], loc_aufwand['col'], aufwand_dict)
    
    return ertraege_dict, aufwand_dict

def parse_bilanz(df):
    """
    Parses the Bilanz DataFrame to extract Aktiva and Passiva dictionaries.
    """
    aktiva_dict = {}
    passiva_dict = {}

    loc_aktiva = {'row': -1, 'col': -1}
    loc_passiva = {'row': -1, 'col': -1}

    for row_idx in range(len(df)):
        for col_idx in range(len(df.columns)):
            cell_value = df.iloc[row_idx, col_idx]
            if isinstance(cell_value, str):
                if "Aktiva" in cell_value:
                    loc_aktiva['row'] = row_idx
                    loc_aktiva['col'] = col_idx
                elif "Passiva" in cell_value:
                    loc_passiva['row'] = row_idx
                    loc_passiva['col'] = col_idx
    
    def extract_data(start_row, start_col_index, data_dict):
        if start_row == -1 or start_col_index == -1:
            return

        empty_row_counter = 0
        for i in range(start_row, len(df)):
            cell_content = df.iloc[i, start_col_index]

            if pd.isna(cell_content) or cell_content == '':
                if empty_row_counter > 0: # Increment if we've already seen an empty row
                    empty_row_counter += 1
                else: # Start counting on first empty row after content
                    last_row_with_content_check = df.iloc[i-1, start_col_index]
                    if not (pd.isna(last_row_with_content_check) or last_row_with_content_check == ''):
                         empty_row_counter = 1
                
                if empty_row_counter >= 3:
                    break
                continue
            
            empty_row_counter = 0 # Reset counter if content is found

            # Rule A: Alphanumeric labels
            if isinstance(cell_content, str) and not cell_content.strip().isdigit():
                key = cell_content.strip()
                try:
                    value = float(df.iloc[i, start_col_index + 3])
                    data_dict[key] = value
                except (ValueError, TypeError):
                    pass

            # Rule B: 4-digit numeric codes
            elif (isinstance(cell_content, str) and cell_content.strip().isdigit() and len(cell_content.strip()) == 4) or \
                 (isinstance(cell_content, (int, float)) and 1000 <= cell_content < 10000):
                key = df.iloc[i, start_col_index + 1].strip()
                try:
                    value = float(df.iloc[i, start_col_index + 3])
                    data_dict[key] = value
                except (ValueError, TypeError):
                    pass

    if loc_aktiva['row'] != -1:
        extract_data(loc_aktiva['row'], loc_aktiva['col'], aktiva_dict)
    if loc_passiva['row'] != -1:
        extract_data(loc_passiva['row'], loc_passiva['col'], passiva_dict)
        
    return aktiva_dict, passiva_dict

def load_financial_data(uploaded_file):
    """Loads, trims, and cleans financial data from an uploaded Excel file."""
    xls = pd.ExcelFile(uploaded_file)
    financial_data = {}

    def process_dataframe(df):
        """Cleans and processes the dataframe."""
        df = df.dropna(how='all', axis=0).dropna(how='all', axis=1)
        df = df.map(parse_iso_currency)
        df = df.fillna('')
        
        new_columns = [f'Spalte {i + 1}' for i in range(len(df.columns))]
        df.columns = new_columns
        
        return df

    if "Bilanz" in xls.sheet_names:
        bilanz_df = pd.read_excel(xls, "Bilanz", header=None)
        processed_bilanz_df = process_dataframe(bilanz_df)
        financial_data["Bilanz"] = processed_bilanz_df.astype(str).replace('nan', '')
        
        aktiva, passiva = parse_bilanz(processed_bilanz_df)
        financial_data["Aktiva"] = aktiva
        financial_data["Passiva"] = passiva

    if "Erfolgsrechnung" in xls.sheet_names:
        erfolgsrechnung_df = pd.read_excel(xls, "Erfolgsrechnung", header=None)
        processed_erfolgsrechnung_df = process_dataframe(erfolgsrechnung_df)
        
        ertraege, aufwand = parse_erfolgsrechnung(processed_erfolgsrechnung_df)
        financial_data["Erträge"] = ertraege
        financial_data["Aufwand"] = aufwand
        
        # For display purposes, convert all data to strings to avoid mixed-type columns
        # that can cause issues with Arrow serialization in Streamlit.
        financial_data["Erfolgsrechnung"] = processed_erfolgsrechnung_df.astype(str).replace('nan', '')
        
    return financial_data
