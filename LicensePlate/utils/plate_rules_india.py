import re
STATE_CODES = {
    "AN","AP","AR","AS","BR","CH","CG","DD","DL","DN","GA","GJ",
    "HP","HR","JH","JK","KA","KL","LA","LD","MH","ML","MN","MP",
    "MZ","NL","OD","PB","PY","RJ","SK","TN","TR","TS","UK","UP","WB"
}

INDIAN_PLATE_REGEX = r'^[A-Z]{2}[0-9]{1,2}[A-Z]{1,2}[0-9]{4}$'


def normalize_indian_plate(text):
    text = text.upper()
    text = re.sub(r'[^A-Z0-9]', '', text)

    replacements = {
        'O': '0',
        'I': '1',
        'Z': '2',
        'S': '5',
        'B': '8'
    }

    return ''.join(replacements.get(c, c) for c in text)


def validate_indian_plate(text):
    if not re.match(INDIAN_PLATE_REGEX, text):
        return False
    return text[:2] in STATE_CODES
