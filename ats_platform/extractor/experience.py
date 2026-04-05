import re
from typing import List


def extract_experience_years(text: str) -> float:
    """
    Extract total years of experience from resume text.

    Args:
        text (str): Cleaned resume text

    Returns:
        float: Total years of experience
    """
    if not text:
        return 0.0

    years_found: List[float] = []

    # Match patterns like "3 years", "2.5 years", "4+ years"
    patterns = [
        r"(\d+(?:\.\d+)?)\s*\+?\s*years",
        r"experience\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*years"
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                years_found.append(float(match))
            except ValueError:
                continue

    return max(years_found) if years_found else 0.0
