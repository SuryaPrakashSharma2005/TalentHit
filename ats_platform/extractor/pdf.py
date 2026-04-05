import pdfplumber
from typing import Optional


def extract_pdf_text(file_path: str) -> str:
    """
    Extract raw text from a PDF file.

    Args:
        file_path (str): Path to the PDF resume

    Returns:
        str: Extracted text (empty string if nothing found)
    """
    text_content = []

    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text: Optional[str] = page.extract_text()
                if page_text:
                    text_content.append(page_text)

    except Exception:
        # Fail silently — ATS must not crash on bad PDFs
        return ""

    return "\n".join(text_content).strip()
