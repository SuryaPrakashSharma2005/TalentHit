import re
from typing import Dict, Optional


DEGREE_KEYWORDS = {
    "b.tech": ["b.tech", "btech", "bachelor of technology"],
    "m.tech": ["m.tech", "mtech", "master of technology"],
    "b.e": ["b.e", "be", "bachelor of engineering"],
    "m.e": ["m.e", "me", "master of engineering"],
    "mca": ["mca", "master of computer applications"],
    "bca": ["bca", "bachelor of computer applications"],
    "b.sc": ["b.sc", "bsc", "bachelor of science"],
    "m.sc": ["m.sc", "msc", "master of science"],
    "phd": ["phd", "doctorate"],
    "diploma": ["diploma"]
}


def extract_education(text: str) -> Dict[str, Optional[str]]:
    """
    Extract education details from resume text.

    Args:
        text (str): Cleaned resume text

    Returns:
        dict: {degree, branch, institution}
    """
    if not text:
        return {
            "degree": None,
            "branch": None,
            "institution": None
        }

    degree = None
    branch = None
    institution = None

    # ---- Degree detection ----
    for canonical, variants in DEGREE_KEYWORDS.items():
        for v in variants:
            if v in text:
                degree = canonical.upper()
                break
        if degree:
            break

    # ---- Branch detection ----
    branch_patterns = [
        r"computer science(?: engineering)?",
        r"information technology",
        r"electronics(?: and communication)?",
        r"mechanical engineering",
        r"civil engineering",
        r"electrical engineering"
    ]

    for pattern in branch_patterns:
        match = re.search(pattern, text)
        if match:
            branch = match.group(0).title()
            break

    # ---- Institution detection ----
    inst_patterns = [
        r"university of [a-z\s]+",
        r"[a-z\s]+ university",
        r"[a-z\s]+ institute of technology",
        r"[a-z\s]+ college"
    ]

    for pattern in inst_patterns:
        match = re.search(pattern, text)
        if match:
            institution = match.group(0).title()
            break

    return {
        "degree": degree,
        "branch": branch,
        "institution": institution
    }
