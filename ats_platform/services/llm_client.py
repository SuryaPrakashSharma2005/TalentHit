import os
from typing import List, Dict, Optional
from dotenv import load_dotenv

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


class LLMClient:
    """
    Centralized LLM client for ATS.
    Used ONLY for resume explanation / summary.
    """

    def __init__(self):
        self.enabled = bool(OPENAI_API_KEY and OpenAI)
        self.client = OpenAI(api_key=OPENAI_API_KEY) if self.enabled else None

    def generate_resume_summary(
        self,
        name: Optional[str],
        skills: List[str],
        experience_years: float,
        education: Dict[str, Optional[str]],
        max_words: int = 80
    ) -> str:
        if not self.enabled:
            return self._fallback_summary(name, skills, experience_years, education)

        prompt = self._build_prompt(
            name=name,
            skills=skills,
            experience_years=experience_years,
            education=education,
            max_words=max_words
        )

        try:
            response = self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return self._fallback_summary(name, skills, experience_years, education)

    @staticmethod
    def _build_prompt(
        name: Optional[str],
        skills: List[str],
        experience_years: float,
        education: Dict[str, Optional[str]],
        max_words: int
    ) -> str:
        return f"""
You are an ATS assistant helping recruiters.

Create a concise professional resume summary (maximum {max_words} words).
Use ONLY the information provided below.
Do NOT invent facts.
Do NOT add opinions.

Candidate Name: {name or "Not provided"}
Experience: {experience_years} years
Skills: {", ".join(skills) if skills else "Not specified"}
Education: {education}

Tone: professional, neutral, recruiter-friendly.
"""

    @staticmethod
    def _fallback_summary(
        name: Optional[str],
        skills: List[str],
        experience_years: float,
        education: Dict[str, Optional[str]]
    ) -> str:
        parts = []

        if name:
            parts.append(name)

        if experience_years > 0:
            parts.append(f"{experience_years} years of experience")

        if skills:
            parts.append(f"skills in {', '.join(skills[:5])}")

        if education and education.get("degree"):
            parts.append(f"{education['degree']} graduate")

        if not parts:
            return "Candidate profile summary unavailable."

        return "Candidate with " + ", ".join(parts) + "."
