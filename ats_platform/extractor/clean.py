import re


def clean_text(text: str) -> str:
    if not text:
        return ""

    text = text.lower()
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()
