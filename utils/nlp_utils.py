from rapidfuzz import process
from dateutil import parser

# Synthetic doctor + location lists (should match your DB)
DOCTORS = ["Dr. Priya Rao", "Dr. Mehul Shah", "Dr. Ananya Iyer"]
LOCATIONS = ["MG Road Clinic", "HSR Layout Clinic", "Indiranagar Clinic"]

def normalize_doctor(input_text: str) -> str | None:
    """
    Fuzzy match doctor name input against known doctors.
    """
    if not input_text:
        return None
    match, score, _ = process.extractOne(input_text, DOCTORS)
    return match if score > 65 else None

def normalize_location(input_text: str) -> str | None:
    """
    Fuzzy match clinic location input against known locations.
    """
    if not input_text:
        return None
    match, score, _ = process.extractOne(input_text, LOCATIONS)
    return match if score > 60 else None

def parse_dob(input_text: str):
    """
    Parse flexible DOB formats into date object.
    """
    try:
        return parser.parse(input_text).date()
    except Exception:
        return None
