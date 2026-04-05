import re
from typing import Dict, Optional


EMAIL_REGEX = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
PHONE_REGEX = r"(\+?\d{1,3}[\s\-]?)?\d{10}"


def extract_personal_info(text: str) -> Dict[str, Optional[str]]:
    """
    Extract personal information from resume text.

    Args:
        text (str): Raw or cleaned resume text

    Returns:
        dict: {name, email, phone}
    """
    if not text:
        return {
            "name": None,
            "email": None,
            "phone": None
        }

    name = _extract_name(text)
    email = _extract_email(text)
    phone = _extract_phone(text)

    return {
        "name": name,
        "email": email,
        "phone": phone
    }


def _extract_email(text: str) -> Optional[str]:
    match = re.search(EMAIL_REGEX, text)
    return match.group(0) if match else None


def _extract_phone(text: str) -> Optional[str]:
    match = re.search(PHONE_REGEX, text)
    return match.group(0) if match else None

def _extract_name(text: str) -> Optional[str]:
    """
    Improved name extraction:
    - Skip section headers
    - Require at least two words
    - Alphabetic characters only
    """
    if not text:
        return None

    blacklist = {
        "name", "resume", "curriculum vitae", "cv",
        "profile", "summary", "contact", "personal information"
    }

    lines = text.splitlines()

    for line in lines[:10]:  # Only look at top of resume
        line = line.strip()
        if not line:
            continue

        lower = line.lower()

        # Skip headers
        if lower in blacklist:
            continue

        # Must contain only alphabets and spaces
        if not re.fullmatch(r"[A-Za-z ]{3,}", line):
            continue

        # Must have at least two words (first + last name)
        if len(line.split()) < 2:
            continue

        return line.title()

    return None

