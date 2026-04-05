import os

PROJECT_NAME = "ats-platform"

DIRECTORIES = [
    "extractor",
    "services",
    "assessment/quiz",
    "assessment/coding",
    "routers",
    "storage",
    "tests"
]

FILES = [
    # Root files
    "app.py",
    "final_score.py",
    "requirements.txt",
    ".env",
    ".gitignore",

    # Extractor
    "extractor/__init__.py",
    "extractor/pdf.py",
    "extractor/clean.py",
    "extractor/personal.py",
    "extractor/skills.py",
    "extractor/experience.py",
    "extractor/education.py",

    # Services
    "services/__init__.py",
    "services/llm_client.py",
    "services/resume_service.py",
    "services/scoring_service.py",

    # Assessment
    "assessment/quiz/__init__.py",
    "assessment/quiz/evaluator.py",
    "assessment/coding/__init__.py",
    "assessment/coding/evaluator.py",

    # Routers
    "routers/__init__.py",
    "routers/resume.py",
    "routers/quiz.py",
    "routers/coding.py",
    "routers/health.py",

    # Tests
    "tests/test_resume.py"
]

def create_structure():
    print("🚀 Creating ATS MVP structure...")

    os.makedirs(PROJECT_NAME, exist_ok=True)
    os.chdir(PROJECT_NAME)

    for d in DIRECTORIES:
        os.makedirs(d, exist_ok=True)

    for f in FILES:
        os.makedirs(os.path.dirname(f), exist_ok=True) if os.path.dirname(f) else None
        if not os.path.exists(f):
            open(f, "w", encoding="utf-8").close()

    print("✅ ATS MVP structure created successfully!")

if __name__ == "__main__":
    create_structure()
