import re

# EU country codes (partial, common ones)
EU_COUNTRY_CODES = {
    "D", "F", "NL", "B", "L", "I", "E", "P", "A", "CH", "S", "DK", "IRL", "EST", "LV", "LT", "PL", "CZ", "SK", "H"
}

def normalize_eu_plate(text):
    """
    Removes spaces and dashes, keeps uppercase letters and digits.
    """
    text = text.upper()
    text = re.sub(r'[^A-Z0-9]', '', text)
    return text

def remove_country_code(text):
    """
    Checks for EU country code at the start and removes it.
    Returns (country_code, plate_number)
    """
    for code in sorted(EU_COUNTRY_CODES, key=lambda x: -len(x)):
        if text.startswith(code):
            return code, text[len(code):]
    return None, text
