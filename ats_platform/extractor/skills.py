from typing import List


# Canonical skill map (extend later)
SKILL_MAP = {
    "python": ["python"],
    "java": ["java"],
    "c++": ["c++", "cpp"],
    "javascript": ["javascript", "js"],
    "fastapi": ["fastapi"],
    "flask": ["flask"],
    "machine learning": ["machine learning", "ml"],
    "deep learning": ["deep learning", "dl"],
    "nlp": ["nlp", "natural language processing"],
    "sql": ["sql"],
    "postgresql": ["postgresql", "postgres"],
    "docker": ["docker"],
    "aws": ["aws", "amazon web services"],
}


def extract_skills(text: str) -> List[str]:
    """
    Extract skills from cleaned resume text.

    Args:
        text (str): Cleaned resume text (lowercase)

    Returns:
        List[str]: List of detected canonical skills
    """
    if not text:
        return []

    detected_skills = set()

    for canonical_skill, variants in SKILL_MAP.items():
        for variant in variants:
            if variant in text:
                detected_skills.add(canonical_skill)
                break

    return sorted(detected_skills)
